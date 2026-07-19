import React, { useState, useEffect, useRef } from 'react';
import { Camera, Radio, Plus, Trash2, ShieldAlert, CheckCircle, XCircle, Info, RefreshCw, Activity } from 'lucide-react';
import { api } from '../utils/api';

function WebcamPlayer({ camera, testingMode }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const isInitializingRef = useRef(false);

  const [webcamError, setWebcamError] = useState(null);
  const [useFallbackImg, setUseFallbackImg] = useState(false);
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);

  // Camera Diagnostics Telemetry State
  const [diagInfo, setDiagInfo] = useState({
    cameraName: camera.name || 'Integrated Camera',
    streamStatus: 'Initializing',
    resolution: 'Resolving...',
    readyState: 'HAVE_NOTHING (0)',
    framesReceived: 0
  });

  const frameCounterRef = useRef(0);
  const animFrameIdRef = useRef(null);

  useEffect(() => {
    console.log("Component Mounted");

    const startCamera = async () => {
      // Prevent multiple concurrent initialization calls or duplicate calls
      if (isInitializingRef.current || (streamRef.current && streamRef.current.active)) {
        return;
      }

      isInitializingRef.current = true;
      setWebcamError(null);
      setUseFallbackImg(false);
      setIsVideoPlaying(false);
      setDiagInfo(prev => ({ ...prev, streamStatus: 'Connecting...', cameraName: camera.name }));

      console.log("Camera Started");

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const errStr = "No webcam detected (Browser mediaDevices API unsupported)";
        console.error("[Camera Error] Browser mediaDevices API unavailable");
        setWebcamError(errStr);
        setDiagInfo(prev => ({ ...prev, streamStatus: 'Error: No Webcam API' }));
        setUseFallbackImg(true);
        isInitializingRef.current = false;
        return;
      }

      let detectedCameraLabel = camera.name || 'Integrated Camera';
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(d => d.kind === 'videoinput');
        if (videoDevices.length === 0) {
          const errStr = "No webcam detected";
          console.error("[Camera Error] No video input devices found.");
          setWebcamError(errStr);
          setDiagInfo(prev => ({ ...prev, streamStatus: 'Error: No Webcam Detected' }));
          setUseFallbackImg(true);
          isInitializingRef.current = false;
          return;
        }
        if (videoDevices[0].label) {
          detectedCameraLabel = videoDevices[0].label;
        }
      } catch (e) {
        console.warn("[Camera Debug] Device enumeration warning:", e);
      }

      try {
        const constraints = { video: true, audio: false };
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        console.log("MediaStream Created");

        if (!stream || !stream.active || stream.getVideoTracks().length === 0) {
          const errStr = "Invalid or inactive MediaStream created";
          console.error("[Camera Error]", errStr);
          setWebcamError(errStr);
          setDiagInfo(prev => ({ ...prev, streamStatus: 'Error: Invalid Stream' }));
          isInitializingRef.current = false;
          return;
        }

        streamRef.current = stream;

        const videoEl = videoRef.current;
        if (!videoEl) {
          const errStr = "Video DOM element reference not found";
          console.error("[Camera Error]", errStr);
          setWebcamError(errStr);
          setDiagInfo(prev => ({ ...prev, streamStatus: 'Error: Video Element Missing' }));
          setUseFallbackImg(true);
          isInitializingRef.current = false;
          return;
        }

        // Attach MediaStream ONLY ONCE to video element
        if (videoEl.srcObject !== stream) {
          videoEl.srcObject = stream;
          console.log("Video Attached");
        }

        // Execute play() inside onloadedmetadata to prevent play() request interruption
        videoEl.onloadedmetadata = async () => {
          try {
            await videoEl.play();
            console.log("Video Playing");
            setIsVideoPlaying(true);

            const track = stream.getVideoTracks()[0];
            let resStr = `${videoEl.videoWidth || 640}x${videoEl.videoHeight || 480}`;
            if (track && track.getSettings) {
              const s = track.getSettings();
              resStr = `${s.width || videoEl.videoWidth || 640}x${s.height || videoEl.videoHeight || 480}`;
            }

            setDiagInfo({
              cameraName: detectedCameraLabel,
              streamStatus: 'Active Streaming',
              resolution: resStr,
              readyState: getReadyStateLabel(videoEl.readyState),
              framesReceived: 0
            });

            // Start animation loop for frame counter & readyState telemetry
            const countFrames = () => {
              if (videoEl && videoEl.readyState >= 2) {
                frameCounterRef.current += 1;
                setDiagInfo(prev => ({
                  ...prev,
                  readyState: getReadyStateLabel(videoEl.readyState),
                  framesReceived: frameCounterRef.current
                }));
              }
              animFrameIdRef.current = requestAnimationFrame(countFrames);
            };
            animFrameIdRef.current = requestAnimationFrame(countFrames);

          } catch (playErr) {
            if (playErr.name !== 'AbortError') {
              console.error("[Camera Debug] Playback error:", playErr);
              const playErrorMsg = `Video Playback Failed: ${playErr.message || 'Autoplay restricted'}`;
              setWebcamError(playErrorMsg);
              setDiagInfo(prev => ({ ...prev, streamStatus: 'Error: Playback Blocked' }));
            }
          }
        };

        // Fallback trigger if metadata is already loaded when listener bound
        if (videoEl.readyState >= 1) {
          videoEl.onloadedmetadata();
        }

      } catch (err) {
        console.error("[Camera Debug] getUserMedia error:", err);
        let errorMsg = err.message || "Failed to access webcam";
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          errorMsg = `Permission Denied: ${err.message || 'Access blocked by user or browser setting'}`;
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
          errorMsg = 'No webcam detected';
        }
        setWebcamError(errorMsg);
        setDiagInfo(prev => ({ ...prev, streamStatus: `Error: ${err.name || 'Denied'}` }));
        setUseFallbackImg(true);
      } finally {
        isInitializingRef.current = false;
      }
    };

    if (testingMode || camera.source === '0') {
      startCamera();
    } else {
      setUseFallbackImg(true);
      setDiagInfo(prev => ({
        ...prev,
        streamStatus: 'Active Streaming (Backend MJPEG)',
        resolution: '640x480 (Server MJPEG)',
        readyState: 'HAVE_ENOUGH_DATA (4)'
      }));
    }

    return () => {
      console.log("Component Unmounted");
      if (animFrameIdRef.current) {
        cancelAnimationFrame(animFrameIdRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      isInitializingRef.current = false;
    };
  }, [camera.id, testingMode, camera.source]);

  const getReadyStateLabel = (state) => {
    switch (state) {
      case 0: return 'HAVE_NOTHING (0)';
      case 1: return 'HAVE_METADATA (1)';
      case 2: return 'HAVE_CURRENT_DATA (2)';
      case 3: return 'HAVE_FUTURE_DATA (3)';
      case 4: return 'HAVE_ENOUGH_DATA (4)';
      default: return `STATE_${state}`;
    }
  };

  const isWebcamActive = (testingMode || camera.source === '0') && !useFallbackImg;

  return (
    <div className="w-full h-full flex flex-col relative">
      {/* Video / Stream Container */}
      <div className="w-full h-48 bg-[#0b0c10] border border-white/5 rounded-xl flex items-center justify-center relative overflow-hidden">
        {/* Unconditionally mounted video element for client webcam */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{
            display: isWebcamActive && !webcamError ? 'block' : 'none',
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            position: 'absolute',
            inset: 0,
            zIndex: 10,
            opacity: 1,
            visibility: 'visible'
          }}
          className="bg-black"
        />

        {/* Backend MJPEG image stream fallback */}
        {useFallbackImg || !testingMode ? (
          <img
            src={api.cameras.getStreamUrl(camera.id)}
            className="w-full h-full object-cover block relative z-10"
            alt={camera.name}
            onError={(e) => {
              console.error("[Camera Debug] Backend MJPEG image onError for camera:", camera.id);
            }}
          />
        ) : webcamError ? (
          <div className="flex flex-col items-center justify-center h-full p-4 text-center bg-[#0b0c10] z-20 relative">
            <Camera size={26} className="text-red-400 mb-2 animate-bounce" />
            <span className="text-red-400 font-semibold text-xs">{webcamError}</span>
            <span className="text-[10px] text-zinc-500 mt-1">Please verify browser webcam permissions</span>
          </div>
        ) : !isVideoPlaying ? (
          /* Placeholder standby spinner - automatically removed once stream starts playing */
          <div className="flex flex-col items-center justify-center gap-2 text-zinc-600 z-20 relative">
            <Radio size={28} className="text-indigo-400 animate-pulse" />
            <span className="text-[10px] uppercase font-bold tracking-wider text-zinc-400">Initializing Webcam Feed...</span>
          </div>
        ) : null}
      </div>

      {/* Camera Diagnostics Panel */}
      <div className="mt-3 bg-[#08090d] border border-white/5 p-3 rounded-xl space-y-1.5 text-[10px] font-mono">
        <div className="flex items-center justify-between border-b border-white/5 pb-1">
          <span className="text-zinc-500 font-semibold uppercase tracking-wider">Camera Name:</span>
          <span className="text-indigo-300 font-bold truncate max-w-[160px]">{diagInfo.cameraName}</span>
        </div>
        <div className="flex items-center justify-between border-b border-white/5 pb-1">
          <span className="text-zinc-500 font-semibold uppercase tracking-wider">Stream Status:</span>
          <span className={`font-bold ${diagInfo.streamStatus.includes('Active') ? 'text-emerald-400' : 'text-amber-400'}`}>
            {diagInfo.streamStatus}
          </span>
        </div>
        <div className="flex items-center justify-between border-b border-white/5 pb-1">
          <span className="text-zinc-500 font-semibold uppercase tracking-wider">Video Resolution:</span>
          <span className="text-zinc-200 font-bold">{diagInfo.resolution}</span>
        </div>
        <div className="flex items-center justify-between border-b border-white/5 pb-1">
          <span className="text-zinc-500 font-semibold uppercase tracking-wider">Ready State:</span>
          <span className="text-emerald-400 font-bold">{diagInfo.readyState}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-zinc-500 font-semibold uppercase tracking-wider">Frames Received:</span>
          <span className="text-indigo-400 font-bold font-mono">{diagInfo.framesReceived}</span>
        </div>
      </div>
    </div>
  );
}

export default function CameraManagement() {
  const [cameras, setCameras] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [error, setError] = useState('');
  const [testingMode, setTestingMode] = useState(true);

  // Diagnostic Modal State
  const [diagnosticLoading, setDiagnosticLoading] = useState(false);
  const [diagnosticModalOpen, setDiagnosticModalOpen] = useState(false);
  const [diagnosticResult, setDiagnosticResult] = useState(null);

  // Form parameters
  const [name, setName] = useState('');
  const [type, setType] = useState('usb');
  const [source, setSource] = useState('0');
  const [userId, setUserId] = useState('');

  // Telemetries tracking
  const [telemetry, setTelemetry] = useState({});

  useEffect(() => {
    fetchData();
  }, []);

  // Poll live JSON coordinate parameters every 1.5 seconds for actively connected cameras
  useEffect(() => {
    const timer = setInterval(() => {
      cameras.forEach((cam) => {
        if (cam.status === 'connected') {
          api.cameras.getTelemetry(cam.id)
            .then((data) => {
              setTelemetry((prev) => ({
                ...prev,
                [cam.id]: data
              }));
            })
            .catch(() => {});
        }
      });
    }, 1500);
    return () => clearInterval(timer);
  }, [cameras]);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const camData = await api.cameras.list();
      setCameras(camData);
      
      // Load employees list to bind camera mapping option
      const empData = await api.employees.list();
      setEmployees(empData);

      try {
        const modeRes = await api.cameras.getTestingMode();
        if (modeRes && typeof modeRes.testing_mode === 'boolean') {
          setTestingMode(modeRes.testing_mode);
        }
      } catch (e) {}
    } catch (err) {
      setError('Could not fetch cameras data registry');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleTestingMode = async (enabled) => {
    setLoading(true);
    try {
      await api.cameras.setTestingMode(enabled);
      setTestingMode(enabled);
      fetchData();
    } catch (err) {
      setError('Could not update camera testing mode');
    } finally {
      setLoading(false);
    }
  };

  const runCameraDiagnosticTest = async () => {
    setDiagnosticLoading(true);
    let cameraDetected = "No";
    let permissionState = "Denied";
    let streamResolution = "N/A";
    let activeStreamState = "No";

    try {
      if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(d => d.kind === 'videoinput');
        if (videoDevices.length > 0) {
          cameraDetected = `Yes (${videoDevices.length} device(s) found: ${videoDevices[0].label || 'Default Camera'})`;
        }
      }

      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        console.log("[Diagnostic Test] Requesting getUserMedia stream...");
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        console.log("[Diagnostic Test] getUserMedia stream acquired successfully:", stream);
        permissionState = "Granted";
        activeStreamState = `Yes (Active Stream ID: ${stream.id.substring(0, 8)})`;

        const track = stream.getVideoTracks()[0];
        if (track) {
          const settings = track.getSettings();
          streamResolution = `${settings.width || 640}x${settings.height || 480} @ ${settings.frameRate || 30}fps`;
        }

        // Release test stream
        stream.getTracks().forEach(t => t.stop());
      }
    } catch (err) {
      console.error("[Diagnostic Test Error]", err);
      permissionState = `Denied (${err.message || 'Permission blocked'})`;
    }

    setDiagnosticResult({
      detected: cameraDetected,
      permission: permissionState,
      resolution: streamResolution,
      activeStream: activeStreamState
    });
    setDiagnosticModalOpen(true);
    setDiagnosticLoading(false);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name || !source) {
      setError('Name and Source are required.');
      return;
    }
    setLoading(true);
    try {
      await api.cameras.create({
        name,
        type,
        source,
        user_id: userId ? parseInt(userId) : null
      });
      setFormOpen(false);
      setName('');
      setSource('0');
      setUserId('');
      fetchData();
    } catch (err) {
      setError(err.message || 'Error saving camera config');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Disconnect and remove this camera configuration?")) return;
    setLoading(true);
    try {
      await api.cameras.delete(id);
      fetchData();
    } catch (err) {
      setError('Error deleting camera configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleConnection = async (cam, action) => {
    setLoading(true);
    try {
      await api.cameras.update(cam.id, {
        status: action === 'connect' ? 'connected' : 'disconnected'
      });
      fetchData();
    } catch (err) {
      setError('Error toggling connection state');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Error Bar */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-4 py-3 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert size={15} />
            <span>{error}</span>
          </div>
          <button onClick={() => setError('')}><Trash2 size={14} /></button>
        </div>
      )}

      {/* Development Mode Banner */}
      {testingMode ? (
        <div className="bg-indigo-600/15 border border-indigo-500/30 text-indigo-300 text-xs px-4 py-3 rounded-xl flex items-center justify-between shadow-lg shadow-indigo-600/10">
          <div className="flex items-center gap-2.5 font-semibold">
            <span className="h-2 w-2 rounded-full bg-indigo-400 animate-ping" />
            <span>Development Mode - Using Laptop Webcam</span>
          </div>
          <button
            onClick={() => handleToggleTestingMode(false)}
            className="text-[10px] bg-white/10 hover:bg-white/20 text-white font-medium px-3 py-1.5 rounded-lg transition-all border border-white/10"
          >
            Switch to CCTV Mode
          </button>
        </div>
      ) : (
        <div className="bg-zinc-800/40 border border-white/5 text-zinc-400 text-xs px-4 py-2.5 rounded-xl flex items-center justify-between">
          <span className="font-medium text-zinc-300">Standard CCTV / RTSP Network Mode Active</span>
          <button
            onClick={() => handleToggleTestingMode(true)}
            className="text-[10px] bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400 font-medium px-3 py-1.5 rounded-lg border border-indigo-500/30 transition-all"
          >
            Enable Testing Mode (Laptop Webcam)
          </button>
        </div>
      )}

      {/* Controller header */}
      <div className="flex items-center justify-between">
        <h3 className="text-white font-bold text-sm tracking-wide">CAMERA MANAGEMENT BOARD</h3>
        
        <div className="flex items-center gap-3">
          <button
            onClick={runCameraDiagnosticTest}
            disabled={diagnosticLoading}
            className="bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all shrink-0"
            title="Run browser webcam diagnostic check"
          >
            <Camera size={14} className={diagnosticLoading ? "animate-spin" : ""} />
            <span>Camera Test</span>
          </button>

          <button onClick={fetchData} className="bg-white/5 hover:bg-white/10 border border-white/10 p-2.5 rounded-xl text-zinc-400 hover:text-white transition-all">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
          
          <button
            onClick={() => setFormOpen(prev => !prev)}
            className="hud-btn-primary text-xs shrink-0 flex items-center gap-2"
          >
            <Plus size={14} />
            <span>Add Camera</span>
          </button>
        </div>
      </div>

      {/* --- ADD CAMERA SUB-PANEL FORM --- */}
      {formOpen && (
        <div className="glass-card p-6 border-indigo-500/10 animate-slideDown">
          <h4 className="text-white text-xs font-bold uppercase tracking-wider mb-4 border-b border-white/5 pb-2">Configure Camera Endpoint</h4>
          <form onSubmit={handleCreate} className="grid grid-cols-4 gap-4 items-end">
            <div>
              <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Camera Label Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-[#0d0e12] border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white placeholder-white/20 focus:outline-none focus:border-indigo-500/40"
                placeholder="e.g. Workspace Left Cam"
                required
              />
            </div>
            
            <div>
              <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Device Type</label>
              <select
                value={type}
                onChange={(e) => {
                  setType(e.target.value);
                  setSource(e.target.value === 'usb' ? '0' : 'rtsp://');
                }}
                className="w-full bg-[#0d0e12] border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40"
              >
                <option value="usb">USB Camera Index</option>
                <option value="rtsp">IP / RTSP Address</option>
              </select>
            </div>

            <div>
              <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Source Endpoint</label>
              <input
                type="text"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="w-full bg-[#0d0e12] border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40 font-mono"
                placeholder="e.g. 0 or rtsp://..."
                required
              />
            </div>

            <div>
              <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Bind Employee</label>
              <select
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                className="w-full bg-[#0d0e12] border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500/40"
              >
                <option value="">Unassigned</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>{emp.username} ({emp.employee_id})</option>
                ))}
              </select>
            </div>

            <div className="col-span-4 flex justify-end gap-2 border-t border-white/5 pt-4 mt-2">
              <button type="button" onClick={() => setFormOpen(false)} className="hud-btn-secondary text-xs">Disconnect</button>
              <button type="submit" disabled={loading} className="hud-btn-primary text-xs shrink-0">Connect Feed</button>
            </div>
          </form>
        </div>
      )}

      {/* --- CAMERAS MONITOR GRID LIST --- */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {cameras.map((cam) => {
          const camTelemetry = telemetry[cam.id] || {
            is_present: false, looking_at_monitor: false, sleeping: false, phone_detected: false, keyboard_active: false, mouse_active: false, score: 0, fps: 0
          };
          const associatedUser = employees.find(e => e.id === cam.user_id);

          return (
            <div key={cam.id} className="glass-card p-5 border-white/5 flex flex-col gap-4 relative overflow-hidden">
              {/* Badge Overlay */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${
                    cam.status === 'connected' ? 'bg-emerald-400 animate-pulse' : cam.status === 'disconnected' ? 'bg-zinc-500' : 'bg-red-500'
                  }`} />
                  <span className="text-white text-xs font-bold">{cam.name}</span>
                </div>
                
                <span className="text-[10px] text-zinc-400 bg-white/5 py-1 px-2.5 border border-white/5 rounded-full font-mono">
                  {cam.type.toUpperCase()}: {cam.source.length > 25 ? `${cam.source.substring(0,25)}...` : cam.source}
                </span>
              </div>

              {/* Feed & Diagnostics Component */}
              {cam.status === 'connected' ? (
                <WebcamPlayer camera={cam} testingMode={testingMode} />
              ) : (
                <div className="w-full h-48 bg-[#0b0c10] border border-white/5 rounded-xl flex items-center justify-center relative overflow-hidden">
                  <div className="flex flex-col items-center gap-2 text-zinc-600">
                    <Radio size={28} className="text-zinc-700" />
                    <span className="text-[10px] uppercase font-bold tracking-wider">Feed Standby</span>
                  </div>
                </div>
              )}

              {/* Telemetry HUD details */}
              {cam.status === 'connected' && (
                <div className="bg-white/5 border border-white/5 p-4 rounded-xl grid grid-cols-2 gap-3 text-[10px]">
                  <div className="flex items-center justify-between border-b border-white/5 pb-1.5">
                    <span className="text-zinc-500">Focus Score:</span>
                    <span className={`font-bold font-mono ${
                      camTelemetry.score > 75 ? 'text-emerald-400' : camTelemetry.score > 40 ? 'text-amber-400' : 'text-red-400'
                    }`}>
                      {camTelemetry.score}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between border-b border-white/5 pb-1.5">
                    <span className="text-zinc-500">Employee Present:</span>
                    <span className={`font-bold ${camTelemetry.is_present ? 'text-emerald-400' : 'text-red-400'}`}>
                      {camTelemetry.is_present ? 'YES' : 'NO'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between border-b border-white/5 pb-1.5">
                    <span className="text-zinc-500">Attention Gaze:</span>
                    <span className={`font-bold ${camTelemetry.looking_at_monitor ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {camTelemetry.looking_at_monitor ? 'Looking Monitor' : 'Looking Away'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between border-b border-white/5 pb-1.5">
                    <span className="text-zinc-500">Phone usage:</span>
                    <span className={`font-bold ${camTelemetry.phone_detected ? 'text-red-400 animate-pulse' : 'text-emerald-400'}`}>
                      {camTelemetry.phone_detected ? 'Distraction Alert' : 'None'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between col-span-2">
                    <span className="text-zinc-500">Drowsiness state:</span>
                    <span className={`font-bold ${camTelemetry.sleeping ? 'text-red-400 animate-pulse' : 'text-emerald-400'}`}>
                      {camTelemetry.sleeping ? 'Sleeping Alert' : 'Active'}
                    </span>
                  </div>
                </div>
              )}

              {/* Action Buttons panel */}
              <div className="flex justify-between items-center pt-2 border-t border-white/5">
                <div className="space-x-2">
                  {cam.status === 'connected' ? (
                    <button
                      onClick={() => handleToggleConnection(cam, 'disconnect')}
                      className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium text-[10px] px-3.5 py-2 rounded-lg transition-all"
                    >
                      Disconnect Feed
                    </button>
                  ) : (
                    <button
                      onClick={() => handleToggleConnection(cam, 'connect')}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-[10px] px-3.5 py-2 rounded-lg transition-all"
                    >
                      Connect Feed
                    </button>
                  )}
                </div>

                <button
                  onClick={() => handleDelete(cam.id)}
                  className="bg-red-500/10 hover:bg-red-500/20 text-red-400 p-2 rounded-lg border border-red-500/15 transition-all inline-flex"
                  title="Remove Camera config"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          );
        })}
        {cameras.length === 0 && (
          <div className="col-span-2 bg-dark-card border border-dark-border p-16 rounded-2xl text-center text-zinc-500">
            <Radio size={36} className="mx-auto text-zinc-700 mb-3" />
            <p className="text-xs font-semibold">No cameras registered on this network yet.</p>
            <p className="text-[10px] text-zinc-600 mt-1">Click Add Camera to connect a local USB webcam or RTSP network link.</p>
          </div>
        )}
      </div>

      {/* --- CAMERA DIAGNOSTIC TEST MODAL --- */}
      {diagnosticModalOpen && diagnosticResult && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="glass-card w-full max-w-md p-6 border border-indigo-500/20 shadow-2xl relative space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <div className="flex items-center gap-2">
                <Camera size={18} className="text-indigo-400" />
                <h4 className="text-white text-xs font-bold uppercase tracking-wider">Webcam Diagnostic Report</h4>
              </div>
              <button onClick={() => setDiagnosticModalOpen(false)} className="text-zinc-400 hover:text-white">
                <XCircle size={16} />
              </button>
            </div>

            <div className="space-y-2.5 text-xs font-mono">
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/5 border border-white/5">
                <span className="text-zinc-400">Camera detected:</span>
                <span className={`font-bold ${diagnosticResult.detected.startsWith('Yes') ? 'text-emerald-400' : 'text-red-400'}`}>
                  {diagnosticResult.detected}
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/5 border border-white/5">
                <span className="text-zinc-400">Permission:</span>
                <span className={`font-bold ${diagnosticResult.permission === 'Granted' ? 'text-emerald-400' : 'text-red-400'}`}>
                  {diagnosticResult.permission}
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/5 border border-white/5">
                <span className="text-zinc-400">Resolution:</span>
                <span className="text-indigo-300 font-bold">
                  {diagnosticResult.resolution}
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg bg-white/5 border border-white/5">
                <span className="text-zinc-400">Active stream:</span>
                <span className={`font-bold ${diagnosticResult.activeStream.startsWith('Yes') ? 'text-emerald-400' : 'text-red-400'}`}>
                  {diagnosticResult.activeStream}
                </span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setDiagnosticModalOpen(false)}
                className="hud-btn-primary text-xs w-full"
              >
                Close Diagnostic Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
