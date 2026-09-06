import React, { useEffect, useState } from 'react';
import { api, TelegramStatus, AnalysisItem } from '../api/client';
import { 
  ShieldCheck, 
  Send, 
  MessageSquare, 
  AlertTriangle, 
  RefreshCw, 
  Zap, 
  Terminal, 
  Layers,
  ArrowRight
} from 'lucide-react';

interface DashboardProps {
  onNavigate: (tab: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [status, setStatus] = useState<TelegramStatus | null>(null);
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState({
    totalMessages: 0,
    autoReplies: 0,
    blockedActions: 0,
    savedAlerts: 0,
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const [st, msgs, analyses, actions, saved] = await Promise.all([
        api.getStatus(),
        api.getMessages(),
        api.getAnalyses(),
        api.getAuditLogs(),
        api.getSavedMessages(),
      ]);

      setStatus(st);
      setRecentAnalyses(analyses.slice(0, 6));

      const autoRepliesCount = actions.filter(a => a.event_type === 'auto_reply_sent' || a.event_type === 'draft_approved_and_sent').length;
      const blockedCount = actions.filter(a => a.event_type === 'guard_block' || (a.metadata_json && a.metadata_json.decision === 'blocked')).length;

      setMetrics({
        totalMessages: msgs.length,
        autoReplies: autoRepliesCount,
        blockedActions: blockedCount,
        savedAlerts: saved.length,
      });
    } catch (e) {
      console.error("Failed to load dashboard data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleResetCircuitBreaker = async () => {
    await api.resetCircuitBreaker();
    await loadData();
  };

  const handleToggleMode = async () => {
    const nextMode = status?.active_mode === 'simulator' ? 'telethon' : 'simulator';
    await api.switchMode(nextMode);
    await loadData();
  };

  return (
    <div>
      {/* Top Banner / Telegram Health Status */}
      <div className="glass-card" style={{ marginBottom: 24, padding: '20px 24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{
              width: 52,
              height: 52,
              borderRadius: 'var(--radius-md)',
              background: status?.active_mode === 'telethon' ? 'var(--primary-gradient)' : 'var(--accent-purple)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(56, 189, 248, 0.25)',
            }}>
              <Zap size={26} color="#fff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <h2 style={{ fontSize: 20 }}>Live Telegram MTProto</h2>
                <span className={`status-chip ${status?.circuit_breaker.is_tripped ? 'tripped' : (status?.is_connected ? 'online' : 'offline')}`}>
                  <span className="pulse-dot" />
                  {status?.circuit_breaker.is_tripped 
                    ? 'CIRCUIT TRIPPED' 
                    : (status?.is_connected ? 'MTPROTO ОНЛАЙН' : 'MTPROTO ОФФЛАЙН')}
                </span>
              </div>
              <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
                {status?.account 
                  ? `Аккаунт: @${status.account.username || 'user'} (${status.account.first_name || 'Owner'}, ${status.account.telegram_user_id})`
                  : 'Ожидает авторизации сессии Telethon'}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <button 
              id="btn-refresh-data"
              className="btn btn-secondary" 
              onClick={loadData}
              title="Обновить данные дашборда"
            >
              <RefreshCw size={15} />
              Обновить
            </button>
            <button 
              id="btn-open-settings"
              className="btn btn-primary" 
              onClick={() => onNavigate('settings')}
            >
              <Zap size={15} />
              Настройки MTProto
            </button>
          </div>
        </div>

        {/* Circuit Breaker Warning if tripped */}
        {status?.circuit_breaker.is_tripped && (
          <div style={{
            marginTop: 16,
            padding: '12px 16px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--rose-glow)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <AlertTriangle size={20} color="#f87171" />
              <span style={{ fontSize: 13, color: '#fca5a5' }}>
                <strong>Circuit Breaker сработал:</strong> {status.circuit_breaker.reason} (автоответы приостановлены для защиты)
              </span>
            </div>
            <button 
              id="btn-reset-cb"
              className="btn btn-danger" 
              style={{ padding: '4px 12px', fontSize: 12 }}
              onClick={handleResetCircuitBreaker}
            >
              Сбросить предохранитель
            </button>
          </div>
        )}
      </div>

      {/* 4 Stat Cards */}
      <div className="stat-grid">
        <div className="glass-card stat-card">
          <div className="stat-icon" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
            <MessageSquare size={24} />
          </div>
          <div>
            <div className="stat-val">{metrics.totalMessages}</div>
            <div className="stat-lbl">Обработано сообщений</div>
          </div>
        </div>

        <div className="glass-card stat-card">
          <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
            <Send size={24} />
          </div>
          <div>
            <div className="stat-val">{metrics.autoReplies}</div>
            <div className="stat-lbl">Отправлено автоответов</div>
          </div>
        </div>

        <div className="glass-card stat-card">
          <div className="stat-icon" style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>
            <ShieldCheck size={24} />
          </div>
          <div>
            <div className="stat-val">{metrics.blockedActions}</div>
            <div className="stat-lbl">Заблокировано Response Guard</div>
          </div>
        </div>

        <div className="glass-card stat-card">
          <div className="stat-icon" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#a855f7' }}>
            <Layers size={24} />
          </div>
          <div>
            <div className="stat-val">{metrics.savedAlerts}</div>
            <div className="stat-lbl">Саммари в «Избранное»</div>
          </div>
        </div>
      </div>

      {/* Recent High Importance Events Feed */}
      <div className="glass-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <div>
            <h3 style={{ fontSize: 18 }}>Последние важные события и AI-анализ</h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
              События, классифицированные AI-модулем в режиме реального времени
            </p>
          </div>
          <button 
            id="btn-view-all-analyses"
            className="btn btn-secondary" 
            style={{ fontSize: 13 }}
            onClick={() => onNavigate('simulator')}
          >
            Тестировать события
            <ArrowRight size={14} />
          </button>
        </div>

        {recentAnalyses.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
            <p>Нет входящих сообщений. Ассистент ожидает новые сообщения в подключенном аккаунте Telegram.</p>
            <button 
              id="btn-empty-go-settings"
              className="btn btn-primary" 
              style={{ marginTop: 16 }}
              onClick={() => onNavigate('settings')}
            >
              Настройки подключения
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {recentAnalyses.map(a => (
              <div 
                key={a.id} 
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '14px 18px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 16,
                  transition: 'background 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div style={{
                    width: 38,
                    height: 38,
                    borderRadius: '50%',
                    background: a.importance >= 8 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                    color: a.importance >= 8 ? '#f87171' : '#38bdf8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 700,
                    fontSize: 14,
                  }}>
                    {a.importance}
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: 600, fontSize: 14, color: '#fff' }}>{a.sender_name}</span>
                      <span className={`badge ${a.intent === 'task' ? 'badge-purple' : (a.intent === 'urgent' ? 'badge-rose' : 'badge-blue')}`}>
                        {a.intent.toUpperCase()}
                      </span>
                      {a.needs_reply && <span className="badge badge-amber">Нужен ответ</span>}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 3 }}>
                      {a.summary}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                  {a.topics.map((t, idx) => (
                    <span key={idx} className="badge badge-emerald" style={{ fontSize: 10 }}>
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
