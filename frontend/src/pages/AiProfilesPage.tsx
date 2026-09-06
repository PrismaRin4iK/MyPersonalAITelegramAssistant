import React, { useEffect, useState } from 'react';
import { api, AiProfileItem } from '../api/client';
import { Cpu, Plus, Check, ShieldCheck } from 'lucide-react';

export const AiProfilesPage: React.FC = () => {
  const [profiles, setProfiles] = useState<AiProfileItem[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProfile, setNewProfile] = useState({
    name: '',
    description: '',
    system_policy: '',
    style: 'friendly',
    max_tokens: 200,
    forbidden_topics_str: 'пароли, ключи, финансы',
  });

  const loadProfiles = async () => {
    try {
      const data = await api.getProfiles();
      setProfiles(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadProfiles();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProfile.name) return;

    const topics = newProfile.forbidden_topics_str
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);

    await api.createProfile({
      name: newProfile.name,
      description: newProfile.description,
      system_policy: newProfile.system_policy,
      style: newProfile.style,
      max_tokens: Number(newProfile.max_tokens),
      forbidden_topics: topics,
      allowed_actions: ['draft', 'summary'],
      is_default: false,
    });

    setIsModalOpen(false);
    setNewProfile({
      name: '',
      description: '',
      system_policy: '',
      style: 'friendly',
      max_tokens: 200,
      forbidden_topics_str: 'пароли, ключи, финансы',
    });
    await loadProfiles();
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h2 style={{ fontSize: 22 }}>AI Профили общения</h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Стили коммуникации, системные политики и запрещенные темы для разных контекстов
          </p>
        </div>
        <button 
          id="btn-create-profile"
          className="btn btn-primary"
          onClick={() => setIsModalOpen(true)}
        >
          <Plus size={16} />
          Создать AI-профиль
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 20 }}>
        {profiles.map(p => (
          <div key={p.id} id={`profile-card-${p.id}`} className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{
                  width: 42,
                  height: 42,
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(168, 85, 247, 0.15)',
                  color: '#c084fc',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <Cpu size={22} />
                </div>
                <div>
                  <h3 style={{ fontSize: 16 }}>{p.name}</h3>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{p.description || 'Пользовательский профиль'}</span>
                </div>
              </div>
              {p.is_default && <span className="badge badge-emerald">По умолчанию</span>}
            </div>

            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <span className="badge badge-blue">Стиль: {p.style}</span>
              <span className="badge badge-purple">Макс токенов: {p.max_tokens}</span>
            </div>

            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 4 }}>
                Системная инструкция (System Policy):
              </div>
              <div style={{
                background: 'rgba(0,0,0,0.3)',
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                fontSize: 12,
                color: 'var(--text-main)',
                fontFamily: 'var(--font-mono)',
                lineHeight: 1.4,
              }}>
                {p.system_policy}
              </div>
            </div>

            {p.forbidden_topics && p.forbidden_topics.length > 0 && (
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#f87171', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <ShieldCheck size={14} />
                  Запрещенные темы (Response Guard filter):
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {p.forbidden_topics.map((t, idx) => (
                    <span key={idx} className="badge badge-rose">
                      🚫 {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Modal: Create Profile */}
      {isModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
        }}>
          <div className="glass-card" style={{ width: 500 }}>
            <h3 style={{ fontSize: 18, marginBottom: 16 }}>Новый AI Профиль</h3>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label className="form-label">Название профиля</label>
                <input 
                  id="input-profile-name"
                  className="form-input" 
                  placeholder="например: VIP Клиенты (Формальный)"
                  value={newProfile.name}
                  onChange={e => setNewProfile({ ...newProfile, name: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Краткое описание</label>
                <input 
                  id="input-profile-desc"
                  className="form-input" 
                  placeholder="Сдержанный тон для партнеров"
                  value={newProfile.description}
                  onChange={e => setNewProfile({ ...newProfile, description: e.target.value })}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Стиль общения</label>
                  <select 
                    id="select-profile-style"
                    className="form-select"
                    value={newProfile.style}
                    onChange={e => setNewProfile({ ...newProfile, style: e.target.value })}
                  >
                    <option value="friendly">Дружелюбный (Friendly)</option>
                    <option value="concise">Лаконичный (Concise)</option>
                    <option value="formal">Деловой / Официальный (Formal)</option>
                    <option value="technical">Технический (Technical)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Лимит длины (токенов)</label>
                  <input 
                    id="input-profile-tokens"
                    type="number" 
                    className="form-input" 
                    value={newProfile.max_tokens}
                    onChange={e => setNewProfile({ ...newProfile, max_tokens: Number(e.target.value) })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Системная политика (Инструкция)</label>
                <textarea 
                  id="textarea-profile-policy"
                  className="form-textarea" 
                  rows={3}
                  placeholder="Инструкция для LLM по стилю и границам поведения"
                  value={newProfile.system_policy}
                  onChange={e => setNewProfile({ ...newProfile, system_policy: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Запрещенные темы (через запятую)</label>
                <input 
                  id="input-profile-forbidden"
                  className="form-input" 
                  placeholder="пароли, платежи, токены, закрытая документация"
                  value={newProfile.forbidden_topics_str}
                  onChange={e => setNewProfile({ ...newProfile, forbidden_topics_str: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 20 }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Отмена</button>
                <button id="btn-save-profile" type="submit" className="btn btn-primary">Создать профиль</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
