import React from 'react';

interface PulseShrineLogoSvgProps {
  className?: string;
  size?: number;
  variant?: 'purple' | 'white';
}

export const PulseShrineLogoSvg: React.FC<PulseShrineLogoSvgProps> = ({ 
  className = "", 
  size = 50,
  variant = 'purple'
}) => {
  // Generate unique IDs for gradients to avoid conflicts
  const uniqueId = Math.random().toString(36).substr(2, 9);
  
  // Color scheme based on variant
  const colors = variant === 'white' ? {
    primary: '#ffffff',
    secondary: '#f8fafc',
    tertiary: '#e2e8f0',
    nodeGradientStart: '#ffffff',
    nodeGradientEnd: '#f1f5f9',
    accentGradientStart: '#ffffff',
    accentGradientEnd: '#f8fafc'
  } : {
    primary: '#9333ea',
    secondary: '#e0aaff',
    tertiary: '#f0c4ff',
    nodeGradientStart: '#f0c4ff',
    nodeGradientEnd: '#e0aaff',
    accentGradientStart: '#ffffff',
    accentGradientEnd: '#f0c4ff'
  };
  
  return (
    <svg 
      viewBox="0 0 400 400" 
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      className={`${className} animate-pulse-gentle`}
      style={{
        filter: 'drop-shadow(0 0 4px rgba(147, 51, 234, 0.2))'
      }}
    >
      {/* Definitions */}
      <defs>
        {/* Gradient for nodes */}
        <radialGradient id={`nodeGradient-${uniqueId}`}>
          <stop offset="0%" style={{stopColor:colors.nodeGradientStart, stopOpacity:1}} />
          <stop offset="100%" style={{stopColor:colors.nodeGradientEnd, stopOpacity:1}} />
        </radialGradient>
        
        {/* Gradient for connections */}
        <linearGradient id={`connectionGradient-${uniqueId}`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{stopColor:colors.secondary, stopOpacity:0.3}} />
          <stop offset="100%" style={{stopColor:colors.primary, stopOpacity:0.1}} />
        </linearGradient>
        
        {/* Accent gradient */}
        <linearGradient id={`accentGradient-${uniqueId}`} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" style={{stopColor:colors.accentGradientStart, stopOpacity:0.8}} />
          <stop offset="100%" style={{stopColor:colors.accentGradientEnd, stopOpacity:0.6}} />
        </linearGradient>
      </defs>
      
      {/* Neural Network Shrine Structure */}
      <g transform="translate(200, 200)">
        
        {/* Base connections (circuit patterns) */}
        {/* Foundation level */}
        <line x1="-120" y1="120" x2="-80" y2="120" stroke={colors.primary} strokeWidth="2.5" opacity="0.4"/>
        <line x1="-40" y1="120" x2="0" y2="120" stroke={colors.primary} strokeWidth="2.5" opacity="0.4"/>
        <line x1="40" y1="120" x2="80" y2="120" stroke={colors.primary} strokeWidth="2.5" opacity="0.4"/>
        <line x1="80" y1="120" x2="120" y2="120" stroke={colors.primary} strokeWidth="2.5" opacity="0.4"/>
        
        {/* Vertical connections */}
        <line x1="-80" y1="120" x2="-80" y2="60" stroke={colors.primary} strokeWidth="2.5" opacity="0.4"/>
        <line x1="0" y1="120" x2="0" y2="60" stroke={colors.primary} strokeWidth="2.5" opacity="0.4"/>
        <line x1="80" y1="120" x2="80" y2="60" stroke={colors.primary} strokeWidth="2.5" opacity="0.4"/>
        
        {/* Mid-level connections */}
        <line x1="-80" y1="60" x2="-40" y2="20" stroke={colors.primary} strokeWidth="2.5" opacity="0.5"/>
        <line x1="0" y1="60" x2="0" y2="20" stroke={colors.primary} strokeWidth="2.5" opacity="0.5"/>
        <line x1="80" y1="60" x2="40" y2="20" stroke={colors.primary} strokeWidth="2.5" opacity="0.5"/>
        
        {/* Upper connections */}
        <line x1="-40" y1="20" x2="0" y2="-40" stroke={colors.primary} strokeWidth="2.5" opacity="0.6"/>
        <line x1="0" y1="20" x2="0" y2="-40" stroke={colors.primary} strokeWidth="2.5" opacity="0.6"/>
        <line x1="40" y1="20" x2="0" y2="-40" stroke={colors.primary} strokeWidth="2.5" opacity="0.6"/>
        
        {/* Top connections */}
        <line x1="0" y1="-40" x2="0" y2="-100" stroke={colors.primary} strokeWidth="2.5" opacity="0.7"/>
        
        {/* Shrine outline structure */}
        {/* Base platform */}
        <rect x="-100" y="100" width="200" height="20" fill="none" stroke={colors.primary} strokeWidth="3" opacity="0.7"/>
        
        {/* Main body */}
        <path d="M -80,100 L -80,40 L -40,0 L 0,-60 L 40,0 L 80,40 L 80,100" 
              fill="none" 
              stroke={colors.primary} 
              strokeWidth="3" 
              opacity="0.8"/>
        
        {/* Roof structure */}
        <path d="M -100,40 L 0,-80 L 100,40" 
              fill="none" 
              stroke={colors.primary} 
              strokeWidth="3" 
              opacity="0.8"/>
        
        {/* Neural nodes with rapid activity animations */}
        {/* Foundation nodes */}
        <circle cx="-80" cy="120" r="6" fill={`url(#nodeGradient-${uniqueId})`} stroke={colors.primary} strokeWidth="1.5" opacity="0.8">
          <animate attributeName="opacity" values="0.8;1.0;0.8" dur="1.5s" repeatCount="indefinite" begin="0s"/>
        </circle>
        <circle cx="0" cy="120" r="6" fill={`url(#nodeGradient-${uniqueId})`} stroke={colors.primary} strokeWidth="1.5" opacity="0.8">
          <animate attributeName="opacity" values="0.8;1.0;0.8" dur="1.5s" repeatCount="indefinite" begin="0.3s"/>
        </circle>
        <circle cx="80" cy="120" r="6" fill={`url(#nodeGradient-${uniqueId})`} stroke={colors.primary} strokeWidth="1.5" opacity="0.8">
          <animate attributeName="opacity" values="0.8;1.0;0.8" dur="1.5s" repeatCount="indefinite" begin="0.6s"/>
        </circle>
        
        {/* Mid-level nodes */}
        <circle cx="-80" cy="60" r="8" fill={`url(#nodeGradient-${uniqueId})`} stroke={colors.primary} strokeWidth="1.5" opacity="0.9">
          <animate attributeName="opacity" values="0.9;1.0;0.9" dur="1.2s" repeatCount="indefinite" begin="0.2s"/>
        </circle>
        <circle cx="0" cy="60" r="8" fill={`url(#nodeGradient-${uniqueId})`} stroke={colors.primary} strokeWidth="1.5" opacity="0.9">
          <animate attributeName="opacity" values="0.9;1.0;0.9" dur="1.2s" repeatCount="indefinite" begin="0.5s"/>
        </circle>
        <circle cx="80" cy="60" r="8" fill={`url(#nodeGradient-${uniqueId})`} stroke={colors.primary} strokeWidth="1.5" opacity="0.9">
          <animate attributeName="opacity" values="0.9;1.0;0.9" dur="1.2s" repeatCount="indefinite" begin="0.8s"/>
        </circle>
        
        {/* Upper nodes with rapid pulsing */}
        <circle cx="-40" cy="20" r="10" fill={`url(#nodeGradient-${uniqueId})`} stroke={colors.primary} strokeWidth="2">
          <animate attributeName="r" values="10;12;10" dur="1.8s" repeatCount="indefinite" begin="0s"/>
          <animate attributeName="opacity" values="1.0;0.7;1.0" dur="1.8s" repeatCount="indefinite" begin="0s"/>
        </circle>
        <circle cx="40" cy="20" r="10" fill={`url(#nodeGradient-${uniqueId})`} stroke={colors.primary} strokeWidth="2">
          <animate attributeName="r" values="10;12;10" dur="1.8s" repeatCount="indefinite" begin="0.9s"/>
          <animate attributeName="opacity" values="1.0;0.7;1.0" dur="1.8s" repeatCount="indefinite" begin="0.9s"/>
        </circle>
        
        {/* Central processing node - main neural activity */}
        <circle cx="0" cy="-40" r="12" fill={`url(#nodeGradient-${uniqueId})`} stroke={colors.primary} strokeWidth="2.5">
          <animate attributeName="r" values="12;15;12" dur="2s" repeatCount="indefinite" begin="0s"/>
          <animate attributeName="opacity" values="1.0;0.6;1.0" dur="2s" repeatCount="indefinite" begin="0s"/>
        </circle>
        
        {/* Apex node - sacred energy */}
        <circle cx="0" cy="-100" r="8" fill={`url(#accentGradient-${uniqueId})`} stroke={colors.primary} strokeWidth="2.5">
          <animate attributeName="opacity" values="1.0;0.5;1.0" dur="2.5s" repeatCount="indefinite" begin="0s"/>
        </circle>
        
        {/* Circuit detail patterns */}
        <rect x="-4" y="-44" width="8" height="8" fill="none" stroke={colors.primary} strokeWidth="1.5" opacity="0.7"/>
        <circle cx="0" cy="-40" r="4" fill={colors.primary} opacity="0.9"/>
        
        {/* Additional architectural details */}
        <line x1="-40" y1="100" x2="-40" y2="80" stroke={colors.primary} strokeWidth="2.5" opacity="0.5"/>
        <line x1="40" y1="100" x2="40" y2="80" stroke={colors.primary} strokeWidth="2.5" opacity="0.5"/>
        
        {/* Small connector nodes */}
        <circle cx="-40" cy="90" r="4" fill={colors.primary} opacity="0.6"/>
        <circle cx="40" cy="90" r="4" fill={colors.primary} opacity="0.6"/>
        <circle cx="0" cy="40" r="4" fill={colors.primary} opacity="0.6"/>
      </g>
    </svg>
  );
};