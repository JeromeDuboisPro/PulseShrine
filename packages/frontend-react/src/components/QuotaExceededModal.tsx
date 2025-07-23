import { AlertCircle, CreditCard, Crown, Sparkles } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { PulseAPI, PricingInfo, SubscriptionInfo } from '../api';

interface QuotaExceededModalProps {
  isOpen: boolean;
  onClose: () => void;
  quotaType: 'pulses' | 'ai_enhancements';
  currentTier: string;
  subscription?: SubscriptionInfo;
  onUpgrade?: () => void;
}

export const QuotaExceededModal: React.FC<QuotaExceededModalProps> = ({
  isOpen,
  onClose,
  quotaType,
  currentTier,
  subscription,
  onUpgrade
}) => {
  const [pricing, setPricing] = useState<PricingInfo | null>(null);

  useEffect(() => {
    if (isOpen) {
      PulseAPI.getPricing().then(setPricing).catch(console.error);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const getQuotaInfo = () => {
    if (quotaType === 'pulses') {
      const pulseQuota = subscription?.usage.pulses.quota || (currentTier === 'free' ? 10 : 'unlimited');
      return {
        title: 'Pulse Limit Reached',
        icon: Sparkles,
        message: `You've reached your monthly limit of ${pulseQuota === -1 ? 'pulses' : `${pulseQuota} pulses`}.`,
        suggestion: 'Upgrade to Pro for unlimited pulse tracking and AI-powered insights!'
      };
    } else {
      const aiQuota = subscription?.usage.ai_enhancements.quota || (pricing?.tiers.free.features.ai_enhancements || 3);
      const quotaText = currentTier === 'free' 
        ? `${aiQuota} AI samples` 
        : (aiQuota === -1 ? 'AI enhancements' : `${aiQuota} AI enhancements`);
      
      return {
        title: 'AI Enhancement Limit Reached',
        icon: Crown,
        message: `You've used all ${quotaText} for this month.`,
        suggestion: currentTier === 'free' 
          ? 'Love the AI insights? Upgrade to Pro for unlimited AI-powered enhancements!'
          : 'Upgrade to unlock more AI-powered pulse insights and personalized recommendations!'
      };
    }
  };

  const quotaInfo = getQuotaInfo();

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-md w-full p-6 relative">
        {/* Header */}
        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2 rounded-full bg-yellow-100">
            <AlertCircle className="w-6 h-6 text-yellow-600" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900">{quotaInfo.title}</h3>
        </div>

        {/* Message */}
        <p className="text-gray-600 mb-2">{quotaInfo.message}</p>
        <p className="text-gray-800 font-medium mb-6">{quotaInfo.suggestion}</p>

        {/* Benefits */}
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 mb-6">
          <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
            <Crown className="w-4 h-4 mr-2 text-blue-600" />
            Pro Plan Benefits
          </h4>
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span>Unlimited pulse tracking</span>
            </li>
            <li className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span>AI-powered insights & enhancements</span>
            </li>
            <li className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span>Advanced analytics & reporting</span>
            </li>
            <li className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span>Priority processing & support</span>
            </li>
            <li className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span>Data export capabilities</span>
            </li>
          </ul>
        </div>

        {/* Pricing */}
        <div className="text-center mb-6">
          <div className="text-3xl font-bold text-blue-600">
            {pricing?.currency_symbol || '$'}{pricing?.tiers.pro.price || 9.99}
          </div>
          <div className="text-sm text-gray-500">per month</div>
        </div>

        {/* Actions */}
        <div className="flex space-x-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Maybe Later
          </button>
          <button
            onClick={() => {
              if (onUpgrade) {
                onUpgrade();
              } else {
                // Default upgrade action
                alert('Upgrade feature coming soon! Stripe integration in progress.');
              }
              onClose();
            }}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center space-x-2"
          >
            <CreditCard className="w-4 h-4" />
            <span>Upgrade Now</span>
          </button>
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <span className="sr-only">Close</span>
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
};