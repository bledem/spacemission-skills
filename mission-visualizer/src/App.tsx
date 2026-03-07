import { useState, useEffect, useCallback, useMemo } from 'react';
import { Scoreboard } from './components/Scoreboard';
import { DeltaVBudget } from './components/DeltaVBudget';
import { SolarSystemView } from './components/SolarSystemView';
import { Timeline } from './components/Timeline';
import { useMissionData } from './hooks/useMissionData';
import sampleMission from './data/sampleMission.json';
import generatedMission from './data/generatedMission.json';
import './index.css';

function App() {
  // Use generated mission if available, otherwise fall back to sample
  const missionData = useMemo(() => {
    // Check URL params for mission selection
    const params = new URLSearchParams(window.location.search);
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
  }, []);

  const { mission, isLoading, error } = useMissionData(missionData);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
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
          <SolarSystemView
            mission={mission}
            showOuterPlanets={showOuterPlanets}
            currentTime={currentTime}
          />

          <Timeline
            mission={mission}
            currentTime={currentTime}
            onTimeChange={handleTimeChange}
            isPlaying={isPlaying}
            onPlayPause={handlePlayPause}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
