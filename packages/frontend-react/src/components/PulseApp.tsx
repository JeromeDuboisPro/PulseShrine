import { Heart, Moon, Mountain, Pause, Play, RotateCcw, Sparkles, Target, Zap, Settings } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { ApiError, IngestedPulse, PulseAPI, StartPulse, StopPulse } from '../api';
import { ApiConfig, updateConfig } from '../config';
import { ConfigurationModal } from './ConfigurationModal';

interface PulseAppProps {
  config: ApiConfig;
  onReconfigure: () => void;
}

export const PulseApp: React.FC<PulseAppProps> = ({ config, onReconfigure }) => {
  const [currentView, setCurrentView] = useState('shrine');
  const [activePulse, setActivePulse] = useState<StartPulse | null>(null);
  const [timeLeft, setTimeLeft] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [completedPulses, setCompletedPulses] = useState<IngestedPulse[]>([]);
  const [stoppedPulses, setStoppedPulses] = useState<StopPulse[]>([]);
  const [intention, setIntention] = useState('');
  const [selectedEnergy, setSelectedEnergy] = useState('creation');
  const [duration, setDuration] = useState(25);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const userIdRef = useRef(config.userId);
  const loadPulsesRef = useRef<(() => Promise<void>) | null>(null);

  // Calculate remaining time for an active pulse
  const calculateRemainingTime = (pulse: StartPulse): number => {
    if (!pulse.duration_seconds) return 0;
    
    // Handle both timestamp (seconds) and start_time (ISO string) formats
    let startTimeUtc: number;
    if (pulse.start_time) {
      // Handle timezone-aware or timezone-naive ISO strings
      let startDate: Date;
      if (pulse.start_time.includes('Z') || pulse.start_time.includes('+') || pulse.start_time.includes('-')) {
        // Timezone-aware ISO string
        startDate = new Date(pulse.start_time);
      } else {
        // Timezone-naive ISO string - assume UTC
        startDate = new Date(pulse.start_time + 'Z');
      }
      
      if (isNaN(startDate.getTime())) {
        console.warn('Invalid start_time format:', pulse.start_time);
        return 0;
      }
      startTimeUtc = startDate.getTime();
    } else if (pulse.timestamp) {
      startTimeUtc = pulse.timestamp * 1000; // Convert to milliseconds
    } else {
      console.warn('Pulse has no start_time or timestamp:', pulse);
      return 0;
    }
    
    // Use UTC time for calculations
    const nowUtc = Date.now();
    const elapsed = Math.floor((nowUtc - startTimeUtc) / 1000); // Convert to seconds
    const remaining = Math.max(0, pulse.duration_seconds - elapsed);
    
    console.log('Time calculation (timezone-aware):', { 
      start_time: pulse.start_time, 
      startTimeUtc: new Date(startTimeUtc).toISOString(),
      nowUtc: new Date(nowUtc).toISOString(),
      elapsed, 
      duration: pulse.duration_seconds, 
      remaining,
      startTimeLocal: new Date(startTimeUtc).toString(),
      nowLocal: new Date(nowUtc).toString()
    });
    
    return remaining;
  };

  // Energy icons mapping
  const energyIcons = {
    creation: { icon: Sparkles, color: 'text-purple-500', bg: 'bg-purple-100' },
    focus: { icon: Target, color: 'text-blue-500', bg: 'bg-blue-100' },
    brainstorm: { icon: Zap, color: 'text-yellow-500', bg: 'bg-yellow-100' },
    study: { icon: Heart, color: 'text-green-500', bg: 'bg-green-100' },
    planning: { icon: Mountain, color: 'text-gray-500', bg: 'bg-gray-100' },
    reflection: { icon: Moon, color: 'text-indigo-500', bg: 'bg-indigo-100' }
  };


  // Update global config on mount (one time only)
  useEffect(() => {
    updateConfig(config);
  }, []); // Empty dependency array - only run once

  // Initialize and set up polling - SIMPLIFIED to avoid dependency loops
  useEffect(() => {
    console.log('App initialized, loading initial data...');
    
    // Define the load function inline to avoid dependency issues
    const doLoadPulses = async () => {
      try {
        setError(null);
        const [ingested, stopped, started] = await Promise.all([
          PulseAPI.getIngestedPulses(userIdRef.current),
          PulseAPI.getStopPulses(userIdRef.current),
          PulseAPI.getStartPulse(userIdRef.current)
        ]);
        
        setActivePulse(started);
        setCompletedPulses(ingested.sort((a, b) => b.inverted_timestamp - a.inverted_timestamp));
        setStoppedPulses(stopped);
        
        // If there's an active pulse, calculate remaining time and set duration
        if (started && started.duration_seconds) {
          const remaining = calculateRemainingTime(started);
          setTimeLeft(remaining);
          setDuration(Math.ceil(started.duration_seconds / 60)); // Convert back to minutes for UI
          
          // Only go to emotion if time has truly expired (with a small buffer for timing issues)
          if (remaining <= 5) { // 5 second buffer
            setCurrentView('emotion');
          }
        }
        
        console.log('Loaded pulses:', { started, stopped: stopped.length, ingested: ingested.length });
      } catch (err) {
        const errorMessage = err instanceof ApiError 
          ? err.message 
          : 'Failed to load pulses. Please check your API configuration.';
        setError(errorMessage);
        console.error('Failed to load pulses:', err);
      }
    };
    
    // Store function reference for other parts of the app
    loadPulsesRef.current = doLoadPulses;
    
    // Initial load
    doLoadPulses();
    
    // Poll for updates every 30 seconds
    const pollInterval = setInterval(() => {
      console.log('Polling for updates...');
      doLoadPulses();
    }, 30000);
    
    return () => {
      console.log('Cleaning up polling interval');
      clearInterval(pollInterval);
    };
  }, []); // Empty dependency array - only run once on mount

  // Timer logic
  useEffect(() => {
    if (isRunning && timeLeft > 0) {
      intervalRef.current = setInterval(() => {
        setTimeLeft(prev => {
          if (prev <= 1) {
            setIsRunning(false);
            setCurrentView('emotion');
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isRunning, timeLeft]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Format UTC ISO string for display in user's local timezone
  const formatLocalTime = (utcIsoString: string) => {
    try {
      const date = new Date(utcIsoString);
      return date.toLocaleTimeString();
    } catch (error) {
      console.warn('Invalid date format:', utcIsoString);
      return 'Unknown time';
    }
  };

  const startNewPulse = async () => {
    if (!intention.trim()) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const pulse = await PulseAPI.startPulse(userIdRef.current, intention, duration * 60, selectedEnergy);
      setActivePulse(pulse);
      setTimeLeft(duration * 60);
      setCurrentView('timer');
      setIsRunning(true); // Auto-start the timer for new pulse
      
      // Refresh pulses to show the new active pulse in shrine
      if (loadPulsesRef.current) {
        await loadPulsesRef.current();
      }
    } catch (err) {
      const errorMessage = err instanceof ApiError 
        ? err.message 
        : 'Failed to start pulse. Please try again.';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleTimer = () => {
    setIsRunning(!isRunning);
  };

  const stopPulse = () => {
    setIsRunning(false);
    setCurrentView('emotion');
  };

  const resetTimer = () => {
    if (activePulse && activePulse.duration_seconds) {
      setTimeLeft(activePulse.duration_seconds);
      setIsRunning(false);
    } else if (activePulse) {
      setTimeLeft(duration * 60);
      setIsRunning(false);
    }
  };

  const submitEmotion = async (emotion: string, reflection = '') => {
    if (!activePulse) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      await PulseAPI.stopPulse(userIdRef.current, reflection, emotion);
      
      // Reset state
      setActivePulse(null);
      setIntention('');
      setSelectedEnergy('creation');
      setDuration(25);
      setCurrentView('shrine');
      
      // Refresh pulses to show the completed pulse
      if (loadPulsesRef.current) {
        await loadPulsesRef.current();
      }
    } catch (err) {
      const errorMessage = err instanceof ApiError 
        ? err.message 
        : 'Failed to complete pulse. Please try again.';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const GuardianMessage = ({ children }: { children: React.ReactNode }) => (
    <div className="bg-gradient-to-r from-purple-100 to-blue-100 p-4 rounded-lg border border-purple-200 mb-6">
      <div className="flex items-start space-x-3">
        <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center text-white font-bold">
          G
        </div>
        <div className="flex-1">
          <p className="text-gray-700 italic">{children}</p>
        </div>
      </div>
    </div>
  );

  const ErrorMessage = ({ message, onClose }: { message: string; onClose: () => void }) => (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
      <div className="flex items-start justify-between">
        <div className="flex">
          <div className="text-red-400 mr-3">⚠️</div>
          <div>
            <h3 className="text-sm font-medium text-red-800">Error</h3>
            <p className="text-sm text-red-700 mt-1">{message}</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-red-400 hover:text-red-600 ml-4"
        >
          ×
        </button>
      </div>
    </div>
  );

  const renderShrine = () => {
    // Combine all pulses for display
    const ingestedIdsSet = new Set(completedPulses.map(p => p.pulse_id));
    const curatedStoppedPulses = stoppedPulses.filter(p => !ingestedIdsSet.has(p.pulse_id));
    
    let displayPulses = [...completedPulses];
    const maxRunes = 18;
    
    // Add stopped pulses that haven't been ingested yet (processing state)
    curatedStoppedPulses.forEach(pulse => {
      if (displayPulses.length < maxRunes) {
        displayPulses.push({
          ...pulse,
          gen_title: pulse.gen_title || '⚡ Processing...',
          gen_badge: '⏳', // Processing indicator
          processing: true // Add flag to identify processing pulses
        } as IngestedPulse & { processing: boolean });
      }
    });

    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 via-blue-50 to-purple-50 p-6">
        <div className="max-w-4xl mx-auto">
          <header className="text-center mb-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex-1"></div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                Pulse Shrine
              </h1>
              <div className="flex-1 flex justify-end">
                <button
                  onClick={() => setShowConfigModal(true)}
                  className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                  title="API Settings"
                >
                  <Settings className="w-5 h-5" />
                </button>
              </div>
            </div>
            <p className="text-gray-600">Sacred space of mindful productivity</p>
            <p className="text-xs text-gray-500 mt-1">Connected to: {config.apiBaseUrl}</p>
          </header>

          {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

          <GuardianMessage>
            Welcome to your sacred shrine, seeker. Here, your completed pulses transform into powerful runes that enhance the tranquility of this space. Each intention you fulfill adds to the mystical energy surrounding us.
          </GuardianMessage>

          <div className="relative bg-gradient-to-br from-slate-100 via-green-50 to-blue-50 rounded-xl p-8 mb-8 border border-slate-200 overflow-hidden">
            {/* Zen Garden Background */}
            <div className="absolute inset-0 opacity-20">
              <svg className="w-full h-full" viewBox="0 0 800 400" fill="none">
                {/* Water pond */}
                <ellipse cx="600" cy="280" rx="120" ry="60" fill="#4A90E2" opacity="0.3"/>
                <ellipse cx="600" cy="280" rx="100" ry="50" fill="#6BA3F0" opacity="0.2"/>
                
                {/* Ripples */}
                <ellipse cx="580" cy="270" rx="8" ry="4" fill="none" stroke="#4A90E2" strokeWidth="1" opacity="0.4"/>
                <ellipse cx="620" cy="290" rx="12" ry="6" fill="none" stroke="#4A90E2" strokeWidth="1" opacity="0.3"/>
                
                {/* Stepping stones */}
                <circle cx="150" cy="320" r="25" fill="#8B7355" opacity="0.3"/>
                <circle cx="220" cy="300" r="30" fill="#9B8365" opacity="0.3"/>
                <circle cx="300" cy="280" r="28" fill="#8B7355" opacity="0.3"/>
                
                {/* Zen rocks */}
                <ellipse cx="100" cy="200" rx="40" ry="25" fill="#A8A8A8" opacity="0.4"/>
                <ellipse cx="750" cy="150" rx="35" ry="20" fill="#B8B8B8" opacity="0.3"/>
                
                {/* Bamboo silhouettes */}
                <rect x="50" y="50" width="8" height="150" fill="#4A7C59" opacity="0.3"/>
                <rect x="65" y="40" width="6" height="140" fill="#5A8C69" opacity="0.3"/>
                <rect x="78" y="60" width="7" height="130" fill="#4A7C59" opacity="0.3"/>
                
                {/* Subtle wave patterns */}
                <path d="M0,350 Q100,340 200,350 T400,350" stroke="#4A90E2" strokeWidth="2" fill="none" opacity="0.2"/>
                <path d="M400,360 Q500,350 600,360 T800,360" stroke="#4A90E2" strokeWidth="2" fill="none" opacity="0.2"/>
              </svg>
            </div>
            
            {/* Floating particles */}
            <div className="absolute inset-0 pointer-events-none">
              <div className="absolute top-20 left-10 w-1 h-1 bg-green-300 rounded-full opacity-40 animate-pulse"></div>
              <div className="absolute top-32 right-20 w-1 h-1 bg-blue-300 rounded-full opacity-40 animate-pulse" style={{animationDelay: '1s'}}></div>
              <div className="absolute bottom-40 left-1/3 w-1 h-1 bg-slate-300 rounded-full opacity-40 animate-pulse" style={{animationDelay: '2s'}}></div>
            </div>

            <h2 className="relative text-2xl font-light text-slate-700 mb-8 flex items-center">
              <div className="mr-3 text-green-600">🌸</div>
              Sacred Zen Garden
              <div className="ml-3 text-blue-500">💧</div>
            </h2>
            
            {displayPulses.length === 0 && !activePulse ? (
              <div className="relative text-center py-16">
                <div className="text-5xl mb-4 animate-pulse">🌱</div>
                <p className="text-slate-500 font-light">Your tranquil garden awaits its first sacred stone...</p>
                <div className="mt-4 text-xs text-slate-400">Each completed pulse becomes a mindful rune in this peaceful space</div>
              </div>
            ) : (
              <div className="relative">
                <div className="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3 mb-6">
                  {/* Show active pulse first if exists */}
                  {activePulse && (
                    <div className="group flex items-center justify-center">
                      <div className="relative">
                        <div className="bg-gradient-to-br from-yellow-100/80 to-orange-50/80 backdrop-blur-sm p-3 rounded-full border border-yellow-200/50 hover:shadow-lg transition-all duration-500 cursor-pointer animate-pulse-slow group-hover:scale-110 group-hover:rotate-3 origin-center">
                          <div className="text-xl text-center">⏳</div>
                          <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-gradient-to-br from-yellow-200 to-orange-300 flex items-center justify-center">
                            <Target className="w-2 h-2 text-orange-600" />
                          </div>
                        </div>
                        <div className="absolute bottom-full mb-3 left-1/2 transform -translate-x-1/2 bg-slate-800/90 backdrop-blur-sm text-white px-3 py-2 rounded-lg text-xs opacity-0 group-hover:opacity-100 transition-all duration-300 whitespace-nowrap z-50 max-w-xs shadow-lg pointer-events-none">
                          <div className="font-medium text-slate-100">{activePulse.intent}</div>
                          <div className="text-slate-300 mt-1">Active pulse in progress...</div>
                          <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-slate-800/90"></div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Show completed pulses */}
                  {displayPulses.map((pulse, index) => {
                    const symbol = pulse.gen_badge?.trim().split(' ')[0] || '✨';
                    const isProcessing = (pulse as any).processing;
                    return (
                      <div key={pulse.pulse_id} className="group flex items-center justify-center">
                        <div className="relative">
                          <div 
                            className={`backdrop-blur-sm p-3 rounded-full border hover:shadow-lg transition-all duration-500 cursor-pointer group-hover:scale-110 group-hover:rotate-3 origin-center ${
                              isProcessing 
                                ? 'bg-gradient-to-br from-yellow-100/80 to-orange-100/80 border-yellow-300/50 animate-pulse' 
                                : 'bg-gradient-to-br from-white/80 to-slate-50/80 border-slate-200/50'
                            }`}
                            style={{
                              animationDelay: `${index * 0.1}s`,
                              animation: isProcessing ? 'fadeInUp 0.6s ease-out forwards, pulse 2s infinite' : 'fadeInUp 0.6s ease-out forwards'
                            }}
                          >
                            <div className={`text-xl text-center ${isProcessing ? 'animate-spin' : ''}`}>{symbol}</div>
                          </div>
                          <div className={`absolute bottom-full mb-3 left-1/2 transform -translate-x-1/2 backdrop-blur-sm text-white px-3 py-2 rounded-lg text-xs opacity-0 group-hover:opacity-100 transition-all duration-300 whitespace-nowrap z-50 max-w-xs shadow-lg pointer-events-none ${
                            isProcessing ? 'bg-yellow-800/90' : 'bg-slate-800/90'
                          }`}>
                            <div className="font-medium text-slate-100">
                              {isProcessing ? '⚡ ' : ''}{pulse.gen_title || pulse.intent}
                            </div>
                            {pulse.reflection && (
                              <div className="text-slate-300 mt-1 whitespace-normal italic max-w-48">"{pulse.reflection}"</div>
                            )}
                            {isProcessing && (
                              <div className="text-yellow-300 mt-1 text-xs animate-pulse">Processing your sacred rune...</div>
                            )}
                            <div className={`absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent ${
                              isProcessing ? 'border-t-yellow-800/90' : 'border-t-slate-800/90'
                            }`}></div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                
                {/* Koi fish swimming animation */}
                <div className="absolute bottom-4 right-8 opacity-30">
                  <div className="text-2xl animate-pulse" style={{animationDuration: '3s'}}>🐟</div>
                </div>
                <div className="absolute bottom-8 right-16 opacity-20">
                  <div className="text-xl animate-pulse" style={{animationDuration: '4s', animationDelay: '1s'}}>🐠</div>
                </div>
              </div>
            )}
          </div>

          <div className="bg-white/70 backdrop-blur-sm rounded-xl p-6 border border-white/50">
            {activePulse ? (
              <div className="space-y-4">
                <div className="bg-gradient-to-r from-yellow-50 to-orange-50 p-4 rounded-lg border border-yellow-200">
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="font-semibold text-gray-800">Active Pulse in Progress</span>
                  </div>
                  <p className="text-gray-700 font-medium">"{activePulse.intent}"</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Started: {
                      activePulse.start_time 
                        ? formatLocalTime(activePulse.start_time)
                        : activePulse.timestamp 
                          ? new Date(activePulse.timestamp * 1000).toLocaleTimeString()
                          : 'Unknown'
                    }
                  </p>
                  {activePulse.duration_seconds && (
                    <p className="text-xs text-gray-600 mt-1">
                      Time remaining: {formatTime(calculateRemainingTime(activePulse))}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => {
                    if (activePulse && activePulse.duration_seconds) {
                      const remaining = calculateRemainingTime(activePulse);
                      setTimeLeft(remaining);
                      setDuration(Math.ceil(activePulse.duration_seconds / 60));
                      
                      if (remaining > 0) {
                        setCurrentView('timer');
                        setIsRunning(true); // Auto-start the timer when resuming
                      } else {
                        setCurrentView('emotion');
                      }
                    } else {
                      setCurrentView('timer');
                      setIsRunning(true); // Auto-start the timer when resuming
                    }
                  }}
                  className="w-full bg-gradient-to-r from-green-500 to-emerald-500 text-white py-4 px-6 rounded-lg font-semibold hover:from-green-600 hover:to-emerald-600 transition-all duration-300 flex items-center justify-center space-x-2"
                >
                  <Target className="w-5 h-5" />
                  <span>Continue Active Pulse</span>
                </button>
              </div>
            ) : (
              <button
                onClick={() => setCurrentView('create')}
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-purple-500 to-blue-500 text-white py-4 px-6 rounded-lg font-semibold hover:from-purple-600 hover:to-blue-600 transition-all duration-300 flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-5 h-5" />
                <span>{isLoading ? 'Loading...' : 'Begin New Pulse'}</span>
              </button>
            )}
          </div>

          {(displayPulses.length > 0 || activePulse) && (
            <div className="mt-6 text-center">
              <p className="text-sm text-gray-600">
                You have manifested {displayPulses.length + (activePulse ? 1 : 0)} sacred rune{displayPulses.length + (activePulse ? 1 : 0) !== 1 ? 's' : ''}
                {activePulse && ' (1 in progress)'}
                {curatedStoppedPulses.length > 0 && (
                  <span className="text-yellow-600 font-medium">
                    {' '}• {curatedStoppedPulses.length} processing ⚡
                  </span>
                )}
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderCreate = () => (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-blue-50 to-purple-50 p-6">
      <div className="max-w-2xl mx-auto">
        <button
          onClick={() => setCurrentView('shrine')}
          className="mb-6 text-gray-600 hover:text-gray-800 transition-colors"
        >
          ← Back to Shrine
        </button>

        {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

        <GuardianMessage>
          Speak your intention into existence, dear seeker. Choose the energy that resonates with your purpose, and let us begin this sacred pulse together.
        </GuardianMessage>

        <div className="bg-white/70 backdrop-blur-sm rounded-xl p-8 border border-white/50">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">Create Your Pulse</h2>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Your Intention
              </label>
              <input
                type="text"
                value={intention}
                onChange={(e) => setIntention(e.target.value)}
                placeholder="What do you wish to accomplish?"
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Choose Your Energy
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(energyIcons).map(([key, { icon: Icon, color }]) => (
                  <button
                    key={key}
                    onClick={() => setSelectedEnergy(key)}
                    className={`p-4 rounded-lg border-2 transition-all duration-200 ${
                      selectedEnergy === key
                        ? 'border-purple-500 bg-purple-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <Icon className={`w-6 h-6 mx-auto mb-2 ${color}`} />
                    <span className="text-sm font-medium capitalize">{key}</span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Duration (minutes)
              </label>
              <select
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value={15}>15 minutes</option>
                <option value={25}>25 minutes</option>
                <option value={45}>45 minutes</option>
                <option value={60}>60 minutes</option>
              </select>
            </div>

            <button
              onClick={startNewPulse}
              disabled={!intention.trim() || isLoading}
              className="w-full bg-gradient-to-r from-purple-500 to-blue-500 text-white py-4 px-6 rounded-lg font-semibold hover:from-purple-600 hover:to-blue-600 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            >
              <Target className="w-5 h-5" />
              <span>{isLoading ? 'Starting...' : 'Begin Pulse'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderTimer = () => {
    if (!activePulse) {
      setCurrentView('shrine');
      return null;
    }

    const EnergyIcon = energyIcons[selectedEnergy as keyof typeof energyIcons]?.icon || Target;
    const totalDuration = activePulse.duration_seconds || (duration * 60);
    const progress = timeLeft > 0 ? ((totalDuration - timeLeft) / totalDuration) * 100 : 100;

    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-blue-900 p-6 text-white">
        <div className="max-w-2xl mx-auto text-center">
          <div className="bg-gradient-to-r from-purple-100 to-blue-100 p-4 rounded-lg border border-purple-200 mb-6">
            <div className="flex items-start space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center text-white font-bold">
                G
              </div>
              <div className="flex-1">
                <p className="text-gray-700 italic">Focus your energy, seeker. Let your intention guide you through this sacred time. I am here, watching over your progress.</p>
              </div>
            </div>
          </div>

          {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-8 border border-white/20 mb-8">
            <div className="mb-6">
              <EnergyIcon className={`w-12 h-12 mx-auto mb-4 ${energyIcons[selectedEnergy as keyof typeof energyIcons]?.color || 'text-purple-500'}`} />
              <h3 className="text-xl font-semibold mb-2">{activePulse.intent}</h3>
              <p className="text-sm text-gray-300 capitalize">{selectedEnergy} energy</p>
            </div>

            <div className="relative w-48 h-48 mx-auto mb-8">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  stroke="rgba(255,255,255,0.2)"
                  strokeWidth="8"
                  fill="none"
                />
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  stroke="url(#gradient)"
                  strokeWidth="8"
                  fill="none"
                  strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 45}`}
                  strokeDashoffset={`${2 * Math.PI * 45 * (1 - progress / 100)}`}
                  className="transition-all duration-1000"
                />
                <defs>
                  <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#8B5CF6" />
                    <stop offset="100%" stopColor="#3B82F6" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-4xl font-bold">{formatTime(timeLeft)}</div>
              </div>
            </div>

            <div className="flex justify-center space-x-4 mb-6">
              <button
                onClick={toggleTimer}
                className="bg-white/20 hover:bg-white/30 p-4 rounded-full transition-colors"
              >
                {isRunning ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
              </button>
              <button
                onClick={resetTimer}
                className="bg-white/20 hover:bg-white/30 p-4 rounded-full transition-colors"
              >
                <RotateCcw className="w-6 h-6" />
              </button>
            </div>

            <button
              onClick={stopPulse}
              className="bg-red-500/80 hover:bg-red-600/80 text-white px-6 py-2 rounded-lg transition-colors text-sm"
            >
              Complete Pulse Early
            </button>
          </div>

          <button
            onClick={() => setCurrentView('shrine')}
            className="text-gray-300 hover:text-white transition-colors"
          >
            Return to Shrine
          </button>
        </div>
      </div>
    );
  };

  const [selectedEmotion, setSelectedEmotion] = useState('');
  const [customReflection, setCustomReflection] = useState('');

  const renderEmotion = () => {
    const emotions = [
      { key: 'fulfilled', label: 'Fulfilled', icon: '⚡', desc: 'I accomplished my intention completely' },
      { key: 'peaceful', label: 'Peaceful', icon: '🌙', desc: 'I feel calm and centered' },
      { key: 'energized', label: 'Energized', icon: '☀️', desc: 'I feel motivated and powerful' },
      { key: 'focused', label: 'Focused', icon: '🎯', desc: 'I maintained clear concentration' },
      { key: 'creative', label: 'Creative', icon: '✨', desc: 'I felt inspired and innovative' },
      { key: 'grounded', label: 'Grounded', icon: '🌿', desc: 'I feel stable and connected' }
    ];

    const handleSubmit = () => {
      if (selectedEmotion) {
        submitEmotion(selectedEmotion, customReflection);
        setSelectedEmotion('');
        setCustomReflection('');
      }
    };

    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 via-blue-50 to-purple-50 p-6">
        <div className="max-w-2xl mx-auto">
          
          {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

          <GuardianMessage>
            Your pulse is complete, brave seeker. Now, reflect upon your journey and choose the emotion that best captures your experience. Share your thoughts if you wish - this will become the essence of your new rune.
          </GuardianMessage>

          <div className="bg-white/70 backdrop-blur-sm rounded-xl p-8 border border-white/50">
            <h2 className="text-2xl font-semibold text-gray-800 mb-6 text-center">
              How do you feel about your pulse?
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {emotions.map((emotion) => (
                <button
                  key={emotion.key}
                  onClick={() => setSelectedEmotion(emotion.key)}
                  className={`p-6 text-left border-2 rounded-lg transition-all duration-200 group ${
                    selectedEmotion === emotion.key
                      ? 'border-purple-500 bg-purple-50'
                      : 'border-gray-200 hover:border-purple-300 hover:bg-purple-25'
                  }`}
                >
                  <div className="flex items-center space-x-4">
                    <span className="text-3xl">{emotion.icon}</span>
                    <div>
                      <h3 className={`font-semibold ${
                        selectedEmotion === emotion.key 
                          ? 'text-purple-700' 
                          : 'text-gray-800 group-hover:text-purple-700'
                      }`}>
                        {emotion.label}
                      </h3>
                      <p className="text-sm text-gray-600">{emotion.desc}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Share your reflection (optional)
              </label>
              <textarea
                value={customReflection}
                onChange={(e) => setCustomReflection(e.target.value)}
                placeholder="What did you learn? How did it feel? What would you do differently?"
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                rows={4}
              />
            </div>

            <button
              onClick={handleSubmit}
              disabled={!selectedEmotion || isLoading}
              className="w-full bg-gradient-to-r from-purple-500 to-blue-500 text-white py-4 px-6 rounded-lg font-semibold hover:from-purple-600 hover:to-blue-600 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            >
              <Sparkles className="w-5 h-5" />
              <span>{isLoading ? 'Creating...' : 'Create Sacred Rune'}</span>
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Main render logic
  const renderCurrentView = () => {
    if (currentView === 'shrine') {
      return renderShrine();
    } else if (currentView === 'create') {
      return renderCreate();
    } else if (currentView === 'timer') {
      return renderTimer();
    } else if (currentView === 'emotion') {
      return renderEmotion();
    }
    return null;
  };

  return (
    <>
      {renderCurrentView()}
      <ConfigurationModal
        isOpen={showConfigModal}
        onClose={() => setShowConfigModal(false)}
        onConfigured={(newConfig) => {
          // If user changes the config significantly, ask them to restart
          if (newConfig.apiBaseUrl !== config.apiBaseUrl || newConfig.apiKey !== config.apiKey) {
            if (confirm('API configuration changed. Do you want to restart the app to apply changes?')) {
              onReconfigure();
            } else {
              setShowConfigModal(false);
            }
          } else {
            // Just update the userId
            userIdRef.current = newConfig.userId;
            setShowConfigModal(false);
          }
        }}
        currentConfig={config}
      />
    </>
  );
};