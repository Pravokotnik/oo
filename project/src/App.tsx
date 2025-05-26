import React, { useEffect, useState } from 'react';
import Curtains from './components/Curtains';
import useScrollPosition from './hooks/useScrollPosition';
import { Glasses } from 'lucide-react';

function App() {
  const scrollPosition = useScrollPosition();
  const [signPosition, setSignPosition] = useState(0);
  const [swingAngle, setSwingAngle] = useState(0);
  const [imageScale, setImageScale] = useState(1);
  const [xrayMode, setXrayMode] = useState(false);
  const [selectedAnnotation, setSelectedAnnotation] = useState<string | null>(null);
  const [curtainsFullyOpen, setCurtainsFullyOpen] = useState(false);
  const [annotationText, setAnnotationText] = useState("Welcome to the exhibition");
  const [showAnnotation, setShowAnnotation] = useState(true);
  const [isAnnotationFading, setIsAnnotationFading] = useState(false);
  const [isGlassesEntering, setIsGlassesEntering] = useState(false);

  const annotations = [
    // Left side annotations
    { 
      id: 'canvas', 
      label: '>> CANVAS', 
      description: 'Circles and lines', 
      top: '35%', 
      left: '5%',
      connectPoint: { x: 35, y: 25 }
    },
    { 
      id: 'vase', 
      label: '>> VASE', 
      description: 'AI Vase recognition from the picture.', 
      top: '55%', 
      left: '5%',
      connectPoint: { x: 35, y: 80 }
    },
    // Right side annotations
    { 
      id: 'face', 
      label: '>> FACE', 
      description: 'Face expression AI recognizer', 
      top: '35%', 
      left: '95%',
      connectPoint: { x: 67, y: 20 }
    },
    { 
      id: 'palette', 
      label: '>> PALETTE', 
      description: 'AI Color palette', 
      top: '55%', 
      left: '95%',
      connectPoint: { x: 55, y: 37 }
    },
    // Center annotation for poses
    { 
      id: 'poses', 
      label: '>> POSES', 
      description: 'AI Pose detection analyzer', 
      top: '50%', 
      left: '95%',
      connectPoint: { x: 70, y: 50 }
    }
  ];

  const redirectToSite = (annotationId: string) => {
    const urls: { [key: string]: string } = {
      canvas: './hough.html',
      vase: './object_viewer.html',
      face: './run-faces',
      palette: './hsl_color_viewer.html',
      poses: './run-poses'
    };
    const url = urls[annotationId];
    if (!url) return;
    window.location.href = url;

    // const animationScreen = document.querySelector('#animation-screen');
    // if (animationScreen) {
    //   animationScreen.classList.add('active');
    // }
    
    // setTimeout(() => {
    //   if (url) {
    //     // Redirect to the specified URL
    //   }
    // }, 500);
  };

  useEffect(() => {
    const maxScroll = 200;
    const position = Math.max(0, Math.min((scrollPosition / maxScroll) * 100, 100));
    const swingAmount = Math.sin(scrollPosition * 0.02) * 2;
    const minScale = 0.8;
    const maxScale = 1;
    const scaleProgress = Math.min(scrollPosition / maxScroll, 1);
    const currentScale = minScale + (maxScale - minScale) * scaleProgress;
    
    setSignPosition(position);
    setSwingAngle(swingAmount);
    setImageScale(currentScale);
    setCurtainsFullyOpen(scrollPosition >= maxScroll);
  }, [scrollPosition]);

  const handleAnnotationClick = () => {
    if (annotationText === "Welcome to the exhibition") {
      setAnnotationText("Click on the glasses to start.");
    } else {
      setIsAnnotationFading(true);
      setTimeout(() => {
        setShowAnnotation(false);
        setIsAnnotationFading(false);
      }, 500);
    }
  };

  const toggleXrayMode = () => {
    if (!xrayMode) {
      setIsGlassesEntering(true);
      setTimeout(() => setIsGlassesEntering(false), 1000);
    }
    setXrayMode(!xrayMode);
    setSelectedAnnotation(null);
    setAnnotationText("Welcome to the exhibition");
    setShowAnnotation(true);
  };

  return (
    <div className={`font-serif fixed inset-0 transition-all duration-500 ${xrayMode ? 'xray-vision' : ''}`}>
      {/* Glasses frame overlay */}
      <div className={`glasses-frame ${xrayMode ? 'active' : ''} ${isGlassesEntering ? 'entering' : ''}`} />
      
      <section className="h-screen relative overflow-hidden flex flex-col items-center justify-center bg-neutral-900">
        <div className="absolute inset-0 flex items-center justify-center bg-neutral-900">
          {/* Theater background */}
          <div 
            className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-40 transition-opacity duration-500"
            style={{
              backgroundImage: 'url(../src/theater.png)',
              filter: xrayMode ? 'brightness(0.3) contrast(1.4) hue-rotate(180deg) saturate(200%)' : 'brightness(0.6)',
            }}
          />

          {/* Speech bubble */}
          {curtainsFullyOpen && showAnnotation && !xrayMode && (
            <div 
              className={`absolute z-10 bg-white px-4 py-2 rounded-xl cursor-pointer transition-all duration-500 ease-in-out`}
              style={{
                top: '14%',
                left: '60%',
                filter: xrayMode ? 'brightness(1.2) contrast(1.4) hue-rotate(180deg) saturate(200%)' : 'none',
                animation: isAnnotationFading ? 'fadeOut 0.5s ease-in-out forwards' : 'fadeIn 0.5s ease-in-out forwards'
              }}
              onClick={handleAnnotationClick}
            >
              <div className="relative">
                <p className="text-base font-sans">{annotationText}</p>
                {/* Speech bubble tail */}
                <div 
                  className="absolute -bottom-4 left-2"
                  style={{
                    width: '12px',
                    height: '12px',
                    background: 'white',
                    clipPath: 'polygon(0 0, 100% 0, 0 100%)',
                    transform: 'rotate(-10deg)'
                  }}
                ></div>
              </div>
            </div>
          )}

          <div className="relative w-full max-w-4xl px-20">
            <img 
              src="../src/painter.png" 
              alt="Painter" 
              className="max-h-[70vh] w-auto object-contain transition-all duration-300 ease-out mx-auto"
              style={{
                transform: `scale(${imageScale})`,
                filter: xrayMode ? 'brightness(1.2) contrast(1.4) hue-rotate(180deg) saturate(200%)' : 'none'
              }}
            />
            
            {/* X-ray annotations */}
            {xrayMode && annotations.map((annotation) => (
              <div
                key={annotation.id}
                className="absolute"
                style={{ 
                  top: annotation.connectPoint.y + '%',
                  left: annotation.connectPoint.x + '%',
                }}
              >
                {/* Horizontal line */}
                <div 
                  className="relative"
                  style={{
                    position: 'absolute',
                    width: '200px',
                    transform: annotation.left === '5%' ? 'translateX(-100%)' : 'translateX(0)',
                  }}
                >
                  <div 
                    className="absolute top-1/2 h-[2px] bg-green-500 shadow-[0_0_5px_#00ff00]"
                    style={{
                      width: '100%',
                    }}
                  />
                  
                  {/* Label box */}
                  <div 
                    className={`absolute top-1/2 transform -translate-y-1/2 cursor-pointer
                             bg-black/90 text-green-500 p-3 rounded-sm
                             border border-green-500/50 shadow-[0_0_10px_#00ff00]
                             hover:scale-105 transition-all duration-300
                             font-mono tracking-wider text-sm`}
                    style={{
                      left: annotation.left === '5%' ? '0' : '100%',
                      transform: `translateY(-50%) ${annotation.left === '5%' ? 'translateX(-100%)' : ''}`,
                      clipPath: 'polygon(0 0, 100% 0, 98% 50%, 100% 100%, 0 100%, 2% 50%)'
                    }}
                    onClick={() => {
                      // setSelectedAnnotation(annotation.id === selectedAnnotation ? null : annotation.id);
                      // setAnnotationText(annotation.description);
                      redirectToSite(annotation.id);
                    }}
                  >
                    <div className="whitespace-nowrap">
                      {annotation.label}
                      {selectedAnnotation === annotation.id && (
                        <div className="mt-1 text-green-400/80 text-xs">{annotation.description}</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* X-ray glasses toggle */}
        {curtainsFullyOpen && (
          <div
            onClick={toggleXrayMode}
            className={`absolute bottom-8 z-30 cursor-pointer transform hover:scale-110 transition-all duration-300
                       opacity-0 animate-[fadeIn_0.5s_ease-out_forwards]`}
            style={{
              filter: xrayMode ? 'drop-shadow(0 0 10px #00ff00) brightness(1.2)' : 'none'
            }}
          >
            <Glasses 
              size={48}
              className={`${xrayMode ? 'text-green-400' : 'text-white'} transition-colors duration-300`}
              strokeWidth={1.5}
            />
          </div>
        )}
        
        {/* Hanging wooden sign */}
        <div 
          className="absolute top-[20vh] left-1/2 z-20"
          style={{
            transform: `translate(-50%, -${signPosition}vh) rotate(${swingAngle}deg)`,
            transition: 'transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
            transformOrigin: 'top center',
          }}
        >
          {/* Left rope */}
          <div 
            className="absolute left-0 -top-[20vh] w-[2px] h-[40vh]"
            style={{
              background: `repeating-linear-gradient(
                180deg,
                #8B4513,
                #654321 5px,
                #8B4513 10px
              )`,
              transformOrigin: 'top',
              transform: `rotate(${swingAngle * 0.5}deg)`,
              boxShadow: '1px 1px 2px rgba(0,0,0,0.3)'
            }}
          >
            {/* Rope texture */}
            <div className="absolute inset-0 opacity-40"
              style={{
                backgroundImage: `repeating-linear-gradient(
                  45deg,
                  transparent,
                  transparent 2px,
                  #000 2px,
                  #000 3px
                )`
              }}
            ></div>
          </div>
          
          {/* Right rope */}
          <div 
            className="absolute right-0 -top-[20vh] w-[2px] h-[40vh]"
            style={{
              background: `repeating-linear-gradient(
                180deg,
                #8B4513,
                #654321 5px,
                #8B4513 10px
              )`,
              transformOrigin: 'top',
              transform: `rotate(${swingAngle * 0.5}deg)`,
              boxShadow: '-1px 1px 2px rgba(0,0,0,0.3)'
            }}
          >
            {/* Rope texture */}
            <div className="absolute inset-0 opacity-40"
              style={{
                backgroundImage: `repeating-linear-gradient(
                  45deg,
                  transparent,
                  transparent 2px,
                  #000 2px,
                  #000 3px
                )`
              }}
            ></div>
          </div>
          
          {/* Wooden sign */}
          <div className="relative mt-[20vh]">
            <div 
              className="px-10 py-5 rounded"
              style={{
                backgroundColor: '#8B4513',
                backgroundImage: `
                  linear-gradient(90deg, 
                    rgba(139,69,19,0.9) 0%, 
                    #8B4513 20%, 
                    #8B4513 80%, 
                    rgba(139,69,19,0.9) 100%
                  ),
                  repeating-linear-gradient(
                    90deg,
                    transparent,
                    transparent 20px,
                    rgba(0,0,0,0.1) 20px,
                    rgba(0,0,0,0.1) 40px
                  ),
                  repeating-linear-gradient(
                    0deg,
                    rgba(255,255,255,0.05),
                    rgba(255,255,255,0.05) 2px,
                    transparent 2px,
                    transparent 4px
                  )
                `,
                border: '3px solid #654321',
                boxShadow: `
                  0 4px 8px rgba(0,0,0,0.3),
                  inset 0 2px 4px rgba(255,255,255,0.1),
                  inset 0 -2px 4px rgba(0,0,0,0.2)
                `
              }}
            >
              <div className="text-center relative">
                <h2 
                  className="text-[#FFE4C4] text-2xl font-bold tracking-wider whitespace-nowrap"
                  style={{
                    textShadow: '2px 2px 2px rgba(0,0,0,0.5)',
                    fontFamily: 'var(--font-serif)'
                  }}
                >
                  Welcome to Pixellect
                </h2>
                <p 
                  className="text-[#FFE4C4]/80 text-sm mt-1 tracking-widest font-sans"
                  style={{
                    textShadow: '1px 1px 1px rgba(0,0,0,0.5)'
                  }}
                >
                  Exploring images with AI
                </p>
              </div>
            </div>
            
            {/* Wood grain edges */}
            <div 
              className="absolute -bottom-2 left-0 right-0 h-2 rounded-b"
              style={{
                background: 'linear-gradient(0deg, #654321, #8B4513)',
                boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
              }}
            ></div>
          </div>
        </div>
        
        <Curtains />
      </section>
    </div>
  );
}

export default App;