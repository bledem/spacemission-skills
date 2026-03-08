import { useEffect, useRef, useState } from 'react';

const CAPTURE_SERVER = 'http://localhost:8788';

// ── Skill step definitions ────────────────────────────────────────────────────

const SKILL_STEPS = [
  { id: 'script',   label: 'Writing script',          keywords: /\b(python|script|import numpy|cat >|tee)\b/i },
  { id: 'dv',       label: 'Delta-v computation',     keywords: /\b(dv_from_vinf|v_inf|vinf|dv_dep|dv_arr)\b/i },
  { id: 'lambert',  label: 'Lambert solver',           keywords: /\b(lambert|solve_lambert|OrbitDetermination)\b/i },
  { id: 'strategy', label: 'Strategy selection',      keywords: /\b(strategy|flyby|gravity.?assist|venus|jupiter|saturn)\b/i },
  { id: 'scan',     label: 'Window scan',              keywords: /\b(ephemeris|synodic|scan|timedelta)\b/i },
  { id: 'output',   label: 'Mission plan output',     keywords: /\b(mission_plan\.json|json\.dump|verif|reward)\b/i },
];

// ── Types ─────────────────────────────────────────────────────────────────────

interface ToolResult {
  command: string;
  stdout: string;
  stderr: string;
  exit_code: number;
}

interface Turn {
  turn: number;
  thinking: string[];
  commands: string[];
  results: ToolResult[];
  usage: { input_tokens?: number; output_tokens?: number };
}

// ── Sub-components ────────────────────────────────────────────────────────────

function TurnCard({ turn, isLast }: { turn: Turn; isLast: boolean }) {
  const [expanded, setExpanded] = useState(isLast);
  const hasContent = turn.thinking.length > 0 || turn.results.length > 0;

  // Re-expand when this becomes the latest turn
  useEffect(() => {
    if (isLast) setExpanded(true);
  }, [isLast]);

  return (
    <div className={`border rounded-lg overflow-hidden transition-colors ${
      isLast ? 'border-blue-700/40 bg-blue-950/10' : 'border-white/10 bg-black/20'
    }`}>
      {/* Turn header */}
      <button
        className="w-full flex items-center gap-3 px-3 py-2 text-left"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className={`text-[10px] font-mono px-1.5 py-px rounded ${
          isLast ? 'bg-blue-800/60 text-blue-300' : 'bg-white/10 text-white/40'
        }`}>
          T{turn.turn}
        </span>
        {turn.thinking[0] && (
          <span className="text-xs text-white/50 truncate flex-1">
            {turn.thinking[0].slice(0, 120)}
          </span>
        )}
        <span className="text-white/20 text-[10px] ml-auto shrink-0">
          {turn.results.length} cmd{turn.results.length !== 1 ? 's' : ''}
          {turn.usage.output_tokens ? ` · ${turn.usage.output_tokens}tok` : ''}
        </span>
        <span className="text-white/20 text-xs">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && hasContent && (
        <div className="border-t border-white/5 px-3 py-2 space-y-3">
          {/* Thinking */}
          {turn.thinking.map((text, i) => (
            <div key={i} className="border-l-2 border-blue-500/30 pl-2">
              <p className="text-[10px] text-blue-500/50 uppercase tracking-wider mb-0.5">Thinking</p>
              <p className="text-xs text-blue-200/70 font-mono leading-relaxed whitespace-pre-wrap">{text}</p>
            </div>
          ))}

          {/* Commands + outputs */}
          {turn.results.map((res, i) => (
            <div key={i} className="space-y-1">
              {/* Command */}
              <div className="bg-green-950/30 border border-green-800/20 rounded px-2 py-1.5">
                <p className="text-[10px] text-green-500/60 mb-0.5">$ bash</p>
                <pre className="text-[11px] text-green-300/80 font-mono whitespace-pre-wrap break-all leading-relaxed max-h-40 overflow-y-auto">
                  {res.command}
                </pre>
              </div>

              {/* Output */}
              {(res.stdout || res.stderr) && (
                <div className="bg-black/30 border border-white/5 rounded px-2 py-1.5">
                  <p className="text-[10px] text-white/25 mb-0.5">
                    output · exit {res.exit_code}
                    {res.stderr ? ' · stderr' : ''}
                  </p>
                  <pre className="text-[11px] text-white/50 font-mono whitespace-pre-wrap break-all leading-relaxed max-h-48 overflow-y-auto">
                    {res.stdout || res.stderr}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface AgentFeedProps {
  onAgentActive?: (active: boolean) => void;
}

export function AgentFeed({ onAgentActive }: AgentFeedProps) {
  const [visible, setVisible] = useState(false);
  const [connected, setConnected] = useState(false);
  const [currentTurnNum, setCurrentTurnNum] = useState(0);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [activeSteps, setActiveSteps] = useState<Set<string>>(new Set());
  const [isDone, setIsDone] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let es: EventSource;
    let connectTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      es = new EventSource(`${CAPTURE_SERVER}/events`);

      connectTimeout = setTimeout(() => {
        es.close();
        if (!isDone) setTimeout(connect, 5000);
      }, 2000);

      es.onopen = () => {
        clearTimeout(connectTimeout);
        setVisible(true);
        setConnected(true);
        onAgentActive?.(true);
      };

      // Raw log → turn progress counter only
      es.addEventListener('log', (e) => {
        const { text } = JSON.parse((e as MessageEvent).data) as { text: string };
        const m = text.match(/Turn\s+(\d+)\/(\d+)/);
        if (m) setCurrentTurnNum(Number(m[1]));
      });

      // Structured turn data from JSONL
      es.addEventListener('turn_complete', (e) => {
        const turn = JSON.parse((e as MessageEvent).data) as Turn;

        // Detect active skill steps from commands and thinking
        const allText = [...turn.thinking, ...turn.commands].join(' ');
        const newSteps = new Set<string>();
        for (const step of SKILL_STEPS) {
          if (step.keywords.test(allText)) newSteps.add(step.id);
        }
        if (newSteps.size > 0) {
          setActiveSteps((prev) => new Set([...prev, ...newSteps]));
        }

        setTurns((prev) => {
          const exists = prev.findIndex((t) => t.turn === turn.turn);
          if (exists >= 0) {
            const next = [...prev];
            next[exists] = turn;
            return next;
          }
          return [...prev, turn];
        });
      });

      es.addEventListener('done', () => {
        setIsDone(true);
        setConnected(false);
        onAgentActive?.(false);
        es.close();
      });

      es.onerror = () => {
        clearTimeout(connectTimeout);
        setConnected(false);
        es.close();
        if (!isDone) setTimeout(connect, 5000);
      };
    }

    connect();
    return () => {
      clearTimeout(connectTimeout);
      es?.close();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns.length]);

  if (!visible) return null;

  const maxTurns = 15;

  return (
    <div className="bg-space-bg/80 backdrop-blur-sm border border-white/10 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-white/10 bg-black/20">
        <span className="text-xs font-semibold text-white/60">Agent Live Feed</span>
        <span className={`px-1.5 py-px rounded text-[10px] font-mono ${
          isDone
            ? 'bg-emerald-900/50 text-emerald-400'
            : connected
            ? 'bg-blue-900/50 text-blue-400 animate-pulse'
            : 'bg-yellow-900/40 text-yellow-500'
        }`}>
          {isDone ? 'DONE' : connected ? 'LIVE' : 'RECONNECTING'}
        </span>

        {/* Turn progress bar */}
        {!isDone && currentTurnNum > 0 && (
          <div className="flex items-center gap-2 ml-2">
            <div className="w-24 bg-white/10 rounded-full h-1 overflow-hidden">
              <div
                className="h-full bg-blue-500/60 transition-all duration-500"
                style={{ width: `${(currentTurnNum / maxTurns) * 100}%` }}
              />
            </div>
            <span className="text-white/30 text-[10px] font-mono">{currentTurnNum}/{maxTurns}</span>
          </div>
        )}

        {/* Skill pills */}
        <div className="ml-auto flex flex-wrap gap-1">
          {SKILL_STEPS.map((step) => (
            <span key={step.id} className={`px-1.5 py-px rounded text-[9px] font-mono transition-colors ${
              activeSteps.has(step.id)
                ? 'bg-blue-800/60 text-blue-300 border border-blue-600/30'
                : 'bg-white/5 text-white/20'
            }`}>
              {step.label}
            </span>
          ))}
        </div>
      </div>

      {/* Turn cards */}
      <div className="p-3 space-y-2 max-h-[520px] overflow-y-auto">
        {turns.length === 0 ? (
          <p className="text-white/20 text-[11px] font-mono py-4 text-center">
            {connected ? 'Waiting for first turn…' : 'Connecting to agent feed…'}
          </p>
        ) : (
          turns.map((t, i) => (
            <TurnCard key={t.turn} turn={t} isLast={i === turns.length - 1} />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {isDone && (
        <div className="px-4 py-2 border-t border-white/10 bg-emerald-950/20 text-emerald-400 text-xs text-center">
          Agent finished — reload the page to see the updated mission.
        </div>
      )}
    </div>
  );
}
