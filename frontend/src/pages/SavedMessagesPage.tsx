import React, { useEffect, useState } from 'react';
import { api, SavedMessageItem, TaskItem } from '../api/client';
import { Bookmark, Sparkles, CheckSquare, Square, RefreshCw, Send } from 'lucide-react';

export const SavedMessagesPage: React.FC = () => {
  const [savedMessages, setSavedMessages] = useState<SavedMessageItem[]>([]);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);

  const loadData = async () => {
    try {
      const [sm, t] = await Promise.all([
        api.getSavedMessages(),
        api.getTasks(),
      ]);
      setSavedMessages(sm);
      setTasks(t);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleGenerateDigest = async () => {
    try {
      setIsGenerating(true);
      await api.runSummary("Внеплановый сводный дайджест");
      await loadData();
    } finally {
      setIsGenerating(false);
    }
  };

  const handleToggleTask = async (taskId: number) => {
    await api.toggleTask(taskId);
    await loadData();
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24 }}>
      {/* Left: Stream of Saved Messages */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <div>
            <h2 style={{ fontSize: 22 }}>«Избранное» (Saved Messages)</h2>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              Лента срочных алертов и периодических дайджестов, отправляемых в личное «Избранное» Telegram
            </p>
          </div>
          <button 
            id="btn-trigger-digest"
            className="btn btn-primary"
            onClick={handleGenerateDigest}
            disabled={isGenerating}
          >
            <Sparkles size={16} />
            {isGenerating ? 'Формирование...' : 'Сформировать дайджест сейчас'}
          </button>
        </div>

        {savedMessages.length === 0 ? (
          <div className="glass-card" style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
            <Bookmark size={48} style={{ opacity: 0.3, margin: '0 auto 16px auto', display: 'block' }} />
            <h3 style={{ fontSize: 18, color: '#fff', marginBottom: 6 }}>«Избранное» пока пусто</h3>
            <p style={{ fontSize: 14 }}>
              Нажмите «Сформировать дайджест сейчас» или отправьте срочное сообщение в песочнице.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {savedMessages.map(item => (
              <div 
                key={item.id} 
                className="glass-card" 
                style={{
                  background: 'rgba(20, 26, 40, 0.9)',
                  borderLeft: item.text.includes('🚨') ? '4px solid #ef4444' : '4px solid var(--primary-glow)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Bookmark size={16} color="var(--primary-glow)" />
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>Сообщение в Избранное</span>
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                    {new Date(item.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <pre style={{
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'inherit',
                  fontSize: 13,
                  lineHeight: 1.6,
                  color: 'var(--text-main)',
                }}>
                  {item.text}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right: Open Tasks checklist */}
      <div>
        <div className="glass-card" style={{ position: 'sticky', top: 90 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16 }}>Открытые задачи</h3>
            <span className="badge badge-amber">{tasks.filter(t => t.status === 'open').length}</span>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
            Задачи автоматически извлекаются AI из входящей переписки
          </p>

          {tasks.length === 0 ? (
            <p style={{ fontSize: 12, color: 'var(--text-dim)' }}>Задач пока нет.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {tasks.map(t => (
                <div 
                  key={t.id}
                  onClick={() => handleToggleTask(t.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 10,
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-sm)',
                    background: t.status === 'done' ? 'rgba(255,255,255,0.02)' : 'rgba(245, 158, 11, 0.08)',
                    cursor: 'pointer',
                    transition: 'background 0.2s ease',
                  }}
                >
                  {t.status === 'done' ? (
                    <CheckSquare size={16} color="var(--emerald)" style={{ marginTop: 2, flexShrink: 0 }} />
                  ) : (
                    <Square size={16} color="var(--amber)" style={{ marginTop: 2, flexShrink: 0 }} />
                  )}
                  <span style={{
                    fontSize: 12,
                    textDecoration: t.status === 'done' ? 'line-through' : 'none',
                    color: t.status === 'done' ? 'var(--text-dim)' : 'var(--text-main)',
                  }}>
                    {t.title}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
