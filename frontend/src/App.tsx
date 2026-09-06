import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  Users, 
  Sliders, 
  Cpu, 
  CheckSquare, 
  Bookmark, 
  Terminal, 
  Settings as SettingsIcon,
  Zap,
  ShieldCheck
} from 'lucide-react';
import { api, TelegramStatus } from './api/client';
import { Dashboard } from './pages/Dashboard';
import { ContactsPage } from './pages/ContactsPage';
import { RulesPage } from './pages/RulesPage';
import { ApprovalQueuePage } from './pages/ApprovalQueuePage';
import { SavedMessagesPage } from './pages/SavedMessagesPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [status, setStatus] = useState<TelegramStatus | null>(null);
  const [pendingDraftsCount, setPendingDraftsCount] = useState<number>(0);

  const pollStatus = async () => {
    try {
      const [st, drafts] = await Promise.all([
        api.getStatus(),
        api.getPendingActions(),
      ]);
      setStatus(st);
      setPendingDraftsCount(drafts.length);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    pollStatus();
    const interval = setInterval(pollStatus, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-layout">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon-wrapper">
            <Zap size={22} color="#fff" />
          </div>
          <div className="logo-text">
            <h1>Telegram AI</h1>
            <span>Personal Assistant</span>
          </div>
        </div>

        <ul className="nav-list">
          <li>
            <button
              id="nav-dashboard"
              className={`nav-item-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              <LayoutDashboard size={18} />
              Дашборд
            </button>
          </li>
          <li>
            <button
              id="nav-contacts"
              className={`nav-item-btn ${activeTab === 'contacts' ? 'active' : ''}`}
              onClick={() => setActiveTab('contacts')}
            >
              <Users size={18} />
              Люди и категории
            </button>
          </li>
          <li>
            <button
              id="nav-rules"
              className={`nav-item-btn ${activeTab === 'rules' ? 'active' : ''}`}
              onClick={() => setActiveTab('rules')}
            >
              <Sliders size={18} />
              Правила
            </button>
          </li>
          <li>
            <button
              id="nav-approvals"
              className={`nav-item-btn ${activeTab === 'approvals' ? 'active' : ''}`}
              onClick={() => setActiveTab('approvals')}
            >
              <CheckSquare size={18} />
              Черновики
              {pendingDraftsCount > 0 && (
                <span className="nav-badge">{pendingDraftsCount}</span>
              )}
            </button>
          </li>
          <li>
            <button
              id="nav-saved"
              className={`nav-item-btn ${activeTab === 'saved' ? 'active' : ''}`}
              onClick={() => setActiveTab('saved')}
            >
              <Bookmark size={18} />
              «Избранное»
            </button>
          </li>
        </ul>

        <div className="sidebar-footer">
          <button
            id="nav-settings"
            className={`nav-item-btn ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            <SettingsIcon size={18} />
            Настройки & MTProto
          </button>
        </div>
      </aside>

      {/* Main Area */}
      <div className="main-wrapper">
        <header className="topbar">
          <div className="topbar-title-section">
            <h2 style={{ fontSize: 18, color: '#fff' }}>
              {activeTab === 'dashboard' && 'Обзор системы'}
              {activeTab === 'contacts' && 'Контакты, категории и персонализированные промпты'}
              {activeTab === 'rules' && 'Политики и правила автоответов'}
              {activeTab === 'approvals' && 'Очередь подтверждения черновиков'}
              {activeTab === 'saved' && 'Дайджесты и алерты в «Избранное»'}
              {activeTab === 'settings' && 'Настройки MTProto & Безопасность'}
            </h2>
          </div>

          <div className="topbar-actions">
            {status && (
              <span className={`status-chip ${status.circuit_breaker.is_tripped ? 'tripped' : (status.is_connected ? 'online' : 'offline')}`}>
                <span className="pulse-dot" />
                {status.circuit_breaker.is_tripped 
                  ? 'CIRCUIT TRIPPED' 
                  : (status.is_connected ? 'MTPROTO ONLINE' : 'MTPROTO OFFLINE')}
              </span>
            )}
          </div>
        </header>

        <main className="page-container">
          {activeTab === 'dashboard' && <Dashboard onNavigate={setActiveTab} />}
          {activeTab === 'contacts' && <ContactsPage />}
          {activeTab === 'rules' && <RulesPage />}
          {activeTab === 'approvals' && <ApprovalQueuePage />}
          {activeTab === 'saved' && <SavedMessagesPage />}
          {activeTab === 'settings' && <SettingsPage onNavigate={setActiveTab} />}
        </main>
      </div>
    </div>
  );
};
export default App;
