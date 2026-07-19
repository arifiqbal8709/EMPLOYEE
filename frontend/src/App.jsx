import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import EmployeeManagement from './pages/EmployeeManagement';
import CameraManagement from './pages/CameraManagement';
import SettingsPage from './pages/Settings';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Loader } from 'lucide-react';

function MainLayout() {
  const { isAuthenticated, loading } = useAuth();
  const [view, setView] = useState('dashboard');

  const getViewTitle = (currentView) => {
    switch (currentView) {
      case 'dashboard':
        return 'EXECUTIVE ANALYTICS OVERVIEW';
      case 'employees':
        return 'EMPLOYEE MANAGEMENT CONSOLE';
      case 'cameras':
        return 'ACTIVE CAMERA LIVESTREAMS HUB';
      case 'settings':
        return 'SYSTEM NOTIFICATIONS & LIMITS CONFIGURATION';
      default:
        return 'AI EMPLOYEE MONITORING CONSOLE';
    }
  };

  const renderContent = () => {
    switch (view) {
      case 'dashboard':
        return <Dashboard />;
      case 'employees':
        return <EmployeeManagement />;
      case 'cameras':
        return <CameraManagement />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <Dashboard />;
    }
  };

  // Full-screen loading state during initial session verification
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#030407] text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader size={32} className="animate-spin text-indigo-500" />
          <p className="text-xs text-zinc-400 font-mono tracking-wider uppercase">Verifying Security Session...</p>
        </div>
      </div>
    );
  }

  // Protected route guard: render Login component if unauthenticated
  if (!isAuthenticated) {
    return <Login />;
  }

  return (
    <div className="min-h-screen relative flex">
      {/* Side Navigation HUD panel */}
      <Sidebar currentView={view} setView={setView} />

      {/* Main viewport area */}
      <div className="flex-1 ml-64 min-h-screen flex flex-col relative">
        <Navbar title={getViewTitle(view)} />
        
        {/* Dynamic Inner page container */}
        <main className="flex-grow pt-28 px-8 pb-8 relative overflow-y-auto">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainLayout />
    </AuthProvider>
  );
}
