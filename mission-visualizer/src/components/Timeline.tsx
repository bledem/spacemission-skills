import type { ParsedMission } from '../lib/missionParser';

interface TimelineProps {
  mission: ParsedMission;
  currentTime: number;
  onTimeChange: (time: number) => void;
  isPlaying: boolean;
  onPlayPause: () => void;
}

export function Timeline({
  mission,
  currentTime,
  onTimeChange,
  isPlaying,
  onPlayPause,
}: TimelineProps) {
  const totalDuration = mission.mission_duration_days;

  // Calculate phase marker positions
  const phaseMarkers = mission.phases.map((phase) => {
    const phaseDate = new Date(phase.date);
    const startDate = new Date(mission.departure_date);
    const daysSinceStart = (phaseDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24);
    return {
      phase: phase.phase,
      position: daysSinceStart / totalDuration,
      date: phase.date,
    };
  });

  return (
    <div className="bg-space-bg/80 backdrop-blur-sm border border-white/10 rounded-lg p-4">
      <div className="flex items-center gap-4">
        <button
          onClick={onPlayPause}
          className="px-3 py-1 bg-white/10 hover:bg-white/20 rounded text-white text-sm transition-colors"
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? '⏸ Pause' : '▶ Play'}
        </button>

        <div className="flex-1 relative">
          {/* Phase markers */}
          <div className="absolute top-0 left-0 right-0 h-4 pointer-events-none">
            {phaseMarkers.map((marker, index) => (
              <div
                key={index}
                className="absolute w-1 h-4 bg-white/50"
                style={{ left: `${marker.position * 100}%` }}
                data-phase-marker={marker.phase}
              />
            ))}
          </div>

          {/* Timeline slider */}
          <input
            type="range"
            min="0"
            max="1"
            step="0.001"
            value={currentTime}
            onChange={(e) => onTimeChange(parseFloat(e.target.value))}
            className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer"
            aria-label="Mission timeline"
          />
        </div>

        <div className="text-white/50 text-xs whitespace-nowrap">
          <span>{mission.departure_date}</span>
          <span className="mx-2">→</span>
          <span>{mission.phases[mission.phases.length - 1]?.date}</span>
        </div>
      </div>
    </div>
  );
}
