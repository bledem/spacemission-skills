import type { ParsedMission } from '../lib/missionParser';

interface ScoreboardProps {
  mission: ParsedMission;
}

const tierColors: Record<string, string> = {
  Bronze: 'text-amber-600',
  Silver: 'text-gray-400',
  Gold: 'text-yellow-400',
  Platinum: 'text-cyan-300',
};

export function Scoreboard({ mission }: ScoreboardProps) {
  return (
    <div className="bg-space-bg/80 backdrop-blur-sm border border-white/10 rounded-lg p-4 text-white">
      <h2 className="text-lg font-semibold mb-3 text-white/80">{mission.mission_name}</h2>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-white/50">Max Distance</span>
          <p className="font-mono text-lg">{mission.max_distance_AU.toFixed(2)} AU</p>
        </div>

        <div>
          <span className="text-white/50">Total Δv</span>
          <p className="font-mono text-lg">{mission.total_delta_v_km_s.toFixed(2)} km/s</p>
        </div>

        <div>
          <span className="text-white/50">Duration</span>
          <p className="font-mono text-lg">{mission.mission_duration_days} days</p>
        </div>

        <div>
          <span className="text-white/50">Tier</span>
          <p className={`font-bold text-lg ${tierColors[mission.tier]}`}>
            {mission.tier}
          </p>
        </div>
      </div>
    </div>
  );
}
