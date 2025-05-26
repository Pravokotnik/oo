import { useState, useEffect } from 'react';

const useScrollPosition = () => {
  const [scrollPosition, setScrollPosition] = useState(0);
  
  useEffect(() => {
    const updatePosition = () => {
      setScrollPosition(window.scrollY);
    };
    
    // Add event listener
    window.addEventListener('scroll', updatePosition);
    
    // Initial position
    updatePosition();
    
    // Cleanup
    return () => window.removeEventListener('scroll', updatePosition);
  }, []);
  
  return scrollPosition;
};

export default useScrollPosition;