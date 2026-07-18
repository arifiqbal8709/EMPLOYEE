import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import EmployeeManagement from './pages/EmployeeManagement';
import CameraManagement from './pages/CameraManagement';
import SettingsPage from './pages/Settings';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(true);
  const [view, setView] = useState('dashboard');

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = () => {
    if (!localStorage.getItem("role")) {
      localStorage.setItem("role", "manager");
    }
    if (!localStorage.getItem("username")) {
      localStorage.setItem("username", "manager_user");
    }
    setIsAuthenticated(true);
  };

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

  return (
    <div className="min-h-screen relative flex">
      {/* Side Navigation HUD panel */}
      <Sidebar currentView={view} setView={setView} onLogout={checkAuth} />

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
