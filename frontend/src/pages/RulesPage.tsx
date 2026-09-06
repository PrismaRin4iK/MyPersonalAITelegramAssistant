import React, { useEffect, useState } from 'react';
import { api, RuleItem, CategoryItem } from '../api/client';
import { Sliders, Plus, Trash2, CheckCircle, XCircle, ArrowUpDown, Sparkles } from 'lucide-react';

export const RulesPage: React.FC = () => {
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // New rule form state
  const [newRule, setNewRule] = useState({
    name: '',
    scope: 'all_groups',
    subject: 'type:group',
    action: 'allow_auto',
    priority: 30,
    auto_reply: true,
    analysis: true,
    summary: true,
    min_importance: 6,
  });

  const loadData = async () => {
    try {
      const [r, c] = await Promise.all([
        api.getRules(), 
        api.getCategories()
      ]);
      setRules(r);
      setCategories(c);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRule.name) return;

    let apiScope = newRule.scope;
    let apiSubject = newRule.subject;

    if (newRule.scope === 'all_groups') {
      apiScope = 'chat_type';
      apiSubject = 'type:group';
    } else if (newRule.scope === 'all_private') {
      apiScope = 'chat_type';
      apiSubject = 'type:private';
    } else if (newRule.scope === 'global') {
      apiScope = 'global';
      apiSubject = 'global';
    } else if (newRule.scope === 'user') {
      apiSubject = newRule.subject.startsWith('user:') ? newRule.subject : `user:${newRule.subject}`;
    } else if (newRule.scope === 'group') {
      apiSubject = newRule.subject.startsWith('chat:') ? newRule.subject : `chat:${newRule.subject}`;
    }

    await api.createRule({
      name: newRule.name,
      scope: apiScope,
      subject: apiSubject,
      action: newRule.action,
      priority: Number(newRule.priority),
      conditions: {
        auto_reply: newRule.auto_reply,
        analysis: newRule.analysis,
        summary: newRule.summary,
        min_importance: Number(newRule.min_importance),
      },
      is_active: true,
    });

    setIsModalOpen(false);
    setNewRule({
      name: '',
      scope: 'all_groups',
      subject: 'type:group',
      action: 'allow_auto',
      priority: 30,
      auto_reply: true,
      analysis: true,
      summary: true,
      min_importance: 6,
    });
    await loadData();
  };

  const handleToggleRule = async (rule: RuleItem) => {
    await api.updateRule(rule.id, { is_active: !rule.is_active });
    await loadData();
  };

  const handleDeleteRule = async (id: number) => {
    if (confirm("Удалить это правило политики?")) {
      await api.deleteRule(id);
      await loadData();
    }
  };

  const getCategoryTitle = (subject?: string) => {
    if (!subject) return '';
    const clean = subject.replace('category:', '');
    const found = categories.find(c => c.id === clean);
    return found ? found.name : clean;
  };

  const renderScopeBadge = (r: RuleItem) => {
    if (r.scope === 'global') {
      return <span className="badge badge-emerald">🌐 Все чаты</span>;
    }
    if (r.scope === 'chat_type' && (r.subject === 'type:group' || r.subject === 'group')) {
      return <span className="badge badge-blue">👥 Все группы</span>;
    }
    if (r.scope === 'chat_type' && (r.subject === 'type:private' || r.subject === 'private')) {
      return <span className="badge badge-purple">👤 Все личные</span>;
    }
    if (r.scope === 'category') {
      return <span className="badge badge-amber">🏷 Категория</span>;
    }
    if (r.scope === 'group') {
      return <span className="badge badge-blue">💬 Группа</span>;
    }
    if (r.scope === 'user') {
      return <span className="badge badge-purple">🎯 Пользователь</span>;
    }
    return <span className="badge badge-blue">{r.scope}</span>;
  };

  const renderSubjectText = (r: RuleItem) => {
    if (r.scope === 'global') return null;
    if (r.scope === 'chat_type' && (r.subject === 'type:group' || r.subject === 'group')) {
      return <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>Все групповые чаты</div>;
    }
    if (r.scope === 'chat_type' && (r.subject === 'type:private' || r.subject === 'private')) {
      return <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>Все личные диалоги</div>;
    }
    if (r.scope === 'category') {
      return (
        <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
          Категория: <strong>{getCategoryTitle(r.subject)}</strong>
        </div>
      );
    }
    if (r.subject) {
      return (
        <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
          Цель: {r.subject}
        </div>
      );
    }
    return null;
  };

  const onScopeChange = (sc: string) => {
    let defaultSubj = '';
    if (sc === 'all_groups') {
      defaultSubj = 'type:group';
    } else if (sc === 'all_private') {
      defaultSubj = 'type:private';
    } else if (sc === 'global') {
      defaultSubj = 'global';
    } else if (sc === 'category') {
      defaultSubj = categories.length > 0 ? `category:${categories[0].id}` : 'category:close';
    }
    setNewRule({ ...newRule, scope: sc, subject: defaultSubj });
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h2 style={{ fontSize: 22 }}>Rule Engine (Детерминированные правила)</h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            AI не принимает решения единолично: правила имеют наивысший приоритет исполнения
          </p>
        </div>
        <button 
          id="btn-create-rule"
          className="btn btn-primary"
          onClick={() => setIsModalOpen(true)}
        >
          <Plus size={16} />
          Создать правило
        </button>
      </div>

      <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 80 }}>Приоритет</th>
              <th>Название правила</th>
              <th>Область (Scope)</th>
              <th>Действие</th>
              <th>Условия политики</th>
              <th style={{ width: 100 }}>Статус</th>
              <th style={{ width: 80 }}>Удалить</th>
            </tr>
          </thead>
          <tbody>
            {rules.map(r => (
              <tr key={r.id} id={`rule-row-${r.id}`}>
                <td>
                  <span className="badge badge-purple" style={{ fontWeight: 700 }}>
                    #{r.priority}
                  </span>
                </td>
                <td>
                  <strong style={{ color: '#fff', fontSize: 14 }}>{r.name}</strong>
                  {renderSubjectText(r)}
                </td>
                <td>
                  {renderScopeBadge(r)}
                </td>
                <td>
                  <span className={`badge ${r.action === 'allow_auto' ? 'badge-emerald' : (r.action === 'force_draft' ? 'badge-amber' : 'badge-rose')}`}>
                    {r.action === 'allow_auto' ? 'Автоответ' : (r.action === 'force_draft' ? 'Черновик' : 'Только анализ')}
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {r.conditions?.auto_reply && <span className="badge badge-emerald">Reply: ON</span>}
                    {r.conditions?.analysis && <span className="badge badge-blue">AI: ON</span>}
                    {r.conditions?.summary && <span className="badge badge-purple">Summary: ON</span>}
                    {r.conditions?.min_importance && (
                      <span className="badge badge-amber">Мин. важность: ≥ {r.conditions.min_importance}</span>
                    )}
                  </div>
                </td>
                <td>
                  <label className="switch">
                    <input 
                      type="checkbox" 
                      checked={r.is_active}
                      onChange={() => handleToggleRule(r)}
                    />
                    <span className="slider" />
                  </label>
                </td>
                <td>
                  <button 
                    id={`btn-del-rule-${r.id}`}
                    className="btn btn-secondary" 
                    style={{ padding: '6px 8px', color: '#f87171' }}
                    onClick={() => handleDeleteRule(r.id)}
                  >
                    <Trash2 size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modal: Visual Rule Builder */}
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
          <div className="glass-card" style={{ width: 540, maxHeight: '90vh', overflowY: 'auto' }}>
            <h3 style={{ fontSize: 18, marginBottom: 16 }}>Конструктор правил (Visual Rule Builder)</h3>

            <form onSubmit={handleCreateRule}>
              <div className="form-group">
                <label className="form-label">Название правила</label>
                <input 
                  id="input-rule-name"
                  className="form-input" 
                  placeholder="например: Для Марии -> Черновик при важности >= 5"
                  value={newRule.name}
                  onChange={e => setNewRule({ ...newRule, name: e.target.value })}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Область действия (Scope)</label>
                  <select 
                    id="select-rule-scope"
                    className="form-select"
                    value={newRule.scope}
                    onChange={e => onScopeChange(e.target.value)}
                  >
                    <option value="all_groups">👥 Все группы (все групповые чаты)</option>
                    <option value="all_private">👤 Все личные переписки (direct)</option>
                    <option value="category">🏷 Категория контактов</option>
                    <option value="global">🌐 Глобально (все чаты без исключения)</option>
                    <option value="user">🎯 Конкретный контакт (по ID)</option>
                    <option value="group">💬 Конкретная группа (по ID чата)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Цель правила (Subject)</label>
                  {newRule.scope === 'all_groups' ? (
                    <div style={{
                      background: 'rgba(56, 189, 248, 0.08)',
                      border: '1px solid rgba(56, 189, 248, 0.25)',
                      borderRadius: 8,
                      padding: '9px 12px',
                      fontSize: 13,
                      color: '#38bdf8',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      minHeight: 40,
                    }}>
                      <span>👥 Все группы и супергруппы</span>
                    </div>
                  ) : newRule.scope === 'all_private' ? (
                    <div style={{
                      background: 'rgba(168, 85, 247, 0.08)',
                      border: '1px solid rgba(168, 85, 247, 0.25)',
                      borderRadius: 8,
                      padding: '9px 12px',
                      fontSize: 13,
                      color: '#c084fc',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      minHeight: 40,
                    }}>
                      <span>👤 Все личные диалоги</span>
                    </div>
                  ) : newRule.scope === 'global' ? (
                    <div style={{
                      background: 'rgba(52, 211, 153, 0.08)',
                      border: '1px solid rgba(52, 211, 153, 0.25)',
                      borderRadius: 8,
                      padding: '9px 12px',
                      fontSize: 13,
                      color: '#34d399',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      minHeight: 40,
                    }}>
                      <span>🌐 Все чаты без исключений</span>
                    </div>
                  ) : newRule.scope === 'category' ? (
                    <select
                      id="select-rule-category-subject"
                      className="form-select"
                      value={newRule.subject}
                      onChange={e => setNewRule({ ...newRule, subject: e.target.value })}
                    >
                      {categories.map(cat => (
                        <option key={cat.id} value={`category:${cat.id}`}>
                          {cat.name} ({cat.id})
                        </option>
                      ))}
                    </select>
                  ) : newRule.scope === 'user' ? (
                    <input 
                      id="input-rule-subject-user"
                      className="form-input" 
                      placeholder="ID пользователя, напр: 1688653559"
                      value={newRule.subject.replace(/^user:/, '')}
                      onChange={e => setNewRule({ ...newRule, subject: e.target.value })}
                      required
                    />
                  ) : (
                    <input 
                      id="input-rule-subject-group"
                      className="form-input" 
                      placeholder="ID группы, напр: -1001234567890"
                      value={newRule.subject.replace(/^chat:/, '')}
                      onChange={e => setNewRule({ ...newRule, subject: e.target.value })}
                      required
                    />
                  )}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Действие (Action)</label>
                  <select 
                    id="select-rule-action"
                    className="form-select"
                    value={newRule.action}
                    onChange={e => setNewRule({ ...newRule, action: e.target.value, auto_reply: e.target.value === 'allow_auto' })}
                  >
                    <option value="allow_auto">Разрешить автоответ</option>
                    <option value="force_draft">Предложение ответа (Черновик)</option>
                    <option value="analysis_only">Только анализ</option>
                    <option value="ignore">Игнорировать</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Приоритет (меньше = главнее)</label>
                  <input 
                    id="input-rule-priority"
                    type="number" 
                    className="form-input" 
                    value={newRule.priority}
                    onChange={e => setNewRule({ ...newRule, priority: Number(e.target.value) })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Минимальная важность для Саммари в «Избранное»: {newRule.min_importance}</label>
                <input 
                  id="range-rule-importance"
                  type="range" 
                  min="1" 
                  max="10" 
                  value={newRule.min_importance}
                  onChange={e => setNewRule({ ...newRule, min_importance: Number(e.target.value) })}
                  style={{ width: '100%', accentColor: 'var(--primary-glow)' }}
                />
              </div>

              <div style={{ display: 'flex', gap: 20, margin: '16px 0' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
                  <input 
                    type="checkbox" 
                    checked={newRule.auto_reply}
                    onChange={e => setNewRule({ ...newRule, auto_reply: e.target.checked })}
                  />
                  Автоответ включен
                </label>

                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer' }}>
                  <input 
                    type="checkbox" 
                    checked={newRule.summary}
                    onChange={e => setNewRule({ ...newRule, summary: e.target.checked })}
                  />
                  Саммари в «Избранное»
                </label>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 20 }}>
                <button 
                  type="button" 
                  className="btn btn-secondary"
                  onClick={() => setIsModalOpen(false)}
                >
                  Отмена
                </button>
                <button 
                  id="btn-save-rule"
                  type="submit" 
                  className="btn btn-primary"
                >
                  Сохранить правило
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
