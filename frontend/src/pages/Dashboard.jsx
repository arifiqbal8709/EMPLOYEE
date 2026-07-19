import React, { useState, useEffect } from 'react';
import { Users, TrendingUp, Camera, AlertTriangle, FileSpreadsheet, Download, RefreshCw, X, Video, Activity, Radio } from 'lucide-react';
import { api } from '../utils/api';

export default function Dashboard() {
  const [employees, setEmployees] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);

  // Webcam state variables
  const [webcamActive, setWebcamActive] = useState(false);
  const [webcamStatus, setWebcamStatus] = useState({
    status: "stopped",
    camera_status: "Inactive",
    person_detected: "No",
    phone_detected: "No",
    laptop_detected: "No",
    chair_detected: "No",
    confidence: "0%",
    fps: 0
  });
  const [streamHash, setStreamHash] = useState(Date.now());

  useEffect(() => {
    let timer;
    const fetchWebcamStatus = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/camera/status");
        if (res.ok) {
          const data = await res.json();
          setWebcamStatus(data);
          setWebcamActive(data.status === "running");
        }
      } catch (err) {
        console.error("Error fetching webcam status:", err);
      }
    };

    fetchWebcamStatus();
    timer = setInterval(fetchWebcamStatus, 1200);
    return () => clearInterval(timer);
  }, []);

  const handleStartWebcam = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/camera/start", { method: "POST" });
      if (res.ok) {
        setWebcamActive(true);
        setStreamHash(Date.now());
      }
    } catch (err) {
      console.error("Error starting camera:", err);
    }
  };

  const handleStopWebcam = async () => {
    try {
      await fetch("http://localhost:8000/api/camera/stop", { method: "POST" });
      setWebcamActive(false);
    } catch (err) {
      console.error("Error stopping camera:", err);
    }
  };

  // Periodicity settings
  const [reportPeriod, setReportPeriod] = useState('daily'); // 'daily', 'weekly', 'monthly'

  // Exporter modal parameters
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [startDate, setStartDate] = useState(new Date(Date.now() - 7 * 24 * 3600 * 1000).toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [selectedEmpId, setSelectedEmpId] = useState('');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const empData = await api.employees.list();
      setEmployees(empData);

      const camData = await api.cameras.list();
      setCameras(camData);

      const alertData = await api.notifications.listAlerts();
      setAlerts(alertData);
    } catch (err) {
      console.error("Error loading dashboard data", err);
    } finally {
      setLoading(false);
    }
  };

  // 1. Gather stats
  const activeCount = employees.filter(e => e.status === 'active').length;
  const idleCount = employees.filter(e => e.status === 'idle').length;
  const totalEmployees = employees.length;
  const liveCount = activeCount + idleCount;
  
  // Calculate mockup focus averages
  const avgFocus = totalEmployees > 0 
    ? Math.round(employees.reduce((acc, curr) => acc + (curr.status === 'active' ? 88 : curr.status === 'idle' ? 42 : 0), 0) / totalEmployees)
    : 0;

  const connectedCamsCount = cameras.filter(c => c.status === 'connected').length;

  // 2. Mock aggregate reports depending on Daily / Weekly / Monthly toggles
  const reportData = {
    daily: [
      { label: "09:00 AM", score: 85, workMins: 55, idleMins: 5 },
      { label: "11:00 AM", score: 92, workMins: 58, idleMins: 2 },
      { label: "01:00 PM", score: 45, workMins: 20, idleMins: 40 }, // Lunch break
      { label: "03:00 PM", score: 78, workMins: 48, idleMins: 12 },
      { label: "05:00 PM", score: 86, workMins: 52, idleMins: 8 }
    ],
    weekly: [
      { label: "Monday", score: 82, workMins: 450, idleMins: 30 },
      { label: "Tuesday", score: 89, workMins: 462, idleMins: 18 },
      { label: "Wednesday", score: 84, workMins: 445, idleMins: 35 },
      { label: "Thursday", score: 78, workMins: 430, idleMins: 50 },
      { label: "Friday", score: 91, workMins: 470, idleMins: 10 }
    ],
    monthly: [
      { label: "Week 1", score: 86, workMins: 2200, idleMins: 200 },
      { label: "Week 2", score: 80, workMins: 2150, idleMins: 250 },
      { label: "Week 3", score: 88, workMins: 2310, idleMins: 90 },
      { label: "Week 4", score: 83, workMins: 2190, idleMins: 210 }
    ]
  };

  const activeReports = reportData[reportPeriod];

  // 3. Employee Ranking
  const rankedEmployees = [...employees].map(emp => {
    let focusValue = 0;
    if (emp.status === 'active') focusValue = 85 + (emp.id % 3) * 5;
    else if (emp.status === 'idle') focusValue = 35 + (emp.id % 3) * 5;
    return { ...emp, score: focusValue };
  }).sort((a, b) => b.score - a.score);

  const getRankColor = (index) => {
    if (index === 0) return "text-amber-400 font-bold"; // Gold
    if (index === 1) return "text-zinc-400 font-bold"; // Silver
    if (index === 2) return "text-amber-600 font-bold"; // Bronze
    return "text-zinc-500";
  };

  const handleExportPDF = () => {
    const url = api.employees.getPdfUrl(startDate, endDate, selectedEmpId);
    window.open(url, "_blank");
  };

  const handleExportExcel = () => {
    const url = api.employees.getExcelUrl(startDate, endDate, selectedEmpId);
    window.open(url, "_blank");
  };

  return (
    <div className="space-y-6">
      {/* KPI METRICS OVERVIEW */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Metric 1: Live Staff */}
        <div className="glass-card p-5 border-white/5 flex items-center gap-4 relative overflow-hidden">
          <div className="absolute top-0 right-0 h-16 w-16 bg-indigo-500/5 rounded-full blur-[20px] pointer-events-none" />
          <div className="bg-indigo-600/15 text-indigo-400 p-3 rounded-xl border border-indigo-500/10 shadow-lg shrink-0">
            <Users size={20} />
          </div>
          <div>
            <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Live Employees</p>
            <h3 className="text-white text-xl font-bold mt-1">{liveCount} <span className="text-zinc-500 text-xs font-semibold">/ {totalEmployees}</span></h3>
            <p className="text-[9px] text-emerald-400 font-medium mt-0.5">{activeCount} actively online</p>
          </div>
        </div>

        {/* Metric 2: Average Score */}
        <div className="glass-card p-5 border-white/5 flex items-center gap-4 relative overflow-hidden">
          <div className="absolute top-0 right-0 h-16 w-16 bg-emerald-500/5 rounded-full blur-[20px] pointer-events-none" />
          <div className="bg-emerald-600/15 text-emerald-400 p-3 rounded-xl border border-emerald-500/10 shadow-lg shrink-0">
            <TrendingUp size={20} />
          </div>
          <div>
            <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Productivity Score</p>
            <h3 className="text-white text-xl font-bold mt-1">{avgFocus}%</h3>
            <p className="text-[9px] text-emerald-400 font-medium mt-0.5">Focus average levels</p>
          </div>
        </div>

        {/* Metric 3: Active Cameras */}
        <div className="glass-card p-5 border-white/5 flex items-center gap-4 relative overflow-hidden">
          <div className="absolute top-0 right-0 h-16 w-16 bg-purple-500/5 rounded-full blur-[20px] pointer-events-none" />
          <div className="bg-purple-600/15 text-purple-400 p-3 rounded-xl border border-purple-500/10 shadow-lg shrink-0">
            <Camera size={20} />
          </div>
          <div>
            <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Active Cameras</p>
            <h3 className="text-white text-xl font-bold mt-1">{connectedCamsCount} <span className="text-zinc-500 text-xs font-semibold">/ {cameras.length}</span></h3>
            <p className="text-[9px] text-purple-400 font-medium mt-0.5">Capture links active</p>
          </div>
        </div>

        {/* Metric 4: Alert count */}
        <div className="glass-card p-5 border-white/5 flex items-center gap-4 relative overflow-hidden">
          <div className="absolute top-0 right-0 h-16 w-16 bg-red-500/5 rounded-full blur-[20px] pointer-events-none" />
          <div className="bg-red-600/15 text-red-500 p-3 rounded-xl border border-red-500/10 shadow-lg shrink-0">
            <AlertTriangle size={20} className={alerts.length > 0 ? "animate-bounce" : ""} />
          </div>
          <div>
            <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Alert Violations</p>
            <h3 className="text-white text-xl font-bold mt-1">{alerts.length}</h3>
            <p className="text-[9px] text-rose-500 font-medium mt-0.5">Unresolved infractions</p>
          </div>
        </div>
      </div>

      {/* REACTION CONTROL UTILITY BAR */}
      <div className="flex justify-between items-center bg-white/5 border border-white/5 rounded-2xl px-6 py-4">
        <h4 className="text-white text-xs font-bold uppercase tracking-wider">Productivity Console</h4>
        
        <div className="flex items-center gap-3">
          <button onClick={fetchDashboardData} className="bg-white/5 hover:bg-white/10 border border-white/10 p-2.5 rounded-xl text-zinc-400 hover:text-white transition-all">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
          
          <button
            onClick={() => setExportModalOpen(true)}
            className="hud-btn-primary text-xs shrink-0 flex items-center gap-2"
          >
            <FileSpreadsheet size={14} />
            <span>Generate Reports</span>
          </button>
        </div>
      </div>

      {/* LIVE AI WEBCAM MONITOR PANEL */}
      <div className="glass-card p-6 border-white/5 space-y-4">
        <div className="flex items-center justify-between border-b border-white/5 pb-4">
          <div className="flex items-center gap-2.5">
            <Radio size={16} className={`text-indigo-400 ${webcamActive ? 'animate-pulse' : ''}`} />
            <h4 className="text-white text-xs font-bold uppercase tracking-wider">Live AI Webcam Monitor</h4>
          </div>

          <div className="flex items-center gap-2">
            {!webcamActive ? (
              <button
                onClick={handleStartWebcam}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-[10px] px-3.5 py-1.5 rounded-lg transition-all flex items-center gap-1.5"
              >
                <span>Start Camera</span>
              </button>
            ) : (
              <button
                onClick={handleStopWebcam}
                className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium text-[10px] px-3.5 py-1.5 rounded-lg transition-all flex items-center gap-1.5"
              >
                <span>Stop Camera</span>
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Live stream preview frame */}
          <div className="md:col-span-2 w-full h-80 bg-[#0b0c10] border border-white/5 rounded-xl flex items-center justify-center relative overflow-hidden">
            {webcamActive && webcamStatus.status === "running" ? (
              <img
                src={`http://localhost:8000/api/camera/stream?t=${streamHash}`}
                className="w-full h-full object-cover"
                alt="Live Webcam Feed"
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            ) : webcamStatus.status === "no_device_error" ? (
              <div className="flex flex-col items-center gap-2 text-red-500">
                <AlertTriangle size={32} className="text-red-500" />
                <span className="text-xs uppercase font-bold tracking-wider">No Webcam Device Found</span>
                <span className="text-[10px] text-zinc-500">Please connect a camera or verify system permission settings</span>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2 text-zinc-600">
                <Camera size={32} className="text-zinc-700" />
                <span className="text-[10px] uppercase font-bold tracking-wider">Webcam Standby</span>
                <span className="text-[9px] text-zinc-700">Click Start Camera to initialize YOLOv11 engine</span>
              </div>
            )}

            {/* Live FPS metric overlay */}
            {webcamActive && webcamStatus.status === "running" && (
              <div className="absolute top-3 right-3 bg-indigo-600/90 text-white font-mono text-[9px] font-bold px-2 py-0.5 rounded border border-indigo-400/20 shadow-lg">
                FPS: {webcamStatus.fps}
              </div>
            )}
          </div>

          {/* Side panel metrics indicator */}
          <div className="bg-white/5 border border-white/5 p-5 rounded-xl flex flex-col justify-between text-xs space-y-4">
            <div>
              <h5 className="text-white text-[10px] font-bold uppercase tracking-wider border-b border-white/5 pb-2 mb-3 flex items-center gap-1.5 flex-row">
                <Activity size={12} className="text-indigo-400" />
                <span>Detection Control Panel</span>
              </h5>
              
              <div className="space-y-3 font-medium text-[11px]">
                <div className="flex items-center justify-between border-b border-white/5 pb-2 flex-row">
                  <span className="text-zinc-400">Camera Status</span>
                  <div className="flex items-center gap-1.5 flex-row">
                    <span className={`h-2 w-2 rounded-full ${
                      webcamStatus.status === "running" ? "bg-emerald-400 animate-pulse" :
                      webcamStatus.status === "no_device_error" ? "bg-rose-500" : "bg-zinc-500"
                    }`} />
                    <span className={`font-bold ${
                      webcamStatus.status === "running" ? "text-emerald-400" :
                      webcamStatus.status === "no_device_error" ? "text-rose-400" : "text-zinc-400"
                    }`}>
                      {webcamStatus.camera_status}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between border-b border-white/5 pb-2 flex-row">
                  <span className="text-zinc-400">Person Detected</span>
                  <span className={`font-bold px-2 py-0.5 rounded ${
                    webcamStatus.person_detected === "Yes" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/10" : "bg-zinc-800 text-zinc-400"
                  }`}>
                    {webcamStatus.person_detected}
                  </span>
                </div>

                <div className="flex items-center justify-between border-b border-white/5 pb-2 flex-row">
                  <span className="text-zinc-400">Phone Detected</span>
                  <span className={`font-bold px-2 py-0.5 rounded ${
                    webcamStatus.phone_detected === "Yes" ? "bg-rose-500/10 text-rose-400 border border-rose-500/10" : "bg-zinc-800 text-zinc-400"
                  }`}>
                    {webcamStatus.phone_detected}
                  </span>
                </div>

                <div className="flex items-center justify-between border-b border-white/5 pb-2 flex-row">
                  <span className="text-zinc-400">Laptop Detected</span>
                  <span className={`font-bold px-2 py-0.5 rounded ${
                    webcamStatus.laptop_detected === "Yes" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/10" : "bg-zinc-800 text-zinc-400"
                  }`}>
                    {webcamStatus.laptop_detected}
                  </span>
                </div>

                <div className="flex items-center justify-between border-b border-white/5 pb-2 flex-row">
                  <span className="text-zinc-400">Chair Detected</span>
                  <span className={`font-bold px-2 py-0.5 rounded ${
                    webcamStatus.chair_detected === "Yes" ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/10" : "bg-zinc-800 text-zinc-400"
                  }`}>
                    {webcamStatus.chair_detected}
                  </span>
                </div>

                <div className="flex items-center justify-between pt-1 flex-row">
                  <span className="text-zinc-400">Detection Confidence</span>
                  <span className="font-bold font-mono text-indigo-400 text-xs">
                    {webcamStatus.confidence}
                  </span>
                </div>
              </div>
            </div>

            <div className="text-[9px] text-zinc-500 bg-[#0d0e12] p-2.5 rounded-lg border border-white/5">
              💡 YOLOv11 extracts detections real-time. Objects detected are automatically synchronized to the local database.
            </div>
          </div>
        </div>
      </div>

      {/* CORE WORKSPACE GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN: CUSTOM GRAPHICS AND REPORTING */}
        <div className="lg:col-span-2 space-y-6">
          {/* Productivity Reports Chart Card */}
          <div className="glass-card p-6 border-white/5">
            <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-6">
              <h4 className="text-white text-xs font-bold uppercase tracking-wider">Focus Hour Trends</h4>
              
              {/* Period selectors tabs */}
              <div className="flex bg-white/5 border border-white/5 rounded-lg p-1 text-[10px]">
                {['daily', 'weekly', 'monthly'].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setReportPeriod(tab)}
                    className={`px-3 py-1.5 rounded-md font-semibold uppercase tracking-wider transition-all ${
                      reportPeriod === tab ? 'bg-indigo-600 text-white shadow' : 'text-zinc-400 hover:text-white'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom Responsive Progress Bar Graphic Chart (Clean Compile, styled via Tailwind) */}
            <div className="space-y-5">
              {activeReports.map((item, idx) => (
                <div key={idx} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-zinc-300">{item.label}</span>
                    <div className="space-x-3 text-[10px]">
                      <span className="text-indigo-400">Score: {item.score}%</span>
                      <span className="text-zinc-500">
                        Work: {item.workMins >= 60 ? `${(item.workMins/60).toFixed(1)}h` : `${item.workMins}m`}
                      </span>
                      <span className="text-red-500/70">
                        Idle: {item.idleMins >= 60 ? `${(item.idleMins/60).toFixed(1)}h` : `${item.idleMins}m`}
                      </span>
                    </div>
                  </div>
                  {/* Chart Progress bars track */}
                  <div className="w-full h-2.5 bg-white/5 rounded-full overflow-hidden flex">
                    <div 
                      style={{ width: `${item.score}%` }} 
                      className="bg-gradient-to-r from-indigo-500 to-indigo-600 h-full transition-all duration-500 ease-out" 
                    />
                    <div 
                      style={{ width: `${100 - item.score}%` }} 
                      className="bg-red-500/20 h-full" 
                    />
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-8 flex justify-end gap-5 text-[10px] text-zinc-500 font-medium">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded bg-indigo-500" />
                <span>Productivity Index</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded bg-red-500/20" />
                <span>Idle / Disengaged Range</span>
              </div>
            </div>
          </div>

          {/* Employee Performance Rankings Card */}
          <div className="glass-card p-6 border-white/5">
            <h4 className="text-white text-xs font-bold uppercase tracking-wider border-b border-white/5 pb-4 mb-4">Focus Lead Ranking</h4>
            
            <div className="divide-y divide-white/5">
              {rankedEmployees.slice(0, 5).map((emp, index) => (
                <div key={emp.id} className="flex items-center justify-between py-3">
                  <div className="flex items-center gap-4">
                    <span className={`w-5 font-mono text-center text-xs ${getRankColor(index)}`}>
                      {index + 1}
                    </span>
                    <div>
                      <h5 className="text-white text-xs font-bold">{emp.username}</h5>
                      <p className="text-[10px] text-zinc-500 mt-0.5">{emp.department || 'UI Design Operations'}</p>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="font-mono text-xs font-bold text-indigo-400">Score: {emp.score}%</div>
                    {/* Status Badge */}
                    <span className={`inline-block text-[8px] font-bold uppercase px-2 py-0.5 rounded-full mt-1 ${
                      emp.status === 'active' 
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/5' 
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/5'
                    }`}>
                      {emp.status}
                    </span>
                  </div>
                </div>
              ))}
              {rankedEmployees.length === 0 && (
                <div className="text-center py-6 text-zinc-500 text-xs">No employees profiles registered yet.</div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: ALERTS NOTIFICATIONS LOGS */}
        <div className="glass-card p-6 border-white/5 h-[585px] overflow-hidden flex flex-col">
          <h4 className="text-white text-xs font-bold uppercase tracking-wider border-b border-white/5 pb-4 mb-4 shrink-0">Inbound Alerts Feed</h4>
          
          <div className="flex-1 overflow-y-auto space-y-4 pr-1">
            {alerts.slice(0, 10).map((alert) => (
              <div 
                key={alert.id} 
                className={`p-3.5 border rounded-xl animate-slideLeft flex flex-col gap-1.5 ${
                  alert.type === 'phone'
                    ? 'bg-rose-500/10 border-rose-500/15'
                    : alert.type === 'idle'
                    ? 'bg-amber-500/10 border-amber-500/15'
                    : 'bg-zinc-800/25 border-zinc-700/20'
                }`}
              >
                <div className="flex justify-between items-start">
                  <h5 className={`text-xs font-bold uppercase tracking-tight ${
                    alert.type === 'phone' ? 'text-rose-400' : 'text-amber-400'
                  }`}>
                    {alert.title}
                  </h5>
                  <span className="text-[9px] text-zinc-500 font-mono">
                    {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                
                <p className="text-zinc-300 text-[10px] leading-relaxed">{alert.message}</p>
                
                <div className="flex justify-between items-center text-[9px] text-zinc-500 font-semibold border-t border-white/5 pt-1.5 mt-0.5">
                  <span className="uppercase">Channel: {alert.channel}</span>
                  <span className="bg-white/5 py-0.5 px-2 rounded tracking-wider uppercase">{alert.type}</span>
                </div>
              </div>
            ))}
            {alerts.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center text-zinc-600 gap-2 mt-20">
                <AlertTriangle size={24} className="text-zinc-800" />
                <span className="text-xs font-semibold">Feed stands clean.</span>
                <span className="text-[10px] text-zinc-700">No alert infractions registered today.</span>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* --- EXPORT MODAL PANEL --- */}
      {exportModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-card w-full max-w-md p-6 border-white/5 animate-scaleUp">
            <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-5">
              <h3 className="text-white text-base font-bold flex items-center gap-2">
                <FileSpreadsheet size={18} className="text-indigo-400" />
                <span>Export Executive Productivity Reports</span>
              </h3>
              <button onClick={() => setExportModalOpen(false)} className="text-zinc-500 hover:text-white transition-all">
                <X size={18} />
              </button>
            </div>
            
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full bg-[#0d0e12] border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40"
                    required
                  />
                </div>
                <div>
                  <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full bg-[#0d0e12] border border-white/5 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500/40"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-zinc-400 text-[10px] font-bold uppercase tracking-wider mb-2">Filter Employee</label>
                <select
                  value={selectedEmpId}
                  onChange={(e) => setSelectedEmpId(e.target.value)}
                  className="w-full bg-[#0d0e12] border border-white/5 rounded-xl px-4 py-2.5 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500/40"
                >
                  <option value="">All Staff Profiles</option>
                  {employees.map((emp) => (
                    <option key={emp.id} value={emp.id}>{emp.username} ({emp.employee_id})</option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-2 pt-4 border-t border-white/5 mt-5">
                <button
                  type="button"
                  onClick={handleExportPDF}
                  className="hud-btn-primary hover:bg-indigo-700 bg-indigo-600 text-white font-medium py-3 rounded-xl transition-all duration-200 active:scale-[0.98] shadow-lg flex items-center justify-center gap-2"
                >
                  <Download size={14} />
                  <span>Download PDF Document Summary</span>
                </button>
                
                <button
                  type="button"
                  onClick={handleExportExcel}
                  className="hud-btn-secondary border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10 font-medium py-3 rounded-xl transition-all duration-200 active:scale-[0.98]"
                >
                  <span>Download Excel Spreadsheet Sheet</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
