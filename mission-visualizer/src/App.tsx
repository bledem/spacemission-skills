import { useState, useEffect, useCallback, useMemo } from 'react';
import { Scoreboard } from './components/Scoreboard';
import { DeltaVBudget } from './components/DeltaVBudget';
import { SolarSystemView } from './components/SolarSystemView';
import { Timeline } from './components/Timeline';
import { LiveView } from './components/LiveView';
import { Telemetry } from './components/Telemetry';
import { MissionObjectivePanel, DEFAULT_OBJECTIVE } from './components/MissionObjectivePanel';
import { MissionLog } from './components/MissionLog';
import { useMissionData } from './hooks/useMissionData';
import { useSimConnection } from './hooks/useSimConnection';
import sampleMission from './data/sampleMission.json';
import generatedMission from './data/generatedMission.json';
import './index.css';

const CAPTURE_SERVER = 'http://localhost:8788';

function PromptMode() {
  const [objective, setObjective] = useState(
    () => localStorage.getItem('missionObjective') ?? DEFAULT_OBJECTIVE
  );
  const [status, setStatus] = useState<'idle' | 'submitting' | 'sent'>('idle');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async () => {
    setStatus('submitting');
    setError(null);
    try {
      localStorage.setItem('missionObjective', objective);
      await fetch(`${CAPTURE_SERVER}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ objective }),
      });
      setStatus('sent');
    } catch (e) {
      setError(`Could not reach capture server at ${CAPTURE_SERVER}. Is the script running?`);
      setStatus('idle');
    }
  }, [objective]);

  if (status === 'sent') {
    // Redirect to main visualizer — AgentFeed is embedded there and will auto-connect
    window.location.href = '/';
    return null;
  }

  return (
    <div className="min-h-screen bg-space-bg flex flex-col items-center justify-center text-white p-8">
      <div className="w-full max-w-2xl space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white/90">Deep Space Explorer</h1>
          <p className="text-white/50 mt-1">Configure your mission objective before the agent runs.</p>
        </div>

        <div className="bg-space-bg/80 backdrop-blur-sm border border-white/10 rounded-lg p-6 space-y-4">
          <label className="block">
            <span className="text-sm font-semibold text-white/70 block mb-2">Mission Objective</span>
            <textarea
              className="w-full bg-black/40 border border-white/10 rounded p-3 text-sm text-white/90 font-mono resize-y min-h-[120px] focus:outline-none focus:border-white/30 leading-relaxed"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              disabled={status === 'submitting'}
            />
          </label>

          <div className="bg-black/20 rounded p-3 text-xs text-white/40 font-mono">
            <span className="text-white/30">instruction.md template: </span>
            <span className="text-white/50">You are a spacecraft mission designer. Your goal is to </span>
            <span className="text-blue-400/70">{'{{MISSION_OBJECTIVE}}'}</span>
          </div>

          {error && (
            <p className="text-red-400 text-xs">{error}</p>
          )}

          <div className="flex gap-3">
            <button
              className="text-xs text-white/40 hover:text-white/60 px-3 py-1.5 border border-white/10 rounded transition-colors"
              onClick={() => setObjective(DEFAULT_OBJECTIVE)}
              disabled={status === 'submitting'}
            >
              Reset to default
            </button>
            <button
              className="flex-1 bg-blue-700 hover:bg-blue-600 disabled:bg-blue-900/50 disabled:text-white/30 text-white font-semibold rounded px-4 py-2 transition-colors text-sm"
              onClick={handleSubmit}
              disabled={status === 'submitting' || !objective.trim()}
            >
              {status === 'submitting' ? 'Launching...' : 'Run Mission'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function App() {
  // Check URL params for mode selection
  const params = useMemo(() => new URLSearchParams(window.location.search), []);
  const isLiveMode = params.get('mode') === 'live';
  const isPromptMode = params.get('mode') === 'prompt';
  const wsUrl = params.get('ws') ?? undefined; // optional custom WS URL

  // Use generated mission if available, otherwise fall back to sample
  const missionData = useMemo(() => {
    const missionParam = params.get('mission');

    if (missionParam === 'sample') {
      return sampleMission;
    }
    if (missionParam === 'generated') {
      return generatedMission;
    }

    // Default: use generated if it has valid data, otherwise sample
    if (generatedMission && generatedMission.mission_name) {
      return generatedMission;
    }
    return sampleMission;
  }, [params]);

  const sim = useSimConnection(isLiveMode ? (wsUrl ?? 'ws://localhost:8765') : null);
  const { mission, isLoading, error } = useMissionData(missionData);
  const [missionObjective, setMissionObjective] = useState<string>(
    () => localStorage.getItem('missionObjective') ?? DEFAULT_OBJECTIVE
  );
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(() => params.get('autoplay') === '1');
  const [showOuterPlanets, setShowOuterPlanets] = useState(false);

  // Animation loop
  useEffect(() => {
    if (!isPlaying) return;

    const animationSpeed = 0.001; // Adjust for playback speed
    const interval = setInterval(() => {
      setCurrentTime((t) => {
        const next = t + animationSpeed;
        if (next >= 1) {
          setIsPlaying(false);
          return 1;
        }
        return next;
      });
    }, 16); // ~60fps

    return () => clearInterval(interval);
  }, [isPlaying]);

  const handleTimeChange = useCallback((time: number) => {
    setCurrentTime(time);
  }, []);

  const handlePlayPause = useCallback(() => {
    setIsPlaying((prev) => !prev);
  }, []);

  const handleObjectiveChange = useCallback((value: string) => {
    setMissionObjective(value);
    localStorage.setItem('missionObjective', value);
  }, []);

  const [agentActive, setAgentActive] = useState(false);

  // --- Prompt capture mode ---
  if (isPromptMode) {
    return <PromptMode />;
  }

  // --- Live sim mode ---
  if (isLiveMode) {
    return (
      <div className="min-h-screen bg-space-bg text-white p-4">
        <header className="mb-4 flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white/90">Mission Control</h1>
          <span className={`px-2 py-0.5 rounded text-xs font-mono ${sim.connected ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
            {sim.connected ? 'CONNECTED' : 'CONNECTING...'}
          </span>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Left sidebar — telemetry */}
          <div className="lg:col-span-1 space-y-4">
            <Telemetry sim={sim} />

            {/* View controls */}
            <div className="bg-space-bg/80 backdrop-blur-sm border border-white/10 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-white/70 mb-2">View Options</h3>
              <label className="flex items-center gap-2 text-sm text-white/70 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showOuterPlanets}
                  onChange={(e) => setShowOuterPlanets(e.target.checked)}
                  className="rounded"
                />
                Show outer planets
              </label>
            </div>
          </div>

          {/* Main visualization area */}
          <div className="lg:col-span-3">
            <LiveView sim={sim} showOuterPlanets={showOuterPlanets} />
          </div>
        </div>
      </div>
    );
  }

  // --- Static mission mode ---
  if (isLoading) {
    return (
      <div className="min-h-screen bg-space-bg flex items-center justify-center text-white">
        Loading mission data...
      </div>
    );
  }

  if (error || !mission) {
    return (
      <div className="min-h-screen bg-space-bg flex items-center justify-center text-red-400">
        Error: {error || 'Failed to load mission'}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-space-bg text-white p-4">
      <header className="mb-4">
        <h1 className="text-2xl font-bold text-white/90">Deep Space Explorer</h1>
        <p className="text-white/50">Mission Visualizer</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Left sidebar */}
        <div className="lg:col-span-1 space-y-4">
          <MissionObjectivePanel
            objective={missionObjective}
            onChange={handleObjectiveChange}
          />
          <Scoreboard mission={mission} />
          <DeltaVBudget
            phases={mission.phases}
            totalDeltaV={mission.total_delta_v_km_s}
          />

          {/* View controls */}
          <div className="bg-space-bg/80 backdrop-blur-sm border border-white/10 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-white/70 mb-2">View Options</h3>
            <label className="flex items-center gap-2 text-sm text-white/70 cursor-pointer">
              <input
                type="checkbox"
                checked={showOuterPlanets}
                onChange={(e) => setShowOuterPlanets(e.target.checked)}
                className="rounded"
              />
              Show outer planets
            </label>
          </div>
        </div>

        {/* Main visualization area */}
        <div className="lg:col-span-3 space-y-4">
          <div className="relative">
            <SolarSystemView
              mission={mission}
              showOuterPlanets={showOuterPlanets}
              currentTime={currentTime}
            />
            {agentActive && !params.get('mission') && (
              <div className="absolute inset-0 bg-space-bg/70 backdrop-blur-sm rounded-lg flex flex-col items-center justify-center gap-3">
                <div className="w-8 h-8 border-2 border-blue-400/60 border-t-blue-400 rounded-full animate-spin" />
                <p className="text-white/60 text-sm font-mono">Agent computing new trajectory…</p>
              </div>
            )}
          </div>

          {(!agentActive || params.get('mission')) && (
            <Timeline
              mission={mission}
              currentTime={currentTime}
              onTimeChange={handleTimeChange}
              isPlaying={isPlaying}
              onPlayPause={handlePlayPause}
            />
          )}

          {!params.get('mission') && <MissionLog onAgentActive={setAgentActive} />}
        </div>
      </div>
    </div>
  );
}

export default App;
