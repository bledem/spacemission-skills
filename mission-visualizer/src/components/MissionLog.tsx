import { useState, useEffect, useRef } from 'react';

// ── Skill step definitions (mirrors agent/skills/deep-space-explorer/SKILL.md) ─

interface SkillStep {
  num: number;
  label: string;
  description: string;
  keywords: RegExp;
  highlights: RegExp;
  color: string;
}

const SKILL_STEPS: SkillStep[] = [
  {
    num: 1,
    label: 'Write single script',
    description: 'One complete Python script, no incremental snippets',
    keywords: /\b(single script|one script|complete script|python3?\s+-c|cat\s*>|tee)\b/i,
    highlights: /\b(single script|one complete|python script)\b/gi,
    color: 'violet',
  },
  {
    num: 2,
    label: 'Δv from v∞',
    description: 'dv_from_vinf: hyperbolic excess speed → parking-orbit burn',
    keywords: /\b(dv_from_vinf|v_inf|vinf|mu_earth|mu_mars|mu_venus|parking.?orbit|dv_dep|dv_arr|dv_cap)\b/i,
    highlights: /\b(dv_from_vinf|v_inf|v_p|v_c|parking)\b/gi,
    color: 'cyan',
  },
  {
    num: 3,
    label: 'Lambert solver',
    description: 'solve_lambert_problem for heliocentric transfer arcs',
    keywords: /\b(lambert|solve_lambert|OrbitDetermination|set_celestial_body|heliocentric|transfer.?orbit)\b/i,
    highlights: /\b(lambert|solve_lambert_problem|OrbitDetermination|heliocentric)\b/gi,
    color: 'blue',
  },
  {
    num: 4,
    label: 'Strategy selection',
    description: 'Direct Hohmann vs gravity assist vs bi-elliptic',
    keywords: /\b(strategy|gravity.?assist|flyby|hohmann|bi.?elliptic|Venus|Jupiter|Saturn|swing.?by)\b/i,
    highlights: /\b(gravity.assist|flyby|Hohmann|bi.elliptic)\b/gi,
    color: 'amber',
  },
  {
    num: 5,
    label: 'Window scan',
    description: 'Iterate departure dates to minimise total Δv',
    keywords: /\b(ephemeris|synodic|scan|departure.?window|timedelta|departure.?date)\b/i,
    highlights: /\b(ephemeris|synodic|scan|window|timedelta)\b/gi,
    color: 'emerald',
  },
  {
    num: 6,
    label: 'Output mission plan',
    description: 'Write /app/mission_plan.json — must pass verifier',
    keywords: /\b(mission_plan\.json|json\.dump|verif|all_constraints|reward)\b/i,
    highlights: /\b(mission_plan\.json|json\.dump|verif|reward)\b/gi,
    color: 'rose',
  },
];

const COLOR: Record<string, Record<string, string>> = {
  violet:  { border: 'border-violet-500/50',  bg: 'bg-violet-950/40',  text: 'text-violet-300',  badge: 'bg-violet-900/60 text-violet-300',  dot: 'bg-violet-400',  mark: 'bg-violet-500/20 text-violet-200' },
  cyan:    { border: 'border-cyan-500/50',    bg: 'bg-cyan-950/40',    text: 'text-cyan-300',    badge: 'bg-cyan-900/60 text-cyan-300',    dot: 'bg-cyan-400',    mark: 'bg-cyan-500/20 text-cyan-200' },
  blue:    { border: 'border-blue-500/50',    bg: 'bg-blue-950/40',    text: 'text-blue-300',    badge: 'bg-blue-900/60 text-blue-300',    dot: 'bg-blue-400',    mark: 'bg-blue-500/20 text-blue-200' },
  amber:   { border: 'border-amber-500/50',   bg: 'bg-amber-950/40',   text: 'text-amber-300',   badge: 'bg-amber-900/60 text-amber-300',   dot: 'bg-amber-400',   mark: 'bg-amber-500/20 text-amber-200' },
  emerald: { border: 'border-emerald-500/50', bg: 'bg-emerald-950/40', text: 'text-emerald-300', badge: 'bg-emerald-900/60 text-emerald-300', dot: 'bg-emerald-400', mark: 'bg-emerald-500/20 text-emerald-200' },
  rose:    { border: 'border-rose-500/50',    bg: 'bg-rose-950/40',    text: 'text-rose-300',    badge: 'bg-rose-900/60 text-rose-300',    dot: 'bg-rose-400',    mark: 'bg-rose-500/20 text-rose-200' },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function detectSteps(text: string): SkillStep[] {
  return SKILL_STEPS.filter((s) => s.keywords.test(text));
}

function HighlightedText({ text, steps }: { text: string; steps: SkillStep[] }) {
  if (steps.length === 0) return <>{text}</>;

  const combined = new RegExp(steps.map((s) => s.highlights.source).join('|'), 'gi');
  const parts: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;

  while ((m = combined.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const matchedStep = steps.find((s) => new RegExp(s.highlights.source, 'i').test(m![0]));
    const c = matchedStep ? COLOR[matchedStep.color] : null;
    parts.push(
      <mark key={m.index} className={`rounded px-0.5 font-semibold not-italic ${c?.mark ?? 'bg-white/10 text-white'}`}>
        {m[0]}
      </mark>
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <>{parts}</>;
}

// ── Types ─────────────────────────────────────────────────────────────────────

interface ToolResult { command: string; stdout: string; stderr: string; exit_code: number; }

interface TurnEntry {
  type: 'turn_complete';
  turn: number;
  thinking: string[];
  commands: string[];
  results: ToolResult[];
  timestamp: number;
  activeSteps: SkillStep[];
}

interface RawLogEntry { type: 'log'; text: string; timestamp: number; }
type LogEntry = TurnEntry | RawLogEntry;

// ── Skill sidebar ─────────────────────────────────────────────────────────────

function SkillPanel({ activeStepNums, latestStepNum }: { activeStepNums: Set<number>; latestStepNum: number | null }) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-[10px] font-semibold text-white/30 uppercase tracking-widest px-1 mb-1">
        deep-space-explorer
      </p>
      {SKILL_STEPS.map((step) => {
        const active = activeStepNums.has(step.num);
        const latest = latestStepNum === step.num;
        const c = COLOR[step.color];
        return (
          <div key={step.num} className={`rounded-lg px-3 py-2 border transition-all duration-300 ${latest ? `${c.border} ${c.bg} shadow-sm` : active ? 'border-white/10 bg-white/5' : 'border-transparent opacity-35'}`}>
            <div className="flex items-center gap-2">
              <span className={`text-[10px] font-bold w-4 shrink-0 ${active ? c.text : 'text-white/30'}`}>{step.num}</span>
              <span className={`text-xs font-semibold leading-tight ${active ? c.text : 'text-white/40'}`}>{step.label}</span>
              {latest && (
                <span className={`ml-auto flex items-center gap-1 text-[9px] font-mono ${c.text}`}>
                  <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${c.dot}`} />
                  NOW
                </span>
              )}
            </div>
            {active && <p className="text-[10px] text-white/30 mt-0.5 leading-snug pl-6">{step.description}</p>}
          </div>
        );
      })}
    </div>
  );
}

// ── Turn card ─────────────────────────────────────────────────────────────────

function TurnCard({ entry }: { entry: TurnEntry }) {
  const [expanded, setExpanded] = useState(true);
  const steps = entry.activeSteps;
  const primaryStep = steps[0];
  const c = primaryStep ? COLOR[primaryStep.color] : null;

  return (
    <div className={`rounded-lg border overflow-hidden ${c ? `${c.border} ${c.bg}` : 'border-white/10 bg-black/20'}`}>
      <button className="w-full flex items-center gap-2 px-3 py-2 text-left" onClick={() => setExpanded((v) => !v)}>
        <span className={`text-[10px] font-mono font-bold px-1.5 py-px rounded ${c ? c.badge : 'bg-white/10 text-white/50'}`}>T{entry.turn}</span>
        {steps.map((s) => (
          <span key={s.num} className={`text-[9px] font-mono px-1.5 py-px rounded border ${COLOR[s.color].badge} ${COLOR[s.color].border}`}>
            Step {s.num}: {s.label}
          </span>
        ))}
        <span className="ml-auto text-white/20 text-[10px]">{new Date(entry.timestamp).toLocaleTimeString()}</span>
        <span className="text-white/20 text-xs">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="border-t border-white/5 px-3 py-2 space-y-3">
          {entry.thinking.map((text, i) => (
            <div key={i} className="border-l-2 border-white/10 pl-3">
              <p className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Thinking</p>
              <p className="text-xs text-white/70 leading-relaxed whitespace-pre-wrap italic">
                <HighlightedText text={text} steps={steps} />
              </p>
            </div>
          ))}
          {entry.results.map((res, i) => (
            <div key={i} className="space-y-1">
              <div className="bg-black/40 border border-white/5 rounded px-2 py-1.5">
                <p className="text-[10px] text-green-500/50 mb-1">$ bash</p>
                <pre className="text-[11px] text-green-300/80 font-mono whitespace-pre-wrap break-all leading-relaxed max-h-48 overflow-y-auto">{res.command}</pre>
              </div>
              {(res.stdout || res.stderr) && (
                <div className="bg-black/30 border border-white/5 rounded px-2 py-1.5">
                  <p className={`text-[10px] mb-1 ${res.exit_code === 0 ? 'text-white/25' : 'text-red-400/60'}`}>
                    exit {res.exit_code}{res.stderr ? ' · stderr' : ''}
                  </p>
                  <pre className={`text-[11px] font-mono whitespace-pre-wrap break-all leading-relaxed max-h-40 overflow-y-auto ${res.exit_code === 0 ? 'text-white/45' : 'text-red-300/70'}`}>
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

interface MissionLogProps {
  onAgentActive?: (active: boolean) => void;
}

export function MissionLog({ onAgentActive }: MissionLogProps = {}) {
  const [visible, setVisible] = useState(false);
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<'connecting' | 'streaming' | 'done' | 'error'>('connecting');
  const [activeStepNums, setActiveStepNums] = useState<Set<number>>(new Set());
  const [latestStepNum, setLatestStepNum] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let es: EventSource;
    let connectTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      es = new EventSource('http://localhost:8788/events');

      connectTimeout = setTimeout(() => {
        es.close();
        setTimeout(connect, 5000);
      }, 3000);

      es.onopen = () => {
        clearTimeout(connectTimeout);
        setVisible(true);
        setStatus('streaming');
        onAgentActive?.(true);
      };

      es.onerror = () => {
        clearTimeout(connectTimeout);
        es.close();
        setTimeout(connect, 5000);
      };

      es.addEventListener('log', (e) => {
        const data = JSON.parse((e as MessageEvent).data);
        if (/Turn\s+\d+\/\d+/.test(data.text)) {
          setEntries((prev) => [...prev, { type: 'log', text: data.text, timestamp: Date.now() }]);
        }
      });

      es.addEventListener('turn_complete', (e) => {
        const data = JSON.parse((e as MessageEvent).data);
        const allText = [...(data.thinking ?? []), ...(data.commands ?? [])].join(' ');
        const steps = detectSteps(allText);

        if (steps.length > 0) {
          setActiveStepNums((prev) => new Set([...prev, ...steps.map((s) => s.num)]));
          setLatestStepNum(steps[steps.length - 1].num);
        }

        setEntries((prev) => [...prev, { type: 'turn_complete', ...data, timestamp: Date.now(), activeSteps: steps }]);
      });

      es.addEventListener('done', () => {
        setStatus('done');
        onAgentActive?.(false);
        es.close();
        setTimeout(() => { window.location.href = '/?mission=generated'; }, 2000);
      });
    }

    connect();
    return () => {
      clearTimeout(connectTimeout);
      es?.close();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries]);

  if (!visible) return null;

  return (
    <div className="flex gap-4" style={{ height: '520px' }}>
      {/* Skill sidebar */}
      <div className="w-52 shrink-0 overflow-y-auto">
        <SkillPanel activeStepNums={activeStepNums} latestStepNum={latestStepNum} />
      </div>

      {/* Log feed */}
      <div className="flex-1 flex flex-col bg-black/40 border border-white/10 rounded-lg overflow-hidden">
        <div className="bg-white/5 px-4 py-2 border-b border-white/10 flex items-center justify-between shrink-0">
          <span className="text-white/60 text-xs font-semibold uppercase tracking-wider">Agent Reasoning & Execution</span>
          <div className="flex items-center gap-2">
            {status === 'streaming' && <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />}
            {status === 'done' && <span className="text-green-400 text-[10px]">DONE — redirecting…</span>}
            {status === 'error' && <span className="text-red-400 text-[10px]">RECONNECTING…</span>}
          </div>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-2">
          {entries.length === 0 && (
            <p className="text-white/20 text-xs italic py-4 text-center">Waiting for agent to start…</p>
          )}
          {entries.map((entry, i) =>
            entry.type === 'log' ? (
              <div key={i} className="text-white/30 text-[11px] font-mono px-2">{(entry as RawLogEntry).text}</div>
            ) : (
              <TurnCard key={i} entry={entry as TurnEntry} />
            )
          )}
        </div>
      </div>
    </div>
  );
}
