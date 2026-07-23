import React, { useRef, useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { Environment, OrbitControls } from '@react-three/drei';
import { Camera, Hand, Move, ZoomIn, Loader2 } from 'lucide-react';
import { CADModel } from './components/CADModel';
import { useHandTracking } from './hooks/useHandTracking';

export default function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [hudVisible, setHudVisible] = useState(true);
  const [sensitivity, setSensitivity] = useState(1);
  const [wireframe, setWireframe] = useState(false);
  const [autoRotate, setAutoRotate] = useState(false);
  const [parts, setParts] = useState({
    base: true,
    vertical: true,
    pins: true
  });
  
  const [activeTool, setActiveTool] = useState('Select');
  const [activeSidebar, setActiveSidebar] = useState('navigator');
  const [menuModal, setMenuModal] = useState<string | null>(null);

  const { mode, isReady, transformRef, resetTransform, snapTransform } = useHandTracking(videoRef, canvasRef, sensitivity);

  const togglePart = (part: keyof typeof parts) => {
    setParts(p => ({ ...p, [part]: !p[part] }));
  };

  useEffect(() => {
    let activeStream: MediaStream | null = null;
    
    if (cameraEnabled && videoRef.current) {
      navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" } })
        .then((stream) => {
          activeStream = stream;
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            videoRef.current.play().catch(e => console.log("Play before load:", e));
            videoRef.current.onloadedmetadata = () => {
              videoRef.current?.play().catch(e => console.error("Play error:", e));
            };
          }
        })
        .catch(err => {
          console.error("Camera access error:", err);
          setCameraEnabled(false);
        });
    }

    return () => {
      if (activeStream) {
        activeStream.getTracks().forEach(track => track.stop());
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [cameraEnabled]);

  const ModeIcon = () => {
    switch (mode) {
      case 'rotate': return <Camera className="w-5 h-5 text-[#005cb9]" />;
      case 'pan': return <Move className="w-5 h-5 text-green-500" />;
      case 'zoom': return <ZoomIn className="w-5 h-5 text-[#ff8c00]" />;
      default: return <Hand className="w-5 h-5 text-[#a0a0a0]" />;
    }
  };

  return (
    <div className="w-full h-screen bg-[#1e1e1e] text-[#d4d4d4] font-sans overflow-hidden flex flex-col select-none">
      
      {/* Top Header / Menu Bar */}
      <div className="h-10 bg-[#2d2d2d] border-b border-[#3e3e3e] flex items-center px-4 justify-between z-20">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 bg-[#005cb9] rounded flex items-center justify-center font-bold text-white text-[10px]">NX</div>
            <span className="text-xs font-semibold tracking-wide text-white flex items-center gap-2">
              NX Gesture Interface
              {!isReady && <Loader2 className="w-3 h-3 text-[#005cb9] animate-spin" />}
            </span>
          </div>
          <div className="flex gap-4 text-[11px] text-[#a0a0a0]">
            {['File', 'Edit', 'View', 'Analysis', 'Tools'].map(menu => (
              <span 
                key={menu} 
                className="hover:text-white cursor-pointer relative"
                onClick={() => setMenuModal(menuModal === menu ? null : menu)}
              >
                {menu}
                {menuModal === menu && (
                  <div className="absolute top-full left-0 mt-2 w-32 bg-[#2d2d2d] border border-[#3e3e3e] rounded shadow-lg z-50">
                    <div className="py-1">
                      <div className="px-4 py-2 hover:bg-[#005cb9] hover:text-white cursor-pointer" onClick={(e) => e.stopPropagation()}>New...</div>
                      <div className="px-4 py-2 hover:bg-[#005cb9] hover:text-white cursor-pointer" onClick={(e) => e.stopPropagation()}>Open</div>
                      <div className="border-t border-[#3e3e3e] my-1"></div>
                      <div className="px-4 py-2 hover:bg-[#005cb9] hover:text-white cursor-pointer" onClick={(e) => e.stopPropagation()}>Exit</div>
                    </div>
                  </div>
                )}
              </span>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-4">
          {cameraEnabled && (
            <div className="flex items-center gap-2 bg-[#005cb9]/20 border border-[#005cb9] px-3 py-1 rounded-full">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-[10px] font-medium text-[#005cb9]">SENSOR ACTIVE</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden" onClick={() => setMenuModal(null)}>
        {/* Sidebar: Resource Bar */}
        <div className="w-12 bg-[#252525] border-r border-[#3e3e3e] flex flex-col items-center py-4 gap-6 z-10">
          <div onClick={() => setActiveSidebar('navigator')} className={`w-8 h-8 flex items-center justify-center rounded text-lg cursor-pointer transition-colors ${activeSidebar === 'navigator' ? 'bg-[#3e3e3e] text-white' : 'text-[#a0a0a0] hover:text-white'}`}>📂</div>
          <div onClick={() => setActiveSidebar('measure')} className={`w-8 h-8 flex items-center justify-center rounded text-lg cursor-pointer transition-colors ${activeSidebar === 'measure' ? 'bg-[#3e3e3e] text-white' : 'text-[#a0a0a0] hover:text-white'}`}>📐</div>
          <div onClick={() => setActiveSidebar('shield')} className={`w-8 h-8 flex items-center justify-center rounded text-lg cursor-pointer transition-colors ${activeSidebar === 'shield' ? 'bg-[#3e3e3e] text-white' : 'text-[#a0a0a0] hover:text-white'}`}>🛡️</div>
          <div onClick={() => setActiveSidebar('settings')} className={`w-8 h-8 flex items-center justify-center rounded text-lg cursor-pointer transition-colors ${activeSidebar === 'settings' ? 'bg-[#3e3e3e] text-white' : 'text-[#a0a0a0] hover:text-white'}`}>⚙️</div>
        </div>

        {/* Left Panel: Dynamic Sidebar */}
        <div className="w-60 bg-[#2d2d2d] border-r border-[#3e3e3e] flex flex-col z-10">
          {activeSidebar === 'navigator' && (
            <>
              <div className="p-3 border-b border-[#3e3e3e] flex justify-between items-center bg-[#333333]">
                <span className="text-[11px] font-bold uppercase tracking-wider text-white">Part Navigator</span>
              </div>
              <div className="flex-1 p-2 text-[11px] overflow-hidden overflow-y-auto">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2 p-1 bg-[#3e3e3e] rounded text-white cursor-pointer"><span>▼</span> <span>Bracket_Assembly_01</span></div>
                  <div className="ml-4 flex items-center gap-2 p-1 text-[#a0a0a0] cursor-pointer hover:text-white"><span>▶</span> <span>History Mode</span></div>
                  <div className="ml-4 flex items-center gap-2 p-1 text-[#a0a0a0] cursor-pointer hover:text-white"><span>▶</span> <span>Datum Coordinate System</span></div>
                  <div className="ml-4 flex flex-col gap-1">
                    <div className="flex items-center gap-2 p-1 bg-[#005cb9]/10 text-[#005cb9] rounded cursor-pointer"><span>▼</span> <span>Model Geometry</span></div>
                    <div onClick={() => togglePart('base')} className={`ml-4 flex items-center gap-2 p-1 cursor-pointer rounded transition-colors ${parts.base ? 'text-[#d4d4d4] hover:bg-[#3e3e3e]' : 'text-[#666] line-through'}`}><span>•</span> <span>Base Plate</span></div>
                    <div onClick={() => togglePart('vertical')} className={`ml-4 flex items-center gap-2 p-1 cursor-pointer rounded transition-colors ${parts.vertical ? 'text-[#d4d4d4] hover:bg-[#3e3e3e]' : 'text-[#666] line-through'}`}><span>•</span> <span>Vertical Brackets</span></div>
                    <div onClick={() => togglePart('pins')} className={`ml-4 flex items-center gap-2 p-1 cursor-pointer rounded transition-colors ${parts.pins ? 'text-[#d4d4d4] hover:bg-[#3e3e3e]' : 'text-[#666] line-through'}`}><span>•</span> <span>Cross Pins & Holes</span></div>
                  </div>
                  <div className="ml-4 flex items-center gap-2 p-1 text-[#a0a0a0] cursor-pointer hover:text-white"><span>▶</span> <span>Surfacing Ops</span></div>
                </div>
              </div>
            </>
          )}

          {activeSidebar === 'measure' && (
            <>
              <div className="p-3 border-b border-[#3e3e3e] flex justify-between items-center bg-[#333333]">
                <span className="text-[11px] font-bold uppercase tracking-wider text-white">Measurement Tool</span>
              </div>
              <div className="p-4 text-[11px]">
                <p className="text-[#a0a0a0] mb-4">Select two points on the model to calculate distance.</p>
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between items-center bg-[#3e3e3e] p-2 rounded">
                    <span className="text-white">Point 1</span>
                    <span className="font-mono text-[#005cb9]">Selected</span>
                  </div>
                  <div className="flex justify-between items-center border border-[#3e3e3e] p-2 rounded text-[#888]">
                    <span>Point 2</span>
                    <span className="font-mono">Waiting...</span>
                  </div>
                  <div className="mt-4 pt-4 border-t border-[#3e3e3e]">
                    <div className="text-[#a0a0a0] mb-1">Distance (Linear)</div>
                    <div className="text-2xl text-white font-light">-- mm</div>
                  </div>
                </div>
              </div>
            </>
          )}

          {activeSidebar === 'shield' && (
            <>
              <div className="p-3 border-b border-[#3e3e3e] flex justify-between items-center bg-[#333333]">
                <span className="text-[11px] font-bold uppercase tracking-wider text-white">Validation</span>
              </div>
              <div className="p-4 text-[11px]">
                <div className="flex items-start gap-3 mb-4 p-2 bg-green-500/10 border border-green-500/30 rounded">
                  <div className="text-green-500 mt-0.5">✓</div>
                  <div>
                    <div className="text-white font-medium">Clearance Check</div>
                    <div className="text-[#a0a0a0] mt-1">No interference detected.</div>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-2 bg-yellow-500/10 border border-yellow-500/30 rounded">
                  <div className="text-yellow-500 mt-0.5">!</div>
                  <div>
                    <div className="text-white font-medium">Draft Angle</div>
                    <div className="text-[#a0a0a0] mt-1">Some faces have &lt; 2° draft.</div>
                  </div>
                </div>
              </div>
            </>
          )}

          {activeSidebar === 'settings' && (
            <>
              <div className="p-3 border-b border-[#3e3e3e] flex justify-between items-center bg-[#333333]">
                <span className="text-[11px] font-bold uppercase tracking-wider text-white">Settings</span>
              </div>
              <div className="p-4 text-[11px] space-y-4">
                <div>
                  <div className="text-[#a0a0a0] mb-2">Display Units</div>
                  <select className="w-full bg-[#1e1e1e] border border-[#3e3e3e] text-white p-1 rounded outline-none">
                    <option>Millimeters (mm)</option>
                    <option>Inches (in)</option>
                  </select>
                </div>
                <div>
                  <div className="text-[#a0a0a0] mb-2">Grid Snap</div>
                  <label className="flex items-center gap-2 text-white cursor-pointer">
                    <input type="checkbox" defaultChecked className="accent-[#005cb9]" /> Enable Snapping
                  </label>
                </div>
                <div>
                  <div className="text-[#a0a0a0] mb-2">Background Theme</div>
                  <select className="w-full bg-[#1e1e1e] border border-[#3e3e3e] text-white p-1 rounded outline-none">
                    <option>Dark Studio (Default)</option>
                    <option>Light Engineering</option>
                    <option>High Contrast</option>
                  </select>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Central Viewport */}
        <div className="flex-1 relative bg-gradient-to-br from-[#1a1c1e] to-[#2a2d32] overflow-hidden flex flex-col">
          
          {/* Viewport Toolbar */}
          <div className="h-10 bg-[#2d2d2d] border-b border-[#3e3e3e] flex items-center px-4 justify-between z-20">
            <div className="flex gap-1">
              {['Select', 'Sketch', 'Extrude', 'Revolve', 'Hole', 'Measure'].map(tool => (
                <button 
                  key={tool}
                  onClick={() => setActiveTool(tool)}
                  className={`px-3 py-1 text-[11px] font-medium rounded transition-colors ${
                    activeTool === tool 
                      ? 'bg-[#005cb9] text-white' 
                      : 'text-[#a0a0a0] hover:bg-[#3e3e3e] hover:text-white'
                  }`}
                >
                  {tool}
                </button>
              ))}
            </div>
            <div className="text-[10px] text-[#888] font-mono">
              Tool: {activeTool}
            </div>
          </div>

          <div className="flex-1 relative">
            {/* 3D Perspective Lines / Grid */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-10 z-0">
              <div className="w-full h-full" style={{ backgroundImage: 'radial-gradient(#ffffff 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>
            </div>
            
            <div className="absolute inset-0 z-10">
              <Canvas camera={{ position: [0, 2, 5], fov: 50 }}>
                <ambientLight intensity={0.5} />
                <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
                <Environment preset="city" />
                <CADModel 
                  transform={transformRef.current} 
                  wireframe={wireframe}
                  showBase={parts.base}
                  showVertical={parts.vertical}
                  showPins={parts.pins}
                  autoRotate={autoRotate}
                  activeTool={activeTool}
                />
                {/* We keep OrbitControls available for mouse fallback, but mostly rely on gestures */}
                <OrbitControls makeDefault enableZoom enablePan enableRotate />
              </Canvas>
            </div>

            {/* Viewport HUD Elements */}
            {hudVisible && (
              <>
                <div className="absolute top-6 left-6 flex flex-col gap-1 pointer-events-none z-20">
                  <div className="text-[24px] font-light text-white">Perspective</div>
                  <div className="text-[10px] font-mono text-[#005cb9]">X: 142.02 Y: -88.10 Z: 0.00</div>
                </div>

                <div className="absolute top-6 right-6 w-24 h-24 border border-[#3e3e3e] bg-[#252525]/80 flex items-center justify-center flex-col pointer-events-none z-20">
                  <div className="relative w-12 h-12 border border-white/20 transform rotate-45">
                    <div className="absolute -top-1 left-1/2 -translate-x-1/2 text-[8px] font-bold -rotate-45">TOP</div>
                  </div>
                  <span className="mt-2 text-[9px] text-[#a0a0a0]">VIEW CUBE</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Right Panel: Gesture Intelligence */}
        <div className="w-72 bg-[#2d2d2d] border-l border-[#3e3e3e] flex flex-col z-10">
          <div className="p-3 border-b border-[#3e3e3e] bg-[#333333]">
            <span className="text-[11px] font-bold uppercase tracking-wider text-white">Gesture Logic</span>
          </div>
          
          <div className="p-4 flex flex-col gap-6 overflow-y-auto">
            
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[#d4d4d4]">Camera Input</span>
              <button
                onClick={() => setCameraEnabled(!cameraEnabled)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-1 focus:ring-[#005cb9] ${
                  cameraEnabled ? 'bg-[#005cb9]' : 'bg-[#3e3e3e]'
                }`}
              >
                <span
                  className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                    cameraEnabled ? 'translate-x-5' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className="relative aspect-video bg-[#1a1c1e] rounded-lg overflow-hidden border border-[#3e3e3e]">
              <video
                ref={videoRef}
                className={`absolute inset-0 w-full h-full object-cover z-0 ${cameraEnabled ? 'opacity-100' : 'opacity-0'}`}
                style={{ transform: 'scaleX(-1)' }}
                playsInline
                muted
                autoPlay
              />
              <canvas
                ref={canvasRef}
                className={`absolute inset-0 w-full h-full pointer-events-none object-cover z-10 ${cameraEnabled ? 'opacity-100' : 'opacity-0'}`}
                style={{ transform: 'scaleX(-1)' }}
              />
              {!cameraEnabled && (
                <div className="absolute inset-0 flex items-center justify-center text-[#a0a0a0] flex-col gap-2">
                  <Camera className="w-5 h-5 opacity-50" />
                  <span className="text-[10px]">Camera Off</span>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3">
              <div className="text-[10px] font-bold text-[#888] uppercase tracking-wider">Active Gesture</div>
              <div className={`p-3 bg-[#333] border-l-2 rounded flex items-center gap-3 ${
                mode === 'rotate' ? 'border-[#005cb9]' : 
                mode === 'pan' ? 'border-green-500' : 
                mode === 'zoom' ? 'border-[#ff8c00]' : 'border-transparent opacity-50'
              }`}>
                <div className="p-1.5 bg-[#252525] rounded-md border border-[#3e3e3e]">
                  <ModeIcon />
                </div>
                <div className="flex flex-col">
                  <span className="text-[11px] text-white capitalize font-medium">{mode === 'idle' ? 'Scanning...' : mode}</span>
                  <span className="text-[9px] text-[#a0a0a0]">
                    {mode === 'rotate' && 'Fist recognized'}
                    {mode === 'pan' && 'Open Hand recognized'}
                    {mode === 'zoom' && 'Pinch scaling engaged'}
                    {mode === 'idle' && 'Waiting for input'}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-2 border border-[#3e3e3e] p-3 rounded bg-[#252525]">
              <div className="text-[10px] font-bold mb-2 text-[#888] uppercase tracking-wider">Quick Actions</div>
              <div className="grid grid-cols-2 gap-2">
                <button onClick={resetTransform} className="p-2 bg-[#3e3e3e] text-[9px] text-white rounded hover:bg-[#4e4e4e] transition-colors">Recalibrate</button>
                <button onClick={() => setHudVisible(!hudVisible)} className={`p-2 text-[9px] text-white rounded transition-colors ${hudVisible ? 'bg-[#3e3e3e] hover:bg-[#4e4e4e]' : 'bg-[#005cb9] hover:bg-[#004a99]'}`}>Toggle HUD</button>
                <button onClick={snapTransform} className="p-2 bg-[#3e3e3e] text-[9px] text-white rounded hover:bg-[#4e4e4e] transition-colors">Snap View</button>
                <button onClick={() => setSensitivity(s => s === 1 ? 2 : 1)} className={`p-2 text-[9px] text-white rounded transition-colors ${sensitivity > 1 ? 'bg-[#005cb9] hover:bg-[#004a99]' : 'bg-[#3e3e3e] hover:bg-[#4e4e4e]'}`}>
                  Sensitivity: {sensitivity}x
                </button>
                <button onClick={() => setWireframe(w => !w)} className={`p-2 text-[9px] text-white rounded transition-colors ${wireframe ? 'bg-[#005cb9] hover:bg-[#004a99]' : 'bg-[#3e3e3e] hover:bg-[#4e4e4e]'}`}>Wireframe</button>
                <button onClick={() => setAutoRotate(r => !r)} className={`p-2 text-[9px] text-white rounded transition-colors ${autoRotate ? 'bg-[#005cb9] hover:bg-[#004a99]' : 'bg-[#3e3e3e] hover:bg-[#4e4e4e]'}`}>Auto-Rotate</button>
              </div>
            </div>

            <div className="mt-2 border border-[#3e3e3e] p-3 rounded bg-[#252525]">
              <div className="text-[10px] font-bold mb-2 text-[#888] uppercase tracking-wider">Instructions</div>
              <div className="text-[10px] text-[#a0a0a0] space-y-2">
                <p className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-[#005cb9]"></span> <strong className="text-[#d4d4d4]">Fist:</strong> Rotate Model</p>
                <p className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-green-500"></span> <strong className="text-[#d4d4d4]">Open Hand:</strong> Pan Model</p>
                <p className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-[#ff8c00]"></span> <strong className="text-[#d4d4d4]">Pinch:</strong> Zoom (Move Up/Down)</p>
              </div>
            </div>
            
          </div>
        </div>
      </div>

      {/* Bottom Status Bar */}
      <div className="h-6 bg-[#005cb9] flex items-center px-4 justify-between text-white text-[10px] font-medium z-20">
        <div className="flex items-center gap-4">
          <span>Ready</span>
          <span className="opacity-60">|</span>
          <span>Design & modeling simplified via hand control</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="bg-white/20 px-2 rounded">TRACKING: {isReady ? 'ONLINE' : 'INITIALIZING'}</span>
          <span>Work Layer: 1</span>
        </div>
      </div>

    </div>
  );
}
