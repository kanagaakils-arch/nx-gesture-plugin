import { useEffect, useRef, useState } from 'react';
import { FilesetResolver, HandLandmarker } from '@mediapipe/tasks-vision';

export type GestureMode = 'idle' | 'rotate' | 'pan' | 'zoom';

interface TransformState {
  rotation: [number, number, number];
  position: [number, number, number];
  scale: number;
}

export function useHandTracking(videoRef: React.RefObject<HTMLVideoElement | null>, canvasRef: React.RefObject<HTMLCanvasElement | null>, sensitivity: number = 1) {
  const [mode, setMode] = useState<GestureMode>('idle');
  const [isReady, setIsReady] = useState(false);
  const landmarkerRef = useRef<HandLandmarker | null>(null);
  
  const transformRef = useRef<TransformState>({
    rotation: [0, 0, 0],
    position: [0, 0, 0],
    scale: 1
  });

  const lastHandPosRef = useRef<{ x: number; y: number; z: number } | null>(null);
  const smoothedPosRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    let active = true;
    
    async function init() {
      try {
        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.12/wasm"
        );
        const landmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
            delegate: "GPU"
          },
          runningMode: "VIDEO",
          numHands: 1,
          minHandDetectionConfidence: 0.7,
          minHandPresenceConfidence: 0.7,
          minTrackingConfidence: 0.7
        });
        
        if (active) {
          landmarkerRef.current = landmarker;
          setIsReady(true);
        }
      } catch (e) {
        console.error("Error initializing hand tracking:", e);
      }
    }
    init();
    
    return () => {
      active = false;
      if (landmarkerRef.current) {
        landmarkerRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    if (!isReady || !videoRef.current) return;
    
    let reqId: number;
    let lastVideoTime = -1;
    
    const processFrame = () => {
      const video = videoRef.current;
      
      if (!video || !landmarkerRef.current || video.readyState < 2 || video.videoWidth === 0 || video.videoHeight === 0) {
        reqId = requestAnimationFrame(processFrame);
        return;
      }
      
      try {
        if (video.currentTime !== lastVideoTime) {
          lastVideoTime = video.currentTime;
          const results = landmarkerRef.current.detectForVideo(video, performance.now());
          
          const canvas = canvasRef.current;
          const ctx = canvas?.getContext('2d');
          if (canvas && video && video.videoWidth) {
            if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
              canvas.width = video.videoWidth;
              canvas.height = video.videoHeight;
            }
          }

        if (results.landmarks && results.landmarks.length > 0) {
          const landmarks = results.landmarks[0];
          
          if (ctx && canvas) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            // Draw skeleton guide
            ctx.strokeStyle = '#005cb9';
            ctx.lineWidth = 2;
            const connections = [
              [0,1,2,3,4], [0,5,6,7,8], [5,9,13,17], [9,10,11,12], [13,14,15,16], [17,18,19,20], [0,17]
            ];
            connections.forEach(line => {
              ctx.beginPath();
              for(let i=0; i<line.length; i++) {
                const point = landmarks[line[i]];
                const x = point.x * canvas.width;
                const y = point.y * canvas.height;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
              }
              ctx.stroke();
            });
            // Draw joints
            ctx.fillStyle = '#4ade80';
            landmarks.forEach(point => {
              ctx.beginPath();
              ctx.arc(point.x * canvas.width, point.y * canvas.height, 3, 0, 2 * Math.PI);
              ctx.fill();
            });
          }
          
          // Heuristics for gestures
          const wrist = landmarks[0];
          const thumbTip = landmarks[4];
          const indexTip = landmarks[8];
          const middleTip = landmarks[12];
          const ringTip = landmarks[16];
          const pinkyTip = landmarks[20];
          
          const indexMcp = landmarks[5];
          const middleMcp = landmarks[9];
          const ringMcp = landmarks[13];
          const pinkyMcp = landmarks[17];
          
          const get2DDist = (p1: any, p2: any) => Math.hypot(p1.x - p2.x, p1.y - p2.y);
          
          // Use 2D distance for robust extension detection in webcam feeds
          const isIndexExtended = get2DDist(indexTip, wrist) > get2DDist(indexMcp, wrist) * 1.2;
          const isMiddleExtended = get2DDist(middleTip, wrist) > get2DDist(middleMcp, wrist) * 1.2;
          const isRingExtended = get2DDist(ringTip, wrist) > get2DDist(ringMcp, wrist) * 1.2;
          const isPinkyExtended = get2DDist(pinkyTip, wrist) > get2DDist(pinkyMcp, wrist) * 1.2;
          
          const distThumbIndex = get2DDist(thumbTip, indexTip);
          
          // Refined gesture states
          const extendedCount = [isIndexExtended, isMiddleExtended, isRingExtended, isPinkyExtended].filter(Boolean).length;
          
          // Pinch: Thumb and index are close
          const isPinch = distThumbIndex < 0.08 && get2DDist(indexTip, indexMcp) > 0.04;
          
          // Fist: No fingers extended, thumb and index not in pinch
          const isFist = extendedCount === 0 && !isPinch;
          
          // Open: At least 3 fingers extended
          const isOpen = extendedCount >= 3 && !isPinch;
          
          let currentMode: GestureMode = 'idle';
          if (isPinch) currentMode = 'zoom';
          else if (isFist) currentMode = 'rotate';
          else if (isOpen) currentMode = 'pan';
          
          setMode(currentMode);
          
          // Calculate center of hand (average of wrist and lower knuckles for stable reference point)
          const handCenter = {
            x: (wrist.x + indexMcp.x + pinkyMcp.x) / 3,
            y: (wrist.y + indexMcp.y + pinkyMcp.y) / 3,
            z: (wrist.z + indexMcp.z + pinkyMcp.z) / 3
          };
          
          const get3DDist = (p1: any, p2: any) => Math.hypot(p1.x - p2.x, p1.y - p2.y, (p1.z || 0) - (p2.z || 0));

          // Apply Adaptive EMA (Exponential Moving Average) for precision and jitter reduction
          if (smoothedPosRef.current) {
            const dist = get3DDist(handCenter, { ...smoothedPosRef.current, z: handCenter.z });
            // Dynamic smoothing: if moving fast, less smoothing (e.g. 0.3) for responsiveness
            // If holding still, more smoothing (e.g. 0.9) to eliminate micro-jitters
            const SMOOTHING = Math.max(0.3, Math.min(0.92, 1 - dist * 12));
            smoothedPosRef.current.x = smoothedPosRef.current.x * SMOOTHING + handCenter.x * (1 - SMOOTHING);
            smoothedPosRef.current.y = smoothedPosRef.current.y * SMOOTHING + handCenter.y * (1 - SMOOTHING);
          } else {
            smoothedPosRef.current = { x: handCenter.x, y: handCenter.y };
          }
          
          if (currentMode !== 'idle') {
            if (lastHandPosRef.current) {
              const dx = smoothedPosRef.current.x - lastHandPosRef.current.x;
              const dy = smoothedPosRef.current.y - lastHandPosRef.current.y;
              
              // Smaller deadzone due to adaptive smoothing
              if (Math.abs(dx) > 0.0003 || Math.abs(dy) > 0.0003) {
                // Non-linear response curve for precise small movements and fast large movements
                const curve = (val: number) => Math.sign(val) * Math.pow(Math.abs(val), 1.2) * 18;
                
                if (currentMode === 'rotate') {
                  transformRef.current.rotation[1] += curve(dx) * sensitivity; // Y-axis rotation
                  transformRef.current.rotation[0] += curve(dy) * sensitivity; // X-axis rotation
                } else if (currentMode === 'pan') {
                  transformRef.current.position[0] -= curve(dx) * 2 * sensitivity;
                  transformRef.current.position[1] += curve(dy) * 2 * sensitivity;
                } else if (currentMode === 'zoom') {
                  const newScale = transformRef.current.scale * (1 - curve(dy) * 0.8 * sensitivity);
                  transformRef.current.scale = Math.max(0.1, Math.min(newScale, 5));
                }
              }
            }
            lastHandPosRef.current = { x: smoothedPosRef.current.x, y: smoothedPosRef.current.y, z: handCenter.z };
          } else {
             lastHandPosRef.current = null;
          }
        } else {
          setMode('idle');
          lastHandPosRef.current = null;
          smoothedPosRef.current = null;
          const canvas = canvasRef.current;
          const ctx = canvas?.getContext('2d');
          if (ctx && canvas) ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
      }
      } catch (err) {
        console.error("Hand tracking error:", err);
      }
      
      reqId = requestAnimationFrame(processFrame);
    };
    
    reqId = requestAnimationFrame(processFrame);
    
    return () => cancelAnimationFrame(reqId);
  }, [isReady, videoRef]);

  const resetTransform = () => {
    transformRef.current = { rotation: [0, 0, 0], position: [0, 0, 0], scale: 1 };
  };

  const snapTransform = () => {
    const snap = (val: number) => Math.round(val / (Math.PI / 2)) * (Math.PI / 2);
    transformRef.current.rotation = [
      snap(transformRef.current.rotation[0]),
      snap(transformRef.current.rotation[1]),
      snap(transformRef.current.rotation[2])
    ];
  };

  return { mode, isReady, transformRef, resetTransform, snapTransform };
}
