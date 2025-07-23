import { AlertCircle, CreditCard, Crown, Sparkles, TrendingUp, Users, Zap } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { PulseAPI, SubscriptionInfo, PricingInfo } from '../api';

interface SubscriptionDashboardProps {
  onClose?: () => void;
}

export const SubscriptionDashboard: React.FC<SubscriptionDashboardProps> = ({ onClose }) => {
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [pricing, setPricing] = useState<PricingInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSubscriptionData = async () => {
      try {
        setLoading(true);
        const [subData, pricingData] = await Promise.all([
          PulseAPI.getSubscription(),
          PulseAPI.getPricing()
        ]);
        setSubscription(subData);
        setPricing(pricingData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load subscription data');
      } finally {
        setLoading(false);
      }
    };

    loadSubscriptionData();
  }, []);

  const getTierIcon = (tier: string) => {
    switch (tier) {
      case 'pro': return Crown;
      case 'enterprise': return Users;
      default: return Sparkles;
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'pro': return 'text-blue-600 bg-blue-100';
      case 'enterprise': return 'text-purple-600 bg-purple-100';
      default: return 'text-green-600 bg-green-100';
    }
  };

  const formatUsageBar = (used: number, quota: number, unlimited: boolean) => {
    if (unlimited) {
      return (
        <div className="flex items-center space-x-2">
          <div className="flex-1 bg-green-100 rounded-full h-2">
            <div className="bg-green-500 h-2 rounded-full w-1/4"></div>
          </div>
          <span className="text-sm text-green-600 font-medium">Unlimited</span>
        </div>
      );
    }

    const percentage = quota > 0 ? Math.min((used / quota) * 100, 100) : 0;
    const isNearLimit = percentage > 80;
    const isAtLimit = percentage >= 100;

    return (
      <div className="flex items-center space-x-2">
        <div className="flex-1 bg-gray-100 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all duration-300 ${
              isAtLimit ? 'bg-red-500' : isNearLimit ? 'bg-yellow-500' : 'bg-blue-500'
            }`}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          ></div>
        </div>
        <span className={`text-sm font-medium ${
          isAtLimit ? 'text-red-600' : isNearLimit ? 'text-yellow-600' : 'text-gray-600'
        }`}>
          {used} / {quota}
        </span>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-lg w-full mx-4">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Loading subscription data...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-lg w-full mx-4">
          <div className="flex items-center text-red-600 mb-4">
            <AlertCircle className="w-6 h-6 mr-2" />
            <span className="font-semibold">Error loading subscription</span>
          </div>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={onClose}
            className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  if (!subscription || !pricing) return null;

  const TierIcon = getTierIcon(subscription.subscription_tier);
  const tierColorClass = getTierColor(subscription.subscription_tier);
  const currentTier = pricing.tiers[subscription.subscription_tier];

  const handleUpgrade = async (targetTier: 'pro' | 'enterprise') => {
    try {
      // In a real implementation, this would integrate with Stripe
      console.log(`Upgrading to ${targetTier}`);
      alert(`Upgrade to ${targetTier} - Stripe integration coming soon!`);
    } catch (err) {
      console.error('Upgrade failed:', err);
      alert('Upgrade failed. Please try again.');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b p-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Subscription & Usage</h2>
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-xl font-semibold"
          >
            ×
          </button>
        </div>

        <div className="p-6 space-y-8">
          {/* Current Plan */}
          <div className="bg-gray-50 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-full ${tierColorClass}`}>
                  <TierIcon className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-xl font-bold capitalize">{subscription.subscription_tier} Plan</h3>
                  <p className="text-gray-600">
                    {currentTier?.price ? `$${currentTier.price}/month` : 'Free'}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-500">
                  {subscription.billing_cycle.days_remaining} days remaining in cycle
                </div>
              </div>
            </div>
          </div>

          {/* Usage Statistics */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* Pulse Usage */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-center space-x-2 mb-4">
                <Zap className="w-5 h-5 text-blue-600" />
                <h4 className="font-semibold text-gray-900">Pulse Usage</h4>
              </div>
              {formatUsageBar(
                subscription.usage.pulses.used, 
                subscription.usage.pulses.quota,
                subscription.usage.pulses.unlimited
              )}
              <p className="text-sm text-gray-500 mt-2">
                Monthly pulse tracking limit
              </p>
            </div>

            {/* AI Enhancement Usage */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex items-center space-x-2 mb-4">
                <Sparkles className="w-5 h-5 text-purple-600" />
                <h4 className="font-semibold text-gray-900">AI Enhancements</h4>
              </div>
              {formatUsageBar(
                subscription.usage.ai_enhancements.used,
                subscription.usage.ai_enhancements.quota,
                subscription.usage.ai_enhancements.unlimited
              )}
              <p className="text-sm text-gray-500 mt-2">
                AI-powered pulse insights
                {subscription.usage.ai_cost_cents > 0 && (
                  <span className="ml-2 text-green-600">
                    (${(subscription.usage.ai_cost_cents / 100).toFixed(2)} this cycle)
                  </span>
                )}
              </p>
            </div>
          </div>

          {/* Features */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h4 className="font-semibold text-gray-900 mb-4 flex items-center">
              <TrendingUp className="w-5 h-5 mr-2 text-green-600" />
              Active Features
            </h4>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${subscription.features.advanced_analytics ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                <span className={subscription.features.advanced_analytics ? 'text-gray-900' : 'text-gray-400'}>
                  Advanced Analytics
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${subscription.features.export_enabled ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                <span className={subscription.features.export_enabled ? 'text-gray-900' : 'text-gray-400'}>
                  Data Export
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${subscription.features.priority_processing ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                <span className={subscription.features.priority_processing ? 'text-gray-900' : 'text-gray-400'}>
                  Priority Processing
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${subscription.features.custom_prompts ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                <span className={subscription.features.custom_prompts ? 'text-gray-900' : 'text-gray-400'}>
                  Custom AI Prompts
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${subscription.features.team_workspaces > 1 ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                <span className={subscription.features.team_workspaces > 1 ? 'text-gray-900' : 'text-gray-400'}>
                  Team Workspaces ({subscription.features.team_workspaces})
                </span>
              </div>
            </div>
          </div>

          {/* Upgrade Options */}
          {subscription.subscription_tier === 'free' && (
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-6">
              <h4 className="font-semibold text-gray-900 mb-4 flex items-center">
                <Crown className="w-5 h-5 mr-2 text-blue-600" />
                Upgrade Your Plan
              </h4>
              <div className="grid md:grid-cols-2 gap-4">
                {/* Pro Upgrade */}
                <div className="bg-white rounded-lg p-4 border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-lg">Pro</span>
                    <span className="text-blue-600 font-bold">${pricing.tiers.pro.price}/mo</span>
                  </div>
                  <p className="text-sm text-gray-600 mb-4">{pricing.tiers.pro.description}</p>
                  <button 
                    onClick={() => handleUpgrade('pro')}
                    className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center"
                  >
                    <CreditCard className="w-4 h-4 mr-2" />
                    Upgrade to Pro
                  </button>
                </div>

                {/* Enterprise Upgrade */}
                <div className="bg-white rounded-lg p-4 border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-lg">Enterprise</span>
                    <span className="text-purple-600 font-bold">${pricing.tiers.enterprise.price}/mo</span>
                  </div>
                  <p className="text-sm text-gray-600 mb-4">{pricing.tiers.enterprise.description}</p>
                  <button 
                    onClick={() => handleUpgrade('enterprise')}
                    className="w-full bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors flex items-center justify-center"
                  >
                    <Users className="w-4 h-4 mr-2" />
                    Upgrade to Enterprise
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};