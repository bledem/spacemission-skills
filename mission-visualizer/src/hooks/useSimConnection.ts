/**
 * WebSocket hook that connects to the sim engine server and receives
 * UniverseState each tick. Converts to the viewer's coordinate system.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const AU_KM = 149_597_870.7;
const DEFAULT_WS_URL = 'ws://localhost:8765';

// Sim engine state types (matches sim/state.py)
interface SimTime {
  elapsed_s: number;
  epoch: string; // ISO datetime
  step: number;
}

interface CelestialBodyState {
  body: number; // CelestialBody enum value
  position_km: [number, number, number];
  velocity_km_s: [number, number, number];
  mu_km3_s2: number;
  radius_km: number;
  soi_km: number;
}

interface OrbitStateData {
  elements: {
    h: number;
    e: number;
    i: number;
    Omega: number;
    omega: number;
    theta: number;
    a: number;
  };
  altitude_km: number;
  period_s: number;
  orbit_type: string;
}

interface SubsystemState {
  power: {
    status: string;
    battery_soc_pct: number;
    solar_input_w: number;
    distance_au: number;
    in_eclipse: boolean;
  };
  thermal: {
    status: string;
    propulsion_temp_c: number;
    battery_temp_c: number;
  };
  propulsion: {
    status: string;
    fuel_kg: number;
    can_fire: boolean;
    fire_inhibit_reason: string | null;
  };
  comms: {
    status: string;
    downlink_rate_kbps: number;
    in_blackout: boolean;
  };
  adcs: {
    status: string;
    pointing_error_deg: number;
    mode: string;
  };
}

interface SpacecraftState {
  id: string;
  position_km: [number, number, number];
  velocity_km_s: [number, number, number];
  mass_kg: number;
  fuel_kg: number;
  orbit: OrbitStateData;
  subsystems: SubsystemState;
  status: string;
  reference_body: number;
}

interface SimEvent {
  type: string;
  body: number | null;
  details: Record<string, unknown>;
}

interface UniverseState {
  time: SimTime;
  bodies: CelestialBodyState[];
  spacecraft: SpacecraftState[];
  events: SimEvent[];
}

// Body enum mapping (matches CelestialBody in spacecraft_sim)
const BODY_NAMES: Record<number, string> = {
  0: 'Sun', 1: 'Mercury', 2: 'Venus', 3: 'Earth', 4: 'Moon',
  5: 'Mars', 6: 'Jupiter', 7: 'Saturn', 8: 'Uranus', 9: 'Neptune',
};

// What the viewer consumes
export interface LiveSimData {
  connected: boolean;
  time: SimTime | null;
  spacecraft: {
    position_au: [number, number]; // 2D heliocentric [x, y] in AU
    altitude_km: number;
    orbit_type: string;
    eccentricity: number;
    period_s: number;
    fuel_kg: number;
    mass_kg: number;
    status: string;
    subsystems: SubsystemState;
  } | null;
  bodies: {
    name: string;
    position_au: [number, number]; // 2D heliocentric [x, y] in AU
  }[];
  events: SimEvent[];
  trajectoryHistory: [number, number][]; // Trail of spacecraft positions in AU
}

const MAX_TRAIL_POINTS = 2000;

export function useSimConnection(wsUrl: string | null = DEFAULT_WS_URL): LiveSimData {
  const [connected, setConnected] = useState(false);
  const [state, setState] = useState<UniverseState | null>(null);
  const [trail, setTrail] = useState<[number, number][]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!wsUrl) return; // disabled — don't connect
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[Sim] Connected to', wsUrl);
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data: UniverseState = JSON.parse(event.data);
        setState(data);

        // Append spacecraft position to trail
        if (data.spacecraft.length > 0) {
          const sc = data.spacecraft[0];

          // Convert spacecraft position to heliocentric AU
          // If reference_body != Sun, the position is relative to that body
          // We need to add the body's heliocentric position
          let hx = sc.position_km[0];
          let hy = sc.position_km[1];

          if (sc.reference_body !== 0) { // Not Sun
            const refBody = data.bodies.find(b => b.body === sc.reference_body);
            if (refBody) {
              hx += refBody.position_km[0];
              hy += refBody.position_km[1];
            }
          }

          const pos_au: [number, number] = [hx / AU_KM, hy / AU_KM];
          setTrail(prev => {
            const next = [...prev, pos_au];
            return next.length > MAX_TRAIL_POINTS ? next.slice(-MAX_TRAIL_POINTS) : next;
          });
        }
      } catch (e) {
        console.warn('[Sim] Failed to parse message:', e);
      }
    };

    ws.onclose = () => {
      console.log('[Sim] Disconnected');
      setConnected(false);
      // Reconnect after 2s
      reconnectRef.current = setTimeout(connect, 2000);
    };

    ws.onerror = (err) => {
      console.warn('[Sim] WebSocket error:', err);
      ws.close();
    };
  }, [wsUrl]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
  }, [connect]);

  // Transform UniverseState into viewer-friendly format
  if (!state) {
    return {
      connected,
      time: null,
      spacecraft: null,
      bodies: [],
      events: [],
      trajectoryHistory: [],
    };
  }

  const sc = state.spacecraft[0];
  let scHelioX = sc?.position_km[0] ?? 0;
  let scHelioY = sc?.position_km[1] ?? 0;

  if (sc && sc.reference_body !== 0) {
    const refBody = state.bodies.find(b => b.body === sc.reference_body);
    if (refBody) {
      scHelioX += refBody.position_km[0];
      scHelioY += refBody.position_km[1];
    }
  }

  return {
    connected,
    time: state.time,
    spacecraft: sc ? {
      position_au: [scHelioX / AU_KM, scHelioY / AU_KM],
      altitude_km: sc.orbit.altitude_km,
      orbit_type: sc.orbit.orbit_type,
      eccentricity: sc.orbit.elements.e,
      period_s: sc.orbit.period_s,
      fuel_kg: sc.fuel_kg,
      mass_kg: sc.mass_kg,
      status: sc.status,
      subsystems: sc.subsystems,
    } : null,
    bodies: state.bodies.map(b => ({
      name: BODY_NAMES[b.body] ?? `Body ${b.body}`,
      position_au: [b.position_km[0] / AU_KM, b.position_km[1] / AU_KM] as [number, number],
    })),
    events: state.events,
    trajectoryHistory: trail,
  };
}
