import React, { useEffect, useRef, useState } from 'react';
import { Heart, Moon, Mountain, Play, Sparkles, Target, Zap, Settings, Star, Brain, Award, CreditCard, AlertCircle } from 'lucide-react';
import { ApiError, IngestedPulse, PulseAPI, StartPulse, StopPulse } from '../api';
import { ApiConfig, updateConfig } from '../config';
import { ConfigurationModal } from './ConfigurationModal';
import { PulseShrineLogoSvg } from './PulseShrineLogoSvg';

interface PulseAppProps {
  config: ApiConfig;
  onReconfigure: () => void;
}

export const PulseApp: React.FC<PulseAppProps> = ({ config, onReconfigure }) => {
  const [currentView, setCurrentView] = useState('shrine');
  const [activePulse, setActivePulse] = useState<StartPulse | null>(null);
  const [timeLeft, setTimeLeft] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [clientTimerActive, setClientTimerActive] = useState(false); // Track if we're in pure client timer mode
  const [timerEndTime, setTimerEndTime] = useState<number | null>(null); // Absolute end time for client timer
  const [timerInitialized, setTimerInitialized] = useState(false); // Track if timer was ever started
  const [completedPulses, setCompletedPulses] = useState<IngestedPulse[]>([]);
  const [stoppedPulses, setStoppedPulses] = useState<StopPulse[]>([]);
  const [intention, setIntention] = useState('');
  const [selectedEnergy, setSelectedEnergy] = useState('creation');
  const [duration, setDuration] = useState(25);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [planNotification, setPlanNotification] = useState<{
    message: string;
    type: 'upgrade' | 'budget' | 'achievement';
    pulse?: IngestedPulse | StopPulse;
  } | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const userIdRef = useRef(config.userId);
  const loadPulsesRef = useRef<(() => Promise<void>) | null>(null);
  const stableTimeLeftRef = useRef(0); // Stable reference to prevent flicker

  // Helper to detect connection/API issues
  const isConnectionError = (errorMessage: string | null): boolean => {
    if (!errorMessage) return false;
    const msg = errorMessage.toLowerCase();
    return msg.includes('network') || 
           msg.includes('connection') || 
           msg.includes('fetch') || 
           msg.includes('failed to fetch') || 
           msg.includes('api') ||
           msg.includes('timeout') ||
           msg.includes('refused') ||
           msg.includes('unavailable');
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
          PulseAPI.getIngestedPulses(userIdRef.current, MAX_STONES),
          PulseAPI.getStopPulses(userIdRef.current),
          PulseAPI.getStartPulse(userIdRef.current)
        ]);
        
        setActivePulse(started);
        setCompletedPulses(ingested.sort((a, b) => b.inverted_timestamp - a.inverted_timestamp));
        setStoppedPulses(stopped);
        
        // Check for plan limitation notifications
        const recentPulses = [...ingested, ...stopped].filter(p => {
          const pulseTime = p.timestamp * 1000;
          const now = Date.now();
          return (now - pulseTime) < 300000; // Last 5 minutes
        });
        
        recentPulses.forEach(pulse => {
          if (pulse.ai_selection_info?.could_be_enhanced && !pulse.ai_enhanced) {
            setPlanNotification({
              message: `This ${pulse.ai_selection_info.worthiness_score >= 0.8 ? 'exceptional' : 'high-quality'} pulse could have been AI-enhanced!`,
              type: 'upgrade',
              pulse
            });
            // Auto-dismiss after 10 seconds for upgrade notifications
            setTimeout(() => setPlanNotification(null), 10000);
          }
          
          if (pulse.triggered_rewards && pulse.triggered_rewards.length > 0) {
            setPlanNotification({
              message: pulse.triggered_rewards[0].message,
              type: 'achievement',
              pulse
            });
            // Auto-dismiss after 7 seconds for achievement notifications
            setTimeout(() => setPlanNotification(null), 7000);
          }
        });
        
        // If there's an active pulse, handle initial setup only
        if (started) {
          setDuration(Math.ceil(started.duration_seconds / 60)); // Convert back to minutes for UI
          
          
          // Only initialize timer if not already running AND not initialized
          if (!clientTimerActive && !timerInitialized) {
            const serverRemaining = started.remaining_seconds !== undefined 
              ? started.remaining_seconds 
              : started.duration_seconds;
            
            console.log('Initializing timer from server:', { serverRemaining });
            setTimeLeft(serverRemaining);
            stableTimeLeftRef.current = serverRemaining;
            
            // Auto-resume if there's time left
            if (serverRemaining > 5) {
              console.log('Auto-resuming timer after page reload');
              setIsRunning(true);
              setClientTimerActive(true);
              setTimerInitialized(true);
              
              const endTime = Date.now() + (serverRemaining * 1000);
              setTimerEndTime(endTime);
            } else {
              // Time expired, clean up any running timer and go to emotion screen
              console.log('Server time expired, cleaning up timer and going to emotion screen');
              setIsRunning(false);
              setClientTimerActive(false);
              setTimerEndTime(null);
              setTimerInitialized(false);
              setCurrentView('emotion');
            }
          } else {
            console.log('POLLING UPDATE - Timer already active, no initialization needed');
          }
        } else {
          // No active pulse on server, clear local state if needed
          if (activePulse) {
            console.log('Server reports no active pulse, clearing local state');
            setActivePulse(null);
            setIsRunning(false);
            setClientTimerActive(false);
            setTimerInitialized(false);
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

  // Timer logic using absolute end time (independent of activePulse updates)
  useEffect(() => {
    // Always clear any existing interval first
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (isRunning && timerEndTime) {
      console.log('Starting timer with end time:', new Date(timerEndTime).toISOString());
      
      intervalRef.current = setInterval(() => {
        const now = Date.now();
        const remaining = Math.max(0, Math.floor((timerEndTime - now) / 1000));
        
        
        setTimeLeft(remaining);
        stableTimeLeftRef.current = remaining; // Keep ref in sync
        
        if (remaining <= 0) {
          setIsRunning(false);
          setClientTimerActive(false);
          setTimerEndTime(null);
          setTimerInitialized(false); // Allow future timers to auto-resume
          setCurrentView('emotion');
        }
      }, 1000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isRunning, timerEndTime]);

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
      stableTimeLeftRef.current = duration * 60; // Initialize stable ref
      setCurrentView('timer');
      setIsRunning(true); // Auto-start the timer for new pulse
      setClientTimerActive(true); // Take control from server polling
      setTimerInitialized(true); // Mark timer as initialized
      
      // Set absolute end time for client timer
      const endTime = Date.now() + (duration * 60 * 1000);
      setTimerEndTime(endTime);
      console.log('Timer will end at:', new Date(endTime).toISOString());
      
      // Don't refresh pulses immediately to avoid overwriting the timer
      // The polling will pick up the change in 30 seconds
    } catch (err) {
      const errorMessage = err instanceof ApiError 
        ? err.message 
        : 'Failed to start pulse. Please try again.';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
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
      setClientTimerActive(false); // Release control back to server
      setTimerEndTime(null); // Clear the end time
      setTimerInitialized(false); // Allow future timers to auto-resume
      
      // Show completion notification
      setPlanNotification({
        message: 'Mindful stone created! Your pulse is now processing...',
        type: 'achievement'
      });
      
      // Auto-dismiss notification after 5 seconds
      setTimeout(() => setPlanNotification(null), 5000);
      
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
        <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center text-white text-lg">
          🧘
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

  const PlanNotification = ({ notification, onClose }: {
    notification: { message: string; type: 'upgrade' | 'budget' | 'achievement'; pulse?: IngestedPulse | StopPulse };
    onClose: () => void;
  }) => {
    const getNotificationStyle = () => {
      switch (notification.type) {
        case 'achievement':
          return 'from-yellow-50 to-orange-50 border-yellow-200 text-yellow-800';
        case 'upgrade':
          return 'from-purple-50 to-blue-50 border-purple-200 text-purple-800';
        case 'budget':
          return 'from-blue-50 to-indigo-50 border-blue-200 text-blue-800';
        default:
          return 'from-gray-50 to-slate-50 border-gray-200 text-gray-800';
      }
    };

    const getIcon = () => {
      switch (notification.type) {
        case 'achievement':
          return <Award className="w-5 h-5 text-yellow-600" />;
        case 'upgrade':
          return <Star className="w-5 h-5 text-purple-600" />;
        case 'budget':
          return <CreditCard className="w-5 h-5 text-blue-600" />;
        default:
          return <AlertCircle className="w-5 h-5 text-gray-600" />;
      }
    };

    return (
      <div className={`bg-gradient-to-r ${getNotificationStyle()} rounded-lg p-4 mb-4 border backdrop-blur-sm transition-all duration-300`}>
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3">
            {getIcon()}
            <div className="flex-1">
              <p className="font-medium">{notification.message}</p>
              {notification.type === 'upgrade' && notification.pulse && (
                <div className="mt-2 text-sm opacity-80">
                  <p>Worthiness: {Math.round((notification.pulse.selection_info?.worthiness_score ?? 0) * 100)}%</p>
                  <p className="text-xs mt-1">Upgrade to enhance high-quality pulses with AI insights!</p>
                </div>
              )}
              {notification.type === 'achievement' && notification.pulse?.triggered_rewards && (
                <div className="mt-2 text-sm opacity-80">
                  <p>+{notification.pulse.triggered_rewards[0]?.ai_credits} AI Credits earned! 🎉</p>
                </div>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-current opacity-60 hover:opacity-100 transition-opacity ml-4"
          >
            ×
          </button>
        </div>
      </div>
    );
  };

  // Configuration constant for max stones to display
  const MAX_STONES = 24;

  const renderShrine = () => {
    // Combine all pulses for display
    const ingestedIdsSet = new Set(completedPulses.map(p => p.pulse_id));
    const curatedStoppedPulses = stoppedPulses.filter(p => !ingestedIdsSet.has(p.pulse_id));
    
    let displayPulses = [...completedPulses];
    
    // Add stopped pulses that haven't been ingested yet (processing state)
    curatedStoppedPulses.forEach(pulse => {
      if (displayPulses.length < MAX_STONES) {
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
              <div className="flex items-center space-x-3">
                <div className="relative group">
                  <div className="absolute inset-0 bg-gradient-to-r from-purple-400 to-blue-400 rounded-full opacity-10 blur-sm animate-zen-breathe"></div>
                  <PulseShrineLogoSvg size={72} className="relative transition-transform duration-300 hover:scale-110 cursor-pointer" />
                  <div className="absolute top-full mt-3 left-1/2 transform -translate-x-1/2 bg-slate-800/90 backdrop-blur-sm text-white px-4 py-3 rounded-lg text-sm opacity-0 group-hover:opacity-100 transition-all duration-300 z-50 w-80 shadow-lg pointer-events-none">
                    <div className="font-medium text-slate-100 flex items-center justify-center space-x-2">
                      <span>🧘</span>
                      <span>Follow the rhythm, find your calm</span>
                      <span>🧘</span>
                    </div>
                    <div className="text-slate-300 mt-1 flex items-center justify-center space-x-2">
                      <span>💙</span>
                      <span>Breathe with the pulse to unlock the stress-reducing power of cardiac coherence</span>
                      <span>💙</span>
                    </div>
                    <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-b-4 border-transparent border-b-slate-800/90"></div>
                  </div>
                </div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                  Pulse Shrine
                </h1>
              </div>
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
            <p className="text-gray-600">Mindful space of focused productivity</p>
            {/* Connection Status - Only show when there's an issue */}
            {isConnectionError(error) ? (
              <div className="flex items-center justify-center space-x-2 mt-3">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" style={{animationDelay: '0s'}}></div>
                  <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" style={{animationDelay: '0.3s'}}></div>
                  <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" style={{animationDelay: '0.6s'}}></div>
                </div>
                <span className="text-xs text-red-600 font-medium bg-red-50 px-3 py-1 rounded-full border border-red-200">
                  ⚠️ Network disrupted • Restoring connection...
                </span>
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" style={{animationDelay: '0.9s'}}></div>
                  <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" style={{animationDelay: '1.2s'}}></div>
                  <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" style={{animationDelay: '1.5s'}}></div>
                </div>
              </div>
            ) : null}
            
          </header>

          {error && <ErrorMessage message={error} onClose={() => setError(null)} />}
          {planNotification && (
            <PlanNotification 
              notification={planNotification} 
              onClose={() => setPlanNotification(null)} 
            />
          )}

          <GuardianMessage>
            Welcome to your zen garden. Here, your completed pulses transform into mindful stones that enhance the tranquility of this space. Each intention you fulfill adds to the focused energy of your practice.
          </GuardianMessage>

          <div className="relative bg-gradient-to-br from-slate-100 via-green-100 to-blue-50 rounded-xl p-8 mb-8 border border-slate-200">
            {/* Zen Garden Background */}
            <div className="absolute inset-0 opacity-20">
              <svg className="w-full h-full" viewBox="0 0 800 400" fill="none">
                {/* Water pond - twice bigger */}
                <ellipse cx="600" cy="280" rx="300" ry="160" fill="#4A90E2" opacity="0.3"/>
                <ellipse cx="600" cy="280" rx="260" ry="140" fill="#6BA3F0" opacity="0.2"/>
                
                {/* Ripples */}
                <ellipse cx="540" cy="240" rx="20" ry="12" fill="none" stroke="#4A90E2" strokeWidth="1" opacity="0.4"/>
                <ellipse cx="660" cy="320" rx="30" ry="16" fill="none" stroke="#4A90E2" strokeWidth="1" opacity="0.3"/>
                <ellipse cx="600" cy="280" rx="40" ry="24" fill="none" stroke="#4A90E2" strokeWidth="1" opacity="0.2"/>
                
                {/* Stepping stones */}
                <circle cx="150" cy="320" r="25" fill="#8B7355" opacity="0.3"/>
                <circle cx="220" cy="300" r="30" fill="#9B8365" opacity="0.3"/>
                <circle cx="300" cy="280" r="28" fill="#8B7355" opacity="0.3"/>
                
                {/* Zen rocks */}
                <ellipse cx="100" cy="200" rx="40" ry="25" fill="#A8A8A8" opacity="0.4"/>
                <ellipse cx="750" cy="150" rx="35" ry="20" fill="#B8B8B8" opacity="0.3"/>
                
                {/* Bamboo forests - small groups scattered around */}
                {/* Left side forest cluster 1 */}
                <rect x="50" y="50" width="8" height="150" fill="#4A7C59" opacity="0.3"/>
                <rect x="65" y="40" width="6" height="140" fill="#5A8C69" opacity="0.3"/>
                <rect x="78" y="60" width="7" height="130" fill="#4A7C59" opacity="0.3"/>
                <rect x="90" y="45" width="5" height="135" fill="#4A7C59" opacity="0.25"/>
                <rect x="100" y="55" width="7" height="125" fill="#5A8C69" opacity="0.3"/>
                <rect x="112" y="35" width="6" height="145" fill="#4A7C59" opacity="0.25"/>
                
                {/* Left side forest cluster 2 */}
                <rect x="20" y="120" width="6" height="110" fill="#4A7C59" opacity="0.25"/>
                <rect x="30" y="105" width="8" height="125" fill="#5A8C69" opacity="0.3"/>
                <rect x="45" y="115" width="5" height="115" fill="#4A7C59" opacity="0.25"/>
                
                {/* Center-left cluster */}
                <rect x="180" y="70" width="7" height="120" fill="#4A7C59" opacity="0.25"/>
                <rect x="195" y="85" width="6" height="105" fill="#5A8C69" opacity="0.25"/>
                <rect x="208" y="75" width="5" height="115" fill="#4A7C59" opacity="0.2"/>
                
                {/* Center-right cluster */}
                <rect x="750" y="60" width="6" height="130" fill="#4A7C59" opacity="0.25"/>
                <rect x="765" y="45" width="8" height="145" fill="#5A8C69" opacity="0.3"/>
                <rect x="778" y="55" width="5" height="135" fill="#4A7C59" opacity="0.25"/>
                
                {/* Right side forest cluster 1 */}
                <rect x="680" y="30" width="8" height="160" fill="#4A7C59" opacity="0.3"/>
                <rect x="695" y="45" width="6" height="140" fill="#5A8C69" opacity="0.3"/>
                <rect x="708" y="25" width="7" height="155" fill="#4A7C59" opacity="0.25"/>
                <rect x="720" y="40" width="5" height="145" fill="#5A8C69" opacity="0.25"/>
                <rect x="732" y="35" width="6" height="150" fill="#4A7C59" opacity="0.3"/>
                
                {/* Right side forest cluster 2 */}
                <rect x="750" y="120" width="7" height="100" fill="#4A7C59" opacity="0.25"/>
                <rect x="765" y="110" width="5" height="110" fill="#5A8C69" opacity="0.25"/>
                <rect x="775" y="125" width="6" height="95" fill="#4A7C59" opacity="0.2"/>
                
                {/* Back center clusters */}
                <rect x="350" y="40" width="5" height="80" fill="#4A7C59" opacity="0.15"/>
                <rect x="360" y="35" width="6" height="85" fill="#5A8C69" opacity="0.15"/>
                <rect x="370" y="45" width="4" height="75" fill="#4A7C59" opacity="0.15"/>
                
                <rect x="450" y="50" width="6" height="90" fill="#4A7C59" opacity="0.15"/>
                <rect x="462" y="45" width="5" height="95" fill="#5A8C69" opacity="0.15"/>
                <rect x="472" y="55" width="7" height="85" fill="#4A7C59" opacity="0.15"/>
                
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

            <h2 className="relative text-2xl font-light text-slate-700 mb-8 text-center">
              Zen Garden
            </h2>
            
            {displayPulses.length === 0 && !activePulse ? (
              <div className="relative text-center py-16">
                <div className="text-5xl mb-4 animate-pulse">🌱</div>
                <p className="text-slate-500 font-light">Your tranquil garden awaits its first mindful stone...</p>
                <div className="mt-4 text-xs text-slate-400">Each completed pulse becomes a focus stone in this peaceful space</div>
              </div>
            ) : (
              <div className="relative z-20">
                <div className="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3 mb-6 relative z-30">
                  {/* Show active pulse first if exists */}
                  {activePulse && (
                    <div className="group flex items-center justify-center">
                      <div className="relative">
                        <div className="bg-gradient-to-br from-yellow-100/80 to-orange-50/80 backdrop-blur-sm p-3 rounded-full border border-yellow-200/50 hover:shadow-lg transition-all duration-500 cursor-pointer animate-pulse group-hover:scale-110 group-hover:rotate-3 origin-center">
                          <div className="text-xl text-center">⏳</div>
                          <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-gradient-to-br from-yellow-200 to-orange-300 flex items-center justify-center">
                            <Target className="w-2 h-2 text-orange-600" />
                          </div>
                        </div>
                        <div className="absolute bottom-full mb-3 left-1/2 transform -translate-x-1/2 bg-slate-800/90 backdrop-blur-sm text-white px-4 py-3 rounded-lg text-sm opacity-0 group-hover:opacity-100 transition-all duration-300 z-50 w-96 shadow-lg pointer-events-none">
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
                    const isAiEnhanced = pulse.ai_enhanced && !isProcessing;
                    return (
                      <div key={pulse.pulse_id} className="group flex items-center justify-center">
                        <div className="relative">
                          <div 
                            className={`backdrop-blur-sm p-3 rounded-full border transition-all duration-500 cursor-pointer group-hover:scale-110 group-hover:rotate-3 origin-center ${
                              isProcessing 
                                ? 'bg-gradient-to-br from-yellow-100/80 to-orange-100/80 border-yellow-300/50 animate-pulse hover:shadow-lg' 
                                : isAiEnhanced
                                ? 'bg-gradient-to-br from-purple-100/90 to-blue-100/90 border-purple-300/70 shadow-lg shadow-purple-200/30 hover:shadow-xl hover:shadow-purple-300/40 animate-pulse-gentle'
                                : 'bg-gradient-to-br from-white/80 to-slate-50/80 border-slate-200/50 hover:shadow-lg'
                            }`}
                            style={{
                              animationDelay: `${index * 0.1}s`,
                              animation: isProcessing ? 'pulse 2s infinite' : isAiEnhanced ? 'pulse-gentle 4s infinite' : 'none'
                            }}
                          >
                            <div className={`text-xl text-center ${isProcessing ? 'animate-spin' : ''}`}>{symbol}</div>
                            {isAiEnhanced && (
                              <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center animate-pulse">
                                <Brain className="w-2 h-2 text-white" />
                              </div>
                            )}
                          </div>
                          <div className={`absolute bottom-full mb-3 left-1/2 transform -translate-x-1/2 backdrop-blur-sm text-white px-4 py-3 rounded-lg text-sm opacity-0 group-hover:opacity-100 transition-all duration-300 z-50 w-96 shadow-lg pointer-events-none ${
                            isProcessing ? 'bg-yellow-800/90' : isAiEnhanced ? 'bg-purple-800/90' : 'bg-slate-800/90'
                          }`}>
                            <div className="font-medium text-slate-100">
                              {pulse.gen_badge && (
                                <div className="mb-1">
                                  {pulse.gen_badge.length > 45 ? `${pulse.gen_badge.slice(0, 45)}...` : pulse.gen_badge}
                                </div>
                              )}
                              {pulse.gen_title || pulse.intent}
                            </div>
                            {pulse.reflection && (
                              <div className="text-slate-300 mt-1 italic">"{pulse.reflection}"</div>
                            )}
                            {isProcessing && (
                              <div className="text-yellow-300 mt-1 text-xs animate-pulse">Processing your focus stone...</div>
                            )}
                            {isAiEnhanced && pulse.ai_insights?.productivity_score && (
                              <div className="text-purple-300 mt-1 text-xs">
                                🌟 Focus: {pulse.ai_insights.productivity_score}/10
                              </div>
                            )}
                            {pulse.ai_insights && (
                              <div className="text-slate-400 mt-2 text-xs border-t border-slate-600 pt-2">
                                <div className="space-y-1">
                                  {pulse.ai_insights.key_insight && (
                                    <div><span className="text-slate-300">💡 Insight:</span> {pulse.ai_insights.key_insight}</div>
                                  )}
                                  {pulse.ai_insights.next_suggestion && (
                                    <div><span className="text-slate-300">🎯 Next:</span> {pulse.ai_insights.next_suggestion}</div>
                                  )}
                                  {pulse.ai_insights.mood_assessment && (
                                    <div><span className="text-slate-300">🧘 Mood:</span> {pulse.ai_insights.mood_assessment}</div>
                                  )}
                                </div>
                              </div>
                            )}
                            <div className={`absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent ${
                              isProcessing ? 'border-t-yellow-800/90' : isAiEnhanced ? 'border-t-purple-800/90' : 'border-t-slate-800/90'
                            }`}></div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                
              </div>
            )}
          </div>

          <div className="bg-white/70 backdrop-blur-sm rounded-xl p-6 border border-white/50">
            {activePulse ? (
              <div className="space-y-4">
                <div className="p-4 rounded-lg border bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-200">
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
                    <span className="font-semibold text-gray-800">
                      Active Pulse in Progress
                    </span>
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
                  <p className="text-xs text-gray-600 mt-1">
                    Time remaining: {formatTime(timeLeft)}
                  </p>
                </div>
                <button
                  onClick={() => {
                    if (activePulse) {
                      // If timer is already running, just navigate to timer view
                      if (isRunning && timerEndTime) {
                        console.log('Timer already running, just navigating to timer view');
                        setCurrentView('timer');
                      } else {
                        // Timer not running, need to start/resume it
                        const serverRemaining = activePulse.remaining_seconds !== undefined 
                          ? activePulse.remaining_seconds 
                          : activePulse.duration_seconds;
                        
                        console.log('Starting timer from Continue button:', { serverRemaining });
                        setTimeLeft(serverRemaining);
                        stableTimeLeftRef.current = serverRemaining;
                        setDuration(Math.ceil(activePulse.duration_seconds / 60));
                        
                        if (serverRemaining > 0) {
                          setCurrentView('timer');
                          setIsRunning(true);
                          setClientTimerActive(true);
                          setTimerEndTime(Date.now() + (serverRemaining * 1000));
                        } else {
                          setCurrentView('emotion');
                        }
                      }
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
                <span>{isLoading ? 'Loading...' : 'Start Focusing'}</span>
              </button>
            )}
          </div>

          {(displayPulses.length > 0 || activePulse) && (
            <div className="mt-6">
              {/* Enhanced Statistics */}
              <div className="bg-white/50 backdrop-blur-sm rounded-lg p-4 mb-4 border border-white/60">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center max-w-md mx-auto">
                  {/* Recent Focus Stones */}
                  <div className="space-y-1">
                    <div className="text-2xl font-bold text-gray-700 h-8 flex items-center justify-center">
                      {(() => {
                        const now = new Date();
                        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                        const todayEnd = new Date(todayStart.getTime() + 24 * 60 * 60 * 1000);
                        
                        const recentPulses = completedPulses.filter(pulse => {
                          const pulseDate = typeof pulse.timestamp === 'number' 
                            ? new Date(pulse.timestamp * 1000) 
                            : new Date((pulse as any).archived_at || pulse.timestamp);
                          return pulseDate >= todayStart && pulseDate < todayEnd;
                        });
                        
                        return recentPulses.length + (activePulse ? 1 : 0);
                      })()}
                    </div>
                    <div className="text-xs text-gray-600">Today</div>
                  </div>
                  
                  {/* AI Enhanced */}
                  <div className="space-y-1">
                    <div className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent h-8 flex items-center justify-center space-x-1 animate-pulse">
                      <Brain className="w-5 h-5 text-purple-600 animate-pulse" />
                      <span>{displayPulses.filter(p => p.ai_enhanced).length}</span>
                    </div>
                    <div className="text-xs text-gray-600">🧠 AI Insights</div>
                  </div>
                  
                  {/* Average Productivity - Always show this slot */}
                  <div className="space-y-1">
                    {displayPulses.some(p => p.ai_insights?.productivity_score) ? (
                      <>
                        <div className="text-2xl font-bold text-yellow-600 h-8 flex items-center justify-center space-x-1">
                          <Star className="w-5 h-5" />
                          <span>
                            {Math.round(
                              displayPulses
                                .filter(p => p.ai_insights?.productivity_score)
                                .reduce((sum, p) => sum + (p.ai_insights?.productivity_score || 0), 0) /
                              displayPulses.filter(p => p.ai_insights?.productivity_score).length
                            )}
                          </span>
                        </div>
                        <div className="text-xs text-gray-600">Focus</div>
                      </>
                    ) : (
                      <>
                        <div className="text-2xl font-bold text-gray-300 h-8 flex items-center justify-center">
                          <Star className="w-6 h-6" />
                        </div>
                        <div className="text-xs text-gray-400">Focus</div>
                      </>
                    )}
                  </div>
                  
                  {/* Dynamic Processing/Ready slot */}
                  <div className="space-y-1 relative">
                    {curatedStoppedPulses.length > 0 ? (
                      <div className="animate-fadeIn">
                        <div className="text-2xl font-bold text-yellow-500 h-8 flex items-center justify-center space-x-1 animate-pulse">
                          <div>⚡</div>
                          <span>{curatedStoppedPulses.length}</span>
                        </div>
                        <div className="text-xs text-gray-600 mt-1">Reflecting</div>
                      </div>
                    ) : (
                      <div className="animate-fadeIn">
                        <div className="text-2xl font-bold text-gray-300 h-8 flex items-center justify-center">
                          <Zap className="w-6 h-6 opacity-60" />
                        </div>
                        <div className="text-xs text-gray-400 mt-1">Complete</div>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* AI Enhancement Summary */}
                {displayPulses.some(p => p.ai_enhanced) && (
                  <div className="mt-4 pt-4 border-t border-gray-200/50">
                    <div className="text-center text-sm text-gray-600">
                      <span className="inline-flex items-center space-x-1 bg-gradient-to-r from-purple-100 to-blue-100 px-3 py-1 rounded-full">
                        <Brain className="w-4 h-4 text-purple-600" />
                        <span>
                          {Math.round((displayPulses.filter(p => p.ai_enhanced).length / displayPulses.length) * 100)}% 
                          of your focus stones are AI-enhanced
                        </span>
                      </span>
                    </div>
                  </div>
                )}
              </div>
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
          Set your intention clearly. Choose the energy that aligns with your purpose, and let us begin this focused pulse together.
        </GuardianMessage>

        <div className="bg-white/70 backdrop-blur-sm rounded-xl p-8 border border-white/50">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">Set Your Intention</h2>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Your Intention
              </label>
              <textarea
                value={intention}
                onChange={(e) => setIntention(e.target.value.slice(0, 200))}
                placeholder="✨ Write my first blog post or learn React hooks"
                maxLength={200}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                rows={3}
              />
              <div className="text-xs text-gray-500 mt-1 text-right">
                {intention.length}/200 characters
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Choose Your Energy
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(energyIcons).map(([key, { icon: Icon, color }]) => {
                  const energyDescriptions = {
                    creation: "Perfect for writing, designing, and bringing new ideas to life",
                    focus: "Ideal for deep work, studying, and tasks requiring concentration", 
                    brainstorm: "Great for ideation, problem-solving, and creative thinking",
                    study: "Best for learning, reading, and absorbing new information",
                    planning: "Optimal for organizing, strategizing, and project planning",
                    reflection: "Perfect for introspection, meditation, and processing experiences"
                  };
                  
                  return (
                    <div key={key} className="relative group">
                      <button
                        onClick={() => setSelectedEnergy(key)}
                        className={`w-full p-4 rounded-lg border-2 transition-all duration-200 ${
                          selectedEnergy === key
                            ? 'border-purple-500 bg-purple-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <Icon className={`w-6 h-6 mx-auto mb-2 ${color}`} />
                        <span className="text-sm font-medium capitalize">{key}</span>
                      </button>
                      
                      {/* Tooltip */}
                      <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-slate-800/90 backdrop-blur-sm text-white px-3 py-2 rounded-lg text-xs opacity-0 group-hover:opacity-100 transition-all duration-300 z-50 w-48 shadow-lg pointer-events-none">
                        <div className="text-center">{energyDescriptions[key as keyof typeof energyDescriptions]}</div>
                        <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-3 border-r-3 border-t-3 border-transparent border-t-slate-800/90"></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Duration (minutes)
              </label>
              <div className="grid grid-cols-5 sm:grid-cols-5 md:grid-cols-10 gap-2">
                {[5, 10, 15, 25, 30, 45, 60, 90, 120, 180].map((minutes, index) => {
                  const intensity = (index + 1) / 10; // 0.1 to 1.0
                  const isSelected = duration === minutes;
                  
                  return (
                    <button
                      key={minutes}
                      type="button"
                      onClick={() => setDuration(minutes)}
                      className={`
                        relative px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 border-2
                        ${isSelected 
                          ? 'border-purple-500 text-purple-700 bg-purple-50 shadow-md' 
                          : 'border-gray-200 hover:border-gray-300 text-gray-700'
                        }
                      `}
                      style={{
                        backgroundColor: isSelected 
                          ? undefined 
                          : `rgb(${255 - intensity * 80}, ${255 - intensity * 80}, ${255 - intensity * 80})`,
                        color: isSelected 
                          ? undefined 
                          : intensity > 0.6 ? 'white' : 'rgb(75, 85, 99)'
                      }}
                    >
                      {minutes}
                    </button>
                  );
                })}
              </div>
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
    const totalDuration = activePulse.duration_seconds;
    const currentTimeLeft = timeLeft;
    const progress = currentTimeLeft > 0 ? ((totalDuration - currentTimeLeft) / totalDuration) * 100 : 100;

    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-blue-900 p-6 text-white relative overflow-hidden">
        {/* Breathing Garden Background */}
        <div className="absolute inset-0 pointer-events-none opacity-10">
          {/* Zen Garden Elements with Breathing Animation */}
          <svg className="w-full h-full" viewBox="0 0 1200 800" fill="none">
            {/* Water pond with breathing ripples */}
            <ellipse cx="900" cy="500" rx="150" ry="80" fill="#4A90E2" opacity="0.3" className="animate-pulse-slow"/>
            <ellipse cx="900" cy="500" rx="120" ry="60" fill="#6BA3F0" opacity="0.4" className="animate-pulse-slow" style={{animationDelay: '1s'}}/>
            
            {/* Breathing ripples */}
            <ellipse cx="880" cy="480" rx="10" ry="5" fill="none" stroke="#4A90E2" strokeWidth="2" opacity="0.5" className="animate-pulse-gentle"/>
            <ellipse cx="920" cy="520" rx="15" ry="8" fill="none" stroke="#4A90E2" strokeWidth="2" opacity="0.4" className="animate-pulse-gentle" style={{animationDelay: '2s'}}/>
            
            {/* Stepping stones with gentle pulse */}
            <circle cx="200" cy="600" r="30" fill="#8B7355" opacity="0.4" className="animate-pulse-slow"/>
            <circle cx="320" cy="560" r="35" fill="#9B8365" opacity="0.4" className="animate-pulse-slow" style={{animationDelay: '1.5s'}}/>
            <circle cx="450" cy="520" r="32" fill="#8B7355" opacity="0.4" className="animate-pulse-slow" style={{animationDelay: '3s'}}/>
            
            {/* Zen rocks breathing */}
            <ellipse cx="150" cy="300" rx="50" ry="30" fill="#A8A8A8" opacity="0.5" className="animate-pulse-gentle"/>
            <ellipse cx="1000" cy="200" rx="40" ry="25" fill="#B8B8B8" opacity="0.4" className="animate-pulse-gentle" style={{animationDelay: '2.5s'}}/>
            
            {/* Bamboo silhouettes with gentle sway */}
            <g className="animate-pulse-slow">
              <rect x="80" y="100" width="12" height="200" fill="#4A7C59" opacity="0.4"/>
              <rect x="100" y="80" width="8" height="180" fill="#5A8C69" opacity="0.4"/>
              <rect x="118" y="120" width="10" height="160" fill="#4A7C59" opacity="0.4"/>
            </g>
            
            {/* Sacred path with breathing glow */}
            <path d="M0,650 Q200,630 400,650 T800,650" stroke="#4A90E2" strokeWidth="3" fill="none" opacity="0.3" className="animate-pulse-gentle"/>
            <path d="M800,670 Q1000,650 1200,670" stroke="#4A90E2" strokeWidth="3" fill="none" opacity="0.3" className="animate-pulse-gentle" style={{animationDelay: '1s'}}/>
            
            {/* Meditation circles with breathing rhythm */}
            <circle cx="600" cy="150" r="20" fill="none" stroke="#ffffff" strokeWidth="1" opacity="0.2" className="animate-pulse-gentle"/>
            <circle cx="600" cy="150" r="35" fill="none" stroke="#ffffff" strokeWidth="1" opacity="0.1" className="animate-pulse-gentle" style={{animationDelay: '1s'}}/>
            <circle cx="600" cy="150" r="50" fill="none" stroke="#ffffff" strokeWidth="1" opacity="0.05" className="animate-pulse-gentle" style={{animationDelay: '2s'}}/>
          </svg>
        </div>
        
        {/* Floating zen particles */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-20 left-20 w-2 h-2 bg-blue-300 rounded-full opacity-20 animate-pulse-slow"></div>
          <div className="absolute top-40 right-32 w-1 h-1 bg-purple-300 rounded-full opacity-30 animate-pulse-slow" style={{animationDelay: '2s'}}></div>
          <div className="absolute bottom-60 left-1/4 w-1.5 h-1.5 bg-green-300 rounded-full opacity-25 animate-pulse-slow" style={{animationDelay: '4s'}}></div>
          <div className="absolute top-1/3 right-1/4 w-1 h-1 bg-white rounded-full opacity-20 animate-pulse-slow" style={{animationDelay: '6s'}}></div>
          <div className="absolute bottom-40 right-20 w-2 h-2 bg-indigo-300 rounded-full opacity-15 animate-pulse-slow" style={{animationDelay: '3s'}}></div>
          <div className="absolute top-60 left-1/2 w-1 h-1 bg-cyan-300 rounded-full opacity-25 animate-pulse-slow" style={{animationDelay: '5s'}}></div>
        </div>

        <div className="max-w-2xl mx-auto text-center relative z-10">
          <div className="bg-gradient-to-r from-purple-100 to-blue-100 p-4 rounded-lg border border-purple-200 mb-6">
            <div className="flex items-start space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center text-white text-lg">
                🧘
              </div>
              <div className="flex-1">
                <p className="text-gray-700 italic">Focus your energy. Let your intention guide you through this mindful time. Your progress is being gently observed.</p>
              </div>
            </div>
          </div>

          {error && <ErrorMessage message={error} onClose={() => setError(null)} />}

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-8 border border-white/20 mb-8">
            <div className="mb-6">
              {selectedEnergy === 'creation' ? (
                <div className="flex justify-center mb-4">
                  <PulseShrineLogoSvg size={96} variant="white" />
                </div>
              ) : (
                <EnergyIcon className={`w-12 h-12 mx-auto mb-4 ${energyIcons[selectedEnergy as keyof typeof energyIcons]?.color || 'text-purple-500'}`} />
              )}
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
                  className="transition-all duration-1000 animate-pulse-gentle"
                />
                <defs>
                  <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#8B5CF6" />
                    <stop offset="100%" stopColor="#3B82F6" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-4xl font-bold animate-pulse-slow">{formatTime(timeLeft)}</div>
              </div>
            </div>


            <div className="flex justify-center space-x-4">
              <button
                onClick={() => setCurrentView('emotion')}
                className="group relative bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white px-8 py-3 rounded-lg font-semibold transition-all duration-300 overflow-hidden"
              >
                {/* Breathing animation background */}
                <div className="absolute inset-0 bg-gradient-to-r from-green-400 to-emerald-400 opacity-0 group-hover:opacity-20 animate-zen-breathe"></div>
                
                {/* Floating particles */}
                <div className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                  <div className="absolute top-1/2 left-1/4 w-1 h-1 bg-white rounded-full animate-float" style={{animationDelay: '0s'}}></div>
                  <div className="absolute top-1/3 right-1/3 w-1 h-1 bg-white rounded-full animate-float" style={{animationDelay: '0.5s'}}></div>
                  <div className="absolute bottom-1/3 left-1/2 w-1 h-1 bg-white rounded-full animate-float" style={{animationDelay: '1s'}}></div>
                </div>
                
                <span className="relative z-10 flex items-center space-x-2">
                  <span>Complete & breathe</span>
                  <span className="text-lg animate-pulse">✓</span>
                </span>
              </button>
            </div>
          </div>

          <button
            onClick={() => setCurrentView('shrine')}
            className="text-gray-300 hover:text-white transition-colors mt-4"
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
            Your pulse is complete. Now, reflect upon your experience and choose the emotion that best captures your journey. Share your insights and learnings - this reflection will become the essence of your new mindful stone.
          </GuardianMessage>

          {activePulse && (
            <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-4 mb-6">
              <h3 className="font-semibold text-purple-800 mb-2">Your Focus Session</h3>
              <div className="text-purple-700">
                <p className="font-medium">"{activePulse.intent}"</p>
                <div className="flex items-center space-x-4 mt-2 text-sm">
                  <div className="flex items-center space-x-1">
                    {energyIcons[selectedEnergy as keyof typeof energyIcons] && (
                      <>
                        {React.createElement(energyIcons[selectedEnergy as keyof typeof energyIcons].icon, {
                          className: `w-4 h-4 ${energyIcons[selectedEnergy as keyof typeof energyIcons].color}`
                        })}
                        <span className="capitalize">{selectedEnergy} energy</span>
                      </>
                    )}
                  </div>
                  <div>Duration: {Math.ceil(activePulse.duration_seconds / 60)} minutes</div>
                </div>
              </div>
            </div>
          )}


          <div className="bg-white/70 backdrop-blur-sm rounded-xl p-8 border border-white/50">
            <h2 className="text-2xl font-semibold text-gray-800 mb-6 text-center">
              How do you feel about your pulse?
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              {emotions.map((emotion) => {
                const emotionMeanings = {
                  fulfilled: "You achieved what you set out to do and feel a deep sense of satisfaction",
                  peaceful: "You feel calm, serene, and emotionally balanced from your practice", 
                  energized: "You feel invigorated, motivated, and ready to take on challenges",
                  focused: "Your mind feels clear, sharp, and able to concentrate deeply",
                  creative: "You feel inspired, imaginative, and ready to express new ideas",
                  grounded: "You feel stable, centered, and connected to the present moment"
                };
                
                return (
                  <div key={emotion.key} className="relative group">
                    <button
                      onClick={() => setSelectedEmotion(emotion.key)}
                      className={`w-full h-32 p-6 text-left border-2 rounded-lg transition-all duration-200 group flex items-center ${
                        selectedEmotion === emotion.key
                          ? 'border-purple-500 bg-purple-50'
                          : 'border-gray-200 hover:border-purple-300 hover:bg-purple-25'
                      }`}
                    >
                      <div className="flex items-center space-x-4 w-full">
                        <span className="text-4xl flex-shrink-0">{emotion.icon}</span>
                        <div className="flex-1 min-w-0">
                          <h3 className={`font-semibold text-lg ${
                            selectedEmotion === emotion.key 
                              ? 'text-purple-700' 
                              : 'text-gray-800 group-hover:text-purple-700'
                          }`}>
                            {emotion.label}
                          </h3>
                          <p className="text-sm text-gray-600 leading-relaxed">{emotion.desc}</p>
                        </div>
                      </div>
                    </button>
                    
                    {/* Tooltip */}
                    <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-slate-800/90 backdrop-blur-sm text-white px-4 py-2 rounded-lg text-sm opacity-0 group-hover:opacity-100 transition-all duration-300 z-50 w-72 shadow-lg pointer-events-none">
                      <div className="text-center">{emotionMeanings[emotion.key as keyof typeof emotionMeanings]}</div>
                      <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-slate-800/90"></div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Share your reflection *
              </label>
              <textarea
                value={customReflection}
                onChange={(e) => setCustomReflection(e.target.value.slice(0, 200))}
                placeholder="🌱 Share your journey... What insights emerged? What breakthrough moment happened? How did this session transform your understanding? (e.g., 'I discovered a new approach to solving complex problems' or 'I felt deeply focused and entered a flow state')"
                maxLength={200}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                rows={4}
              />
              <div className="text-xs text-gray-500 mt-1 text-right">
                {customReflection.length}/200 characters
              </div>
            </div>

            <button
              onClick={handleSubmit}
              disabled={!selectedEmotion || !customReflection.trim() || isLoading}
              className="w-full bg-gradient-to-r from-purple-500 to-blue-500 text-white py-4 px-6 rounded-lg font-semibold hover:from-purple-600 hover:to-blue-600 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            >
              <Sparkles className="w-5 h-5" />
              <span>
                {isLoading ? 'Creating...' : 'Create Focus Stone'}
              </span>
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
          // Save the config to localStorage
          updateConfig(newConfig);
          
          // Always update the userIdRef
          userIdRef.current = newConfig.userId;
          
          // If user changes the config significantly, ask them to restart
          if (newConfig.apiBaseUrl !== config.apiBaseUrl || newConfig.apiKey !== config.apiKey) {
            if (confirm('API configuration changed. Do you want to restart the app to apply changes?')) {
              onReconfigure();
            } else {
              // User declined restart, but config is still saved
              setShowConfigModal(false);
            }
          } else {
            // Minor changes (userId only) - just close modal
            setShowConfigModal(false);
          }
        }}
        currentConfig={config}
      />
    </>
  );
};
