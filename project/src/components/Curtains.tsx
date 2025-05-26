import React, { useEffect, useState } from 'react';
import useScrollPosition from '../hooks/useScrollPosition';

const Curtains: React.FC = () => {
  const scrollPosition = useScrollPosition();
  const [curtainOpen, setCurtainOpen] = useState(0);
  
  useEffect(() => {
    // Calculate curtain opening percentage based on scroll
    const maxScroll = 500; // Reduced scroll distance for faster opening
    const openAmount = Math.min((scrollPosition / maxScroll) * 100, 100);
    setCurtainOpen(openAmount);
  }, [scrollPosition]);

  // Calculate curtain positions based on opening percentage
  const leftPosition = `${-120 * (curtainOpen / 100)}%`;
  const rightPosition = `${120 * (curtainOpen / 100)}%`;
  
  // Dynamic swaying effect based on opening percentage
  const swayAmount = Math.sin(curtainOpen * 0.1) * (1 - curtainOpen / 100) * 2;
  const leftSway = `rotate(${swayAmount}deg)`;
  const rightSway = `rotate(${-swayAmount}deg)`;
  
  return (
    <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
      {/* Left curtain */}
      <div 
        className="absolute top-0 left-0 w-1/2 h-full bg-gradient-to-r from-red-900 to-red-800 shadow-2xl origin-top"
        style={{ 
          transform: `translateX(${leftPosition}) ${leftSway}`,
          transition: 'transform 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)',
          backgroundImage: `
            linear-gradient(to right, #7f1d1d, #991b1b),
            repeating-linear-gradient(90deg, rgba(0,0,0,0.1), rgba(0,0,0,0.1) 1px, transparent 1px, transparent 20px)
          `,
        }}
      >
        {/* Curtain folds with dynamic shadows */}
        <div className="h-full w-full flex">
          {[...Array(10)].map((_, i) => (
            <div 
              key={`left-fold-${i}`} 
              className="h-full flex-1 border-r border-red-950/30 relative overflow-hidden"
              style={{
                backgroundImage: 'linear-gradient(90deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0) 50%, rgba(0,0,0,0.3) 100%)',
                transform: `scaleY(${1 + Math.sin(i * 0.5 + curtainOpen * 0.05) * 0.02})`,
                transition: 'transform 0.5s ease-out',
              }}
            >
              <div 
                className="absolute inset-0"
                style={{
                  background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent)',
                  transform: `translateX(${Math.sin(curtainOpen * 0.1 + i) * 100}%)`,
                  transition: 'transform 1s ease-out',
                }}
              />
            </div>
          ))}
        </div>
      </div>
      
      {/* Right curtain */}
      <div 
        className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-red-900 to-red-800 shadow-2xl origin-top"
        style={{ 
          transform: `translateX(${rightPosition}) ${rightSway}`,
          transition: 'transform 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)',
          backgroundImage: `
            linear-gradient(to left, #7f1d1d, #991b1b),
            repeating-linear-gradient(90deg, rgba(0,0,0,0.1), rgba(0,0,0,0.1) 1px, transparent 1px, transparent 20px)
          `,
        }}
      >
        {/* Curtain folds with dynamic shadows */}
        <div className="h-full w-full flex">
          {[...Array(10)].map((_, i) => (
            <div 
              key={`right-fold-${i}`} 
              className="h-full flex-1 border-l border-red-950/30 relative overflow-hidden"
              style={{
                backgroundImage: 'linear-gradient(90deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0) 50%, rgba(0,0,0,0.3) 100%)',
                transform: `scaleY(${1 + Math.sin(i * 0.5 + curtainOpen * 0.05) * 0.02})`,
                transition: 'transform 0.5s ease-out',
              }}
            >
              <div 
                className="absolute inset-0"
                style={{
                  background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent)',
                  transform: `translateX(${Math.sin(curtainOpen * 0.1 + i) * 100}%)`,
                  transition: 'transform 1s ease-out',
                }}
              />
            </div>
          ))}
        </div>
      </div>
      
      {/* Curtain rod with enhanced appearance */}
      <div className="absolute top-0 left-0 right-0 h-6 bg-gradient-to-b from-amber-700 to-amber-800 border-b-4 border-amber-600 z-20 shadow-md"></div>
    </div>
  );
};

export default Curtains;