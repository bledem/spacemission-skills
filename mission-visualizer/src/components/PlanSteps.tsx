import type { LiveSimData, PlanStep } from '../hooks/useSimConnection';

const STATUS_ICON: Record<PlanStep['status'], string> = {
  pending: '○',
  active: '◉',
  done: '●',
  failed: '✕',
};

const STATUS_COLOR: Record<PlanStep['status'], string> = {
  pending: 'text-white/30',
  active: 'text-yellow-400',
  done: 'text-green-400',
  failed: 'text-red-400',
};

function formatDate(date: string): string {
  if (!date) return '';
  return date.slice(0, 10);
}

function formatPhase(phase: string): string {
  return phase.replace(/_/g, ' ');
}

export function PlanSteps({ sim }: { sim: LiveSimData }) {
  if (sim.planSteps.length === 0) {
    return null;
  }

  return (
    <div className="bg-space-bg/80 backdrop-blur-sm border border-white/10 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white/70">Mission Steps</h3>
        {sim.planStatus === 'error' && (
          <span className="text-xs font-mono text-red-400">FAILED</span>
        )}
        {sim.planStatus === 'complete' && (
          <span className="text-xs font-mono text-green-400">DONE</span>
        )}
      </div>

      <div className="space-y-2">
        {sim.planSteps.map((step, i) => (
          <div
            key={i}
            className={`flex items-start gap-2 text-xs ${
              step.status === 'active' ? 'bg-yellow-900/20 -mx-2 px-2 py-1 rounded' :
              step.status === 'failed' ? 'bg-red-900/20 -mx-2 px-2 py-1 rounded' : ''
            }`}
          >
            <span className={`${STATUS_COLOR[step.status]} text-sm leading-none mt-0.5`}>
              {STATUS_ICON[step.status]}
            </span>
            <div className="flex-1 min-w-0">
              <div className={`font-mono uppercase ${
                step.status === 'active' ? 'text-yellow-400' :
                step.status === 'done' ? 'text-white/70' :
                step.status === 'failed' ? 'text-red-400' : 'text-white/40'
              }`}>
                {formatPhase(step.phase)}
              </div>
              <div className="text-white/30 truncate">{step.description}</div>
              <div className="flex gap-3 text-white/30 mt-0.5">
                <span>{formatDate(step.date)}</span>
                <span>{step.delta_v_km_s.toFixed(2)} km/s</span>
              </div>
              {step.status === 'failed' && sim.planError && (
                <div className="mt-1 text-red-400 font-mono">
                  {sim.planError.replace(/_/g, ' ')}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
