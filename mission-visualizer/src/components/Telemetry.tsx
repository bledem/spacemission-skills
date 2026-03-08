/**
 * Live telemetry panel — shows spacecraft subsystem status from the sim.
 */

import type { LiveSimData } from '../hooks/useSimConnection';

const STATUS_COLORS: Record<string, string> = {
  green: 'text-green-400',
  yellow: 'text-yellow-400',
  red: 'text-red-400',
  emergency: 'text-red-600 animate-pulse',
};

function StatusDot({ status }: { status: string }) {
  const color = STATUS_COLORS[status] ?? 'text-gray-400';
  return <span className={color}>●</span>;
}

function formatElapsed(elapsed_s: number): string {
  const days = Math.floor(elapsed_s / 86400);
  const hours = Math.floor((elapsed_s % 86400) / 3600);
  const mins = Math.floor((elapsed_s % 3600) / 60);
  const secs = Math.floor(elapsed_s % 60);
  if (days > 0) return `T+${days}d ${hours}h ${mins}m`;
  if (hours > 0) return `T+${hours}h ${mins}m ${secs}s`;
  return `T+${mins}m ${secs}s`;
}

function formatEpoch(epoch: string): string {
  const d = new Date(epoch);
  return d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
}

export function Telemetry({ sim }: { sim: LiveSimData }) {
  if (!sim.spacecraft || !sim.time) {
    return (
      <div className="bg-space-bg/80 backdrop-blur-sm border border-white/10 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-white/70 mb-2">Telemetry</h3>
        <p className="text-white/30 text-xs">
          {sim.connected ? 'Waiting for data...' : 'Disconnected'}
        </p>
      </div>
    );
  }

  const { spacecraft: sc, time } = sim;
  const sub = sc.subsystems;

  return (
    <div className="bg-space-bg/80 backdrop-blur-sm border border-white/10 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/70">Telemetry</h3>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${sim.connected ? 'bg-green-400' : 'bg-red-400'}`} />
          <span className="text-xs text-white/50">{sim.connected ? 'LIVE' : 'OFFLINE'}</span>
        </div>
      </div>

      {/* Time & Status */}
      <div className="space-y-1 text-xs">
        <div>
          <span className="text-white/40">Epoch</span>
          <div className="text-white/90 font-mono">{formatEpoch(time.epoch)}</div>
        </div>
        <div>
          <span className="text-white/40">Elapsed</span>
          <div className="text-white/90 font-mono">{formatElapsed(time.elapsed_s)}</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-white/40">Step</span>
          <div className="text-white/90 font-mono">{time.step}</div>
        </div>
        <div>
          <span className="text-white/40">Status</span>
          <div className="text-white/90 font-mono uppercase">{sc.status}</div>
        </div>
        <div>
          <span className="text-white/40">Orbit</span>
          <div className="text-white/90 font-mono">{sc.orbit_type}</div>
        </div>
      </div>

      {/* Orbit */}
      <div className="border-t border-white/5 pt-2">
        <div className="text-xs text-white/40 mb-1">Orbit</div>
        <div className="grid grid-cols-2 gap-1 text-xs font-mono">
          <div>Alt: <span className="text-white/90">{sc.altitude_km.toFixed(1)} km</span></div>
          <div>e: <span className="text-white/90">{sc.eccentricity.toFixed(4)}</span></div>
          <div>T: <span className="text-white/90">{sc.period_s < 1e8 ? `${(sc.period_s / 60).toFixed(0)} min` : '∞'}</span></div>
          <div>Mass: <span className="text-white/90">{sc.mass_kg.toFixed(2)} kg</span></div>
        </div>
      </div>

      {/* Subsystems */}
      <div className="border-t border-white/5 pt-2">
        <div className="text-xs text-white/40 mb-1">Subsystems</div>
        <div className="space-y-1 text-xs">
          <div className="flex justify-between">
            <span><StatusDot status={sub.power.status} /> Power</span>
            <span className="font-mono text-white/70">
              SOC {sub.power.battery_soc_pct.toFixed(0)}% | {sub.power.solar_input_w.toFixed(0)}W
            </span>
          </div>
          <div className="flex justify-between">
            <span><StatusDot status={sub.thermal.status} /> Thermal</span>
            <span className="font-mono text-white/70">
              Prop {sub.thermal.propulsion_temp_c.toFixed(0)}°C | Batt {sub.thermal.battery_temp_c.toFixed(0)}°C
            </span>
          </div>
          <div className="flex justify-between">
            <span><StatusDot status={sub.propulsion.status} /> Propulsion</span>
            <span className="font-mono text-white/70">
              {sub.propulsion.fuel_kg.toFixed(2)} kg | {sub.propulsion.can_fire ? 'READY' : 'INHIBIT'}
            </span>
          </div>
          <div className="flex justify-between">
            <span><StatusDot status={sub.comms.status} /> Comms</span>
            <span className="font-mono text-white/70">
              {sub.comms.downlink_rate_kbps.toFixed(1)} kbps
            </span>
          </div>
          <div className="flex justify-between">
            <span><StatusDot status={sub.adcs.status} /> ADCS</span>
            <span className="font-mono text-white/70">
              {sub.adcs.mode} | {sub.adcs.pointing_error_deg.toFixed(3)}°
            </span>
          </div>
        </div>
      </div>

      {/* Events */}
      {sim.events.length > 0 && (
        <div className="border-t border-white/5 pt-2">
          <div className="text-xs text-white/40 mb-1">Events</div>
          {sim.events.slice(-3).map((ev, i) => (
            <div key={i} className="text-xs text-yellow-400/80 font-mono">
              ⚡ {ev.type}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
