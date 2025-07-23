import { AlertCircle, Crown, Sparkles, Users, Zap } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { PulseAPI, SubscriptionInfo } from '../api';

interface SubscriptionStatusProps {
  onShowDashboard?: () => void;
}

export const SubscriptionStatus: React.FC<SubscriptionStatusProps> = ({ onShowDashboard }) => {
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSubscription = async () => {
      try {
        const data = await PulseAPI.getSubscription();
        setSubscription(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load subscription');
      } finally {
        setLoading(false);
      }
    };

    loadSubscription();
  }, []);

  if (loading || error || !subscription) {
    return null; // Don't show anything if we can't load subscription data
  }

  const getTierIcon = () => {
    switch (subscription.subscription_tier) {
      case 'pro': return Crown;
      case 'enterprise': return Users;
      default: return Sparkles;
    }
  };

  const getTierColor = () => {
    switch (subscription.subscription_tier) {
      case 'pro': return 'text-blue-600 bg-blue-100 border-blue-200';
      case 'enterprise': return 'text-purple-600 bg-purple-100 border-purple-200';
      default: return 'text-green-600 bg-green-100 border-green-200';
    }
  };

  const TierIcon = getTierIcon();
  const tierColorClass = getTierColor();

  // Check if user is approaching limits
  const pulseUsage = subscription.usage.pulses;
  const aiUsage = subscription.usage.ai_enhancements;
  const isNearPulseLimit = !pulseUsage.unlimited && pulseUsage.percentage > 80;
  const isAtPulseLimit = !pulseUsage.unlimited && pulseUsage.percentage >= 100;
  const isNearAILimit = !aiUsage.unlimited && aiUsage.quota > 0 && aiUsage.percentage > 80;
  const isAtAILimit = !aiUsage.unlimited && aiUsage.quota === 0 || (!aiUsage.unlimited && aiUsage.percentage >= 100);

  const showWarning = isNearPulseLimit || isAtPulseLimit || isNearAILimit || isAtAILimit;

  return (
    <div 
      className={`
        border rounded-lg p-3 cursor-pointer transition-all duration-200 hover:shadow-md
        ${tierColorClass}
        ${showWarning ? 'ring-2 ring-yellow-400 ring-opacity-50' : ''}
      `}
      onClick={onShowDashboard}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <TierIcon className="w-4 h-4" />
          <span className="font-medium capitalize text-sm">
            {subscription.subscription_tier}
          </span>
          {showWarning && (
            <AlertCircle className="w-4 h-4 text-yellow-600" />
          )}
        </div>
        <div className="text-xs opacity-75">
          {subscription.billing_cycle.days_remaining}d left
        </div>
      </div>

      {/* Usage indicators */}
      <div className="mt-2 space-y-1">
        {/* Pulse usage */}
        <div className="flex items-center space-x-2">
          <Zap className="w-3 h-3 opacity-60" />
          <div className="flex-1">
            {pulseUsage.unlimited ? (
              <div className="text-xs opacity-75">Unlimited pulses</div>
            ) : (
              <div className="flex items-center space-x-2">
                <div className="flex-1 bg-white bg-opacity-50 rounded-full h-1">
                  <div 
                    className={`h-1 rounded-full transition-all duration-300 ${
                      isAtPulseLimit ? 'bg-red-500' : 
                      isNearPulseLimit ? 'bg-yellow-500' : 'bg-current'
                    }`}
                    style={{ width: `${Math.min(pulseUsage.percentage, 100)}%` }}
                  ></div>
                </div>
                <span className="text-xs opacity-75">
                  {pulseUsage.used}/{pulseUsage.quota}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* AI usage */}
        <div className="flex items-center space-x-2">
          <Sparkles className="w-3 h-3 opacity-60" />
          <div className="flex-1">
            {aiUsage.unlimited ? (
              <div className="text-xs opacity-75">Unlimited AI</div>
            ) : aiUsage.quota === 0 ? (
              <div className="text-xs opacity-75">No AI access</div>
            ) : aiUsage.quota <= 5 ? (  // Show "samples" for small quotas (adjusts with backend constants)
              <div className="flex items-center space-x-2">
                <div className="flex-1 bg-white bg-opacity-50 rounded-full h-1">
                  <div 
                    className={`h-1 rounded-full transition-all duration-300 ${
                      isAtAILimit ? 'bg-red-500' : 
                      isNearAILimit ? 'bg-yellow-500' : 'bg-current'
                    }`}
                    style={{ width: `${Math.min(aiUsage.percentage, 100)}%` }}
                  ></div>
                </div>
                <span className="text-xs opacity-75">
                  {aiUsage.used}/{aiUsage.quota} samples
                </span>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <div className="flex-1 bg-white bg-opacity-50 rounded-full h-1">
                  <div 
                    className={`h-1 rounded-full transition-all duration-300 ${
                      isAtAILimit ? 'bg-red-500' : 
                      isNearAILimit ? 'bg-yellow-500' : 'bg-current'
                    }`}
                    style={{ width: `${Math.min(aiUsage.percentage, 100)}%` }}
                  ></div>
                </div>
                <span className="text-xs opacity-75">
                  {aiUsage.used}/{aiUsage.quota}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Warning message */}
      {showWarning && (
        <div className="mt-2 text-xs text-yellow-700 font-medium">
          {isAtPulseLimit && "Pulse limit reached!"}
          {isAtAILimit && !isAtPulseLimit && (
            subscription.subscription_tier === 'free' && subscription.usage.ai_enhancements.used > 0
              ? "AI samples used up!" 
              : "AI limit reached!"
          )}
          {(isNearPulseLimit || isNearAILimit) && !isAtPulseLimit && !isAtAILimit && "Approaching limit"}
          {subscription.subscription_tier === 'free' && (
            <span className="ml-1">
              {subscription.usage.ai_enhancements.used > 0 
                ? "Love AI? Upgrade for unlimited!" 
                : "Upgrade for more."}
            </span>
          )}
        </div>
      )}

      {/* Encouraging message for unused AI samples */}
      {subscription.subscription_tier === 'free' && 
       !showWarning && 
       subscription.usage.ai_enhancements.quota > 0 && 
       subscription.usage.ai_enhancements.used === 0 && (
        <div className="mt-2 text-xs text-blue-600 font-medium">
          ✨ Try AI enhancement on your next pulse!
        </div>
      )}
    </div>
  );
};