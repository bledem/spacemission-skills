import { useState, useCallback } from 'react';

export const DEFAULT_OBJECTIVE =
  "design a round-trip interplanetary mission that reaches the **maximum possible heliocentric distance** from the Sun and returns safely to Earth, all within a fixed propellant (delta-v) budget.";

const INSTRUCTION_TEMPLATE_URL = '../../../task/instruction.md';

interface MissionObjectivePanelProps {
  objective: string;
  onChange: (value: string) => void;
}

export function MissionObjectivePanel({ objective, onChange }: MissionObjectivePanelProps) {
  const [expanded, setExpanded] = useState(false);

  const handleExport = useCallback(async () => {
    try {
      const resp = await fetch(INSTRUCTION_TEMPLATE_URL);
      let template = resp.ok ? await resp.text() : null;

      if (!template) {
        // Fallback: generate a minimal stub if the file isn't reachable
        template = `# Deep Space Explorer: Interplanetary Mission Design Challenge\n\nYou are a spacecraft mission designer. Your goal is to {{MISSION_OBJECTIVE}}\n`;
      }

      const injected = template.replace('{{MISSION_OBJECTIVE}}', objective);
      const blob = new Blob([injected], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'instruction.md';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('Export failed — check console for details.');
    }
  }, [objective]);

  return (
    <div className="bg-space-bg/80 backdrop-blur-sm border border-white/10 rounded-lg p-4">
      <button
        className="w-full flex items-center justify-between text-sm font-semibold text-white/70 mb-2"
        onClick={() => setExpanded((v) => !v)}
      >
        <span>Mission Objective</span>
        <span className="text-white/40 text-xs">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <>
          <textarea
            className="w-full bg-black/30 border border-white/10 rounded p-2 text-xs text-white/80 font-mono resize-y min-h-[80px] focus:outline-none focus:border-white/30"
            value={objective}
            onChange={(e) => onChange(e.target.value)}
          />
          <div className="mt-2 flex gap-2">
            <button
              className="flex-1 text-xs bg-white/10 hover:bg-white/20 text-white/70 rounded px-2 py-1 transition-colors"
              onClick={() => onChange(DEFAULT_OBJECTIVE)}
            >
              Reset
            </button>
            <button
              className="flex-1 text-xs bg-blue-900/50 hover:bg-blue-800/50 text-blue-300 rounded px-2 py-1 transition-colors"
              onClick={handleExport}
            >
              Export instruction.md
            </button>
          </div>
          <p className="mt-2 text-white/30 text-xs leading-tight">
            Replaces <code className="text-white/50">{'{{MISSION_OBJECTIVE}}'}</code> in instruction.md
          </p>
        </>
      )}

      {!expanded && (
        <p className="text-white/40 text-xs truncate font-mono">{objective}</p>
      )}
    </div>
  );
}
