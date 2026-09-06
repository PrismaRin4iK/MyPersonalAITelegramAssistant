import React, { useEffect, useState } from 'react';
import { api, ContactItem, CategoryItem } from '../api/client';
import { 
  User, 
  Sparkles, 
  BookOpen, 
  Clock, 
  Tag, 
  FolderPlus, 
  RefreshCw,
  Search,
  X,
  AlertCircle,
  Check,
  Zap,
  MessageSquare
} from 'lucide-react';

export const ContactsPage: React.FC = () => {
  const [contacts, setContacts] = useState<ContactItem[]>([]);
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [selectedContact, setSelectedContact] = useState<any | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncNotice, setSyncNotice] = useState<{ success: boolean; message: string } | null>(null);

  // New category modal state
  const [isCatModalOpen, setIsCatModalOpen] = useState(false);
  const [catName, setCatName] = useState('');
  const [catId, setCatId] = useState('');
  const [catColor, setCatColor] = useState('#38bdf8');
  const [catDesc, setCatDesc] = useState('');
  const [catPrompt, setCatPrompt] = useState('');
  const [savingCat, setSavingCat] = useState(false);
  const [catError, setCatError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [cts, cats] = await Promise.all([
        api.getContacts(),
        api.getCategories()
      ]);
      setContacts(cts);
      setCategories(cats);
      if (cts.length > 0 && !selectedContact) {
        loadContactDetails(cts[0].id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadContactDetails = async (id: number) => {
    try {
      const details = await api.getContactDetails(id);
      setSelectedContact(details);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSyncContacts = async () => {
    setSyncing(true);
    setSyncNotice(null);
    try {
      const res = await api.syncContacts();
      setSyncNotice({ success: true, message: res.message });
      await loadData();
    } catch (err: any) {
      setSyncNotice({ success: false, message: err.message || "Ошибка синхронизации контактов" });
    } finally {
      setSyncing(false);
    }
  };

  const handleUpdateMode = async (contactId: number, ai_mode: string) => {
    await api.updateContact(contactId, { ai_mode });
    await loadData();
    if (selectedContact?.contact.id === contactId) {
      await loadContactDetails(contactId);
    }
  };

  const handleUpdateCategory = async (contactId: number, category: string) => {
    await api.updateContact(contactId, { category });
    await loadData();
    if (selectedContact?.contact.id === contactId) {
      await loadContactDetails(contactId);
    }
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!catName.trim()) {
      setCatError("Укажите название категории");
      return;
    }
    const finalId = catId.trim() || catName.trim().toLowerCase().replace(/\s+/g, '_');
    setSavingCat(true);
    setCatError(null);
    try {
      await api.createCategory({
        id: finalId,
        name: catName.trim(),
        color: catColor,
        description: catDesc.trim(),
        prompt_instruction: catPrompt.trim(),
      });
      setIsCatModalOpen(false);
      setCatName('');
      setCatId('');
      setCatDesc('');
      setCatPrompt('');
      await loadData();
    } catch (err: any) {
      setCatError(err.message || "Не удалось сохранить категорию");
    } finally {
      setSavingCat(false);
    }
  };

  const filteredContacts = contacts.filter(c => {
    const matchesCat = activeFilter === 'all' || c.category === activeFilter;
    if (!matchesCat) return false;

    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase().trim();
    return (
      (c.display_name && c.display_name.toLowerCase().includes(q)) ||
      (c.username && c.username.toLowerCase().includes(q)) ||
      (c.phone && c.phone.toLowerCase().includes(q)) ||
      (c.telegram_user_id && c.telegram_user_id.toLowerCase().includes(q))
    );
  });

  const getCategoryInfo = (catId?: string) => {
    const defaultCat = { id: 'colleague', name: 'Коллега', color: '#38bdf8', prompt_instruction: 'Деловой, дружелюбный тон.' };
    if (!catId) return defaultCat;
    return categories.find(c => c.id === catId) || defaultCat;
  };

  const getEffectiveBehaviorBadge = (c: ContactItem) => {
    const mode = c.ai_mode;
    const isAuto = mode === 'auto_reply' || (mode !== 'draft' && mode !== 'analysis_only' && mode !== 'ignored' && (c.category === 'close' || c.category === 'family'));
    const isDraft = mode === 'draft';
    const isAnalysis = mode === 'analysis_only';
    const isIgnored = mode === 'ignored';

    if (isAuto) {
      return (
        <span className="badge badge-emerald" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <Zap size={12} />
          Автоответ ⚡️
        </span>
      );
    } else if (isDraft) {
      return (
        <span className="badge badge-amber" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <MessageSquare size={12} />
          Черновик ✍️
        </span>
      );
    } else if (isAnalysis) {
      return (
        <span className="badge badge-blue" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          Только анализ 🔍
        </span>
      );
    } else if (isIgnored) {
      return (
        <span className="badge" style={{ background: 'rgba(255,255,255,0.1)', color: 'var(--text-muted)' }}>
          Игнор 🚫
        </span>
      );
    }
    return (
      <span className="badge badge-amber" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
        По категории
      </span>
    );
  };

  const COLOR_PALETTE = [
    '#f43f5e', // Rose / Close
    '#f97316', // Orange / Family
    '#10b981', // Emerald / Friend
    '#06b6d4', // Cyan
    '#38bdf8', // Sky / Colleague
    '#8b5cf6', // Violet / Client
    '#eab308', // Amber / VIP
    '#ec4899', // Pink
    '#94a3b8', // Slate / Stranger
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 24 }}>
      {/* Left column: Contact list */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h2 style={{ fontSize: 22 }}>Контакты и категории</h2>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              Категории (Близкие, Семья, Друзья, Коллеги), поиск по контактам и автоответы
            </p>
          </div>

          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              id="btn-sync-contacts"
              className="btn btn-secondary"
              onClick={handleSyncContacts}
              disabled={syncing}
              style={{ display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}
              title="Импортировать контакты и чаты напрямую из вашего Telegram"
            >
              <RefreshCw size={15} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
              {syncing ? 'Синхронизация...' : '🔄 Подтянуть контакты'}
            </button>

            <button
              id="btn-add-category"
              className="btn btn-primary"
              onClick={() => setIsCatModalOpen(true)}
              style={{ display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}
            >
              <FolderPlus size={16} />
              + Своя категория
            </button>
          </div>
        </div>

        {/* Sync notification banner */}
        {syncNotice && (
          <div style={{
            padding: '10px 14px',
            borderRadius: 'var(--radius-sm)',
            background: syncNotice.success ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
            border: `1px solid ${syncNotice.success ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            color: syncNotice.success ? '#34d399' : '#fca5a5',
            fontSize: 13,
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 8,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {syncNotice.success ? <Check size={16} /> : <AlertCircle size={16} />}
              <span>{syncNotice.message}</span>
            </div>
            <button
              onClick={() => setSyncNotice(null)}
              style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', padding: 2 }}
            >
              ✕
            </button>
          </div>
        )}

        {/* SEARCH BAR */}
        <div style={{ position: 'relative', marginBottom: 14 }}>
          <div style={{
            position: 'absolute',
            left: 14,
            top: '50%',
            transform: 'translateY(-50%)',
            display: 'flex',
            alignItems: 'center',
            color: 'var(--text-muted)',
            pointerEvents: 'none',
          }}>
            <Search size={16} />
          </div>
          <input
            id="input-search-contacts"
            type="text"
            className="form-input"
            placeholder="Поиск по имени, @юзернейму, номеру телефона или ID..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ paddingLeft: 40, paddingRight: searchQuery ? 38 : 14 }}
          />
          {searchQuery && (
            <button
              id="btn-clear-contact-search"
              onClick={() => setSearchQuery('')}
              style={{
                position: 'absolute',
                right: 12,
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: 4,
              }}
              title="Очистить поиск"
            >
              <X size={15} />
            </button>
          )}
        </div>

        {/* Search match stats */}
        {searchQuery.trim() && (
          <div style={{ fontSize: 12, color: 'var(--primary-glow)', marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Найдено контактов: <strong>{filteredContacts.length}</strong> из {contacts.length}</span>
            <button
              onClick={() => setSearchQuery('')}
              style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', textDecoration: 'underline', fontSize: 12 }}
            >
              Сбросить поиск
            </button>
          </div>
        )}

        {/* Dynamic Category filter tabs */}
        <div style={{ 
          display: 'flex', 
          gap: 6, 
          background: 'rgba(255,255,255,0.04)', 
          padding: 6, 
          borderRadius: 'var(--radius-sm)',
          marginBottom: 18,
          overflowX: 'auto',
          flexWrap: 'wrap'
        }}>
          <button
            id="filter-all"
            className={`btn ${activeFilter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '4px 12px', fontSize: 12 }}
            onClick={() => setActiveFilter('all')}
          >
            Все ({contacts.length})
          </button>
          {categories.map(cat => {
            const count = contacts.filter(c => c.category === cat.id).length;
            const isAct = activeFilter === cat.id;
            return (
              <button
                key={cat.id}
                id={`filter-${cat.id}`}
                className={`btn ${isAct ? 'btn-primary' : 'btn-secondary'}`}
                style={{ 
                  padding: '4px 12px', 
                  fontSize: 12,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  borderColor: isAct ? undefined : `${cat.color}40`,
                }}
                onClick={() => setActiveFilter(cat.id)}
              >
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: cat.color }} />
                <span>{cat.name}</span>
                <span style={{ opacity: 0.7, fontSize: 11 }}>({count})</span>
              </button>
            );
          })}
        </div>

        {/* Contact cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {filteredContacts.length === 0 ? (
            <div className="glass-card" style={{ textAlign: 'center', padding: 36, color: 'var(--text-muted)' }}>
              {searchQuery ? (
                <div>
                  <Search size={32} style={{ opacity: 0.3, marginBottom: 8 }} />
                  <p>По запросу «{searchQuery}» контактов не найдено.</p>
                  <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={() => setSearchQuery('')}>
                    Очистить поиск
                  </button>
                </div>
              ) : contacts.length === 0 ? (
                <div>
                  <User size={32} style={{ opacity: 0.3, marginBottom: 8 }} />
                  <p>В базе пока нет контактов.</p>
                  <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={handleSyncContacts} disabled={syncing}>
                    🔄 Подтянуть контакты из Telegram
                  </button>
                </div>
              ) : (
                <p>В выбранной категории нет контактов.</p>
              )}
            </div>
          ) : (
            filteredContacts.map(c => {
              const isSelected = selectedContact?.contact.id === c.id;
              const catInfo = getCategoryInfo(c.category);

              return (
                <div 
                  key={c.id}
                  id={`contact-card-${c.id}`}
                  className="glass-card"
                  style={{
                    padding: '16px 20px',
                    cursor: 'pointer',
                    borderColor: isSelected ? 'var(--border-focus)' : 'var(--border-subtle)',
                    background: isSelected ? 'rgba(56, 189, 248, 0.08)' : 'var(--bg-card)',
                    transition: 'border-color 0.2s, background 0.2s',
                  }}
                  onClick={() => loadContactDetails(c.id)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                      <div style={{
                        width: 46,
                        height: 46,
                        borderRadius: '50%',
                        background: `${catInfo.color}20`,
                        border: `2px solid ${catInfo.color}`,
                        color: catInfo.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 700,
                        fontSize: 18,
                        flexShrink: 0,
                      }}>
                        {c.category === 'close' ? '❤️' : (c.category === 'family' ? '🏡' : (c.category === 'friend' ? '🤝' : (c.display_name ? c.display_name[0].toUpperCase() : '👤')))}
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                          <span style={{ fontWeight: 600, fontSize: 15, color: '#fff' }}>{c.display_name}</span>
                          
                          {/* Category Badge */}
                          <span 
                            className="badge" 
                            style={{ 
                              background: `${catInfo.color}22`, 
                              color: catInfo.color, 
                              borderColor: `${catInfo.color}66`,
                              fontWeight: 600,
                            }}
                          >
                            {catInfo.name}
                          </span>

                          {/* Effective AI Behavior Badge */}
                          {getEffectiveBehaviorBadge(c)}
                        </div>
                        <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                          {c.username && <span>@{c.username}</span>}
                          {c.phone && <span>тел: {c.phone}</span>}
                          <span>ID: <code>{c.telegram_user_id}</code></span>
                        </div>
                      </div>
                    </div>

                    {/* Controls on card: Category selector & AI Mode */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }} onClick={e => e.stopPropagation()}>
                      {/* Category dropdown */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Категория:</span>
                        <select
                          id={`select-category-${c.id}`}
                          className="form-select"
                          style={{ width: 135, fontSize: 12, padding: '5px 8px', background: 'var(--card-bg)' }}
                          value={c.category}
                          onChange={e => handleUpdateCategory(c.id, e.target.value)}
                        >
                          {categories.map(cat => (
                            <option key={cat.id} value={cat.id}>
                              {cat.name}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* AI Mode selector */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Режим:</span>
                        <select
                          id={`select-mode-${c.id}`}
                          className="form-select"
                          style={{ width: 175, fontSize: 12, padding: '5px 8px' }}
                          value={c.ai_mode || 'inherit'}
                          onChange={e => handleUpdateMode(c.id, e.target.value)}
                        >
                          <option value="inherit">По правилу категории (авто)</option>
                          <option value="auto_reply">Всегда автоответ ⚡️</option>
                          <option value="draft">Черновик (на согласование) ✍️</option>
                          <option value="analysis_only">Только анализ 🔍</option>
                          <option value="ignored">Игнорировать 🚫</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right column: Contact profile details & memory */}
      <div>
        {selectedContact ? (
          <div className="glass-card" style={{ position: 'sticky', top: 90 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingBottom: 16, borderBottom: '1px solid var(--border-subtle)', marginBottom: 16 }}>
              <div style={{
                width: 50,
                height: 50,
                borderRadius: 'var(--radius-md)',
                background: `${getCategoryInfo(selectedContact.contact.category).color}25`,
                border: `2px solid ${getCategoryInfo(selectedContact.contact.category).color}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 22,
                flexShrink: 0,
              }}>
                {selectedContact.contact.category === 'close' ? '❤️' : (selectedContact.contact.category === 'family' ? '🏡' : '👤')}
              </div>
              <div style={{ overflow: 'hidden' }}>
                <h3 style={{ fontSize: 16, color: '#fff', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  {selectedContact.contact.display_name}
                </h3>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {selectedContact.contact.username ? `@${selectedContact.contact.username}` : `ID: ${selectedContact.contact.telegram_user_id}`}
                </div>
              </div>
            </div>

            {/* Active Category & AI Persona Guidance */}
            <div style={{ 
              marginBottom: 16, 
              padding: 12, 
              borderRadius: 'var(--radius-sm)', 
              background: `${getCategoryInfo(selectedContact.contact.category).color}10`,
              border: `1px solid ${getCategoryInfo(selectedContact.contact.category).color}33`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: getCategoryInfo(selectedContact.contact.category).color, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Категория: {getCategoryInfo(selectedContact.contact.category).name}
                </span>
                <select
                  className="form-select"
                  style={{ width: 130, fontSize: 11, padding: '3px 6px' }}
                  value={selectedContact.contact.category}
                  onChange={e => handleUpdateCategory(selectedContact.contact.id, e.target.value)}
                >
                  {categories.map(cat => (
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                </select>
              </div>

              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.85)', lineHeight: 1.4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, fontWeight: 600 }}>
                  <Sparkles size={14} color={getCategoryInfo(selectedContact.contact.category).color} />
                  <span>Промпт для нейросети:</span>
                </div>
                <p style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>
                  "{getCategoryInfo(selectedContact.contact.category).prompt_instruction}"
                </p>
              </div>
            </div>

            {/* AI Behavior Mode Box in Details Panel */}
            <div style={{ 
              marginBottom: 18, 
              padding: 12, 
              borderRadius: 'var(--radius-sm)', 
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--border-subtle)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontSize: 12, fontWeight: 600 }}>Поведение AI:</span>
                <select
                  className="form-select"
                  style={{ width: 165, fontSize: 11, padding: '3px 6px' }}
                  value={selectedContact.contact.ai_mode || 'inherit'}
                  onChange={e => handleUpdateMode(selectedContact.contact.id, e.target.value)}
                >
                  <option value="inherit">По правилу категории</option>
                  <option value="auto_reply">Всегда автоответ ⚡️</option>
                  <option value="draft">Черновик (согласование) ✍️</option>
                  <option value="analysis_only">Только анализ 🔍</option>
                  <option value="ignored">Игнорировать 🚫</option>
                </select>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                {(() => {
                  const mode = selectedContact.contact.ai_mode;
                  const cat = selectedContact.contact.category;
                  if (mode === 'auto_reply') return '⚡️ Для этого контакта принудительно включен автоответ без согласования.';
                  if (mode === 'draft') return '✍️ Ответы генерируются и направляются на ваше согласование во вкладку Черновики.';
                  if (mode === 'analysis_only') return '🔍 Нейросеть только анализирует входящие и обновляет память, не формируя ответы.';
                  if (mode === 'ignored') return '🚫 Сообщения от этого контакта полностью игнорируются.';
                  if (cat === 'close' || cat === 'family') return '⚡️ По правилу категории (Близкие/Семья) включен приоритетный автоответ без задержек.';
                  return '✍️ По умолчанию ответы формируются как черновики для подтверждения.';
                })()}
              </div>
            </div>

            {/* Extracted Memory Facts */}
            <div style={{ marginBottom: 18 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <BookOpen size={16} color="var(--primary-glow)" />
                <h4 style={{ fontSize: 14 }}>Извлеченные факты (Память AI)</h4>
              </div>
              {selectedContact.memories.length === 0 ? (
                <p style={{ fontSize: 12, color: 'var(--text-dim)' }}>Факты пока не зафиксированы в переписке.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {selectedContact.memories.map((m: any) => (
                    <div key={m.id} style={{ fontSize: 12, background: 'rgba(255,255,255,0.03)', padding: '6px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.05)' }}>
                      • {m.fact}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Unclosed Tasks */}
            <div style={{ marginBottom: 18 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <Clock size={16} color="var(--amber)" />
                <h4 style={{ fontSize: 14 }}>Незакрытые задачи</h4>
              </div>
              {selectedContact.tasks.length === 0 ? (
                <p style={{ fontSize: 12, color: 'var(--text-dim)' }}>Нет открытых задач.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {selectedContact.tasks.map((t: any) => (
                    <div key={t.id} style={{ fontSize: 12, background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)', padding: '6px 10px', borderRadius: 6 }}>
                      ▫️ {t.title}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent Decisions History */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <Tag size={16} color="var(--emerald)" />
                <h4 style={{ fontSize: 14 }}>История AI-решений</h4>
              </div>
              {selectedContact.recent_actions.length === 0 ? (
                <p style={{ fontSize: 12, color: 'var(--text-dim)' }}>Решений пока не зафиксировано.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {selectedContact.recent_actions.map((act: any) => (
                    <div key={act.id} style={{ fontSize: 11, background: 'rgba(255,255,255,0.02)', padding: '8px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.05)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600 }}>
                        <span>{act.action_type}</span>
                        <span className={`badge ${act.status === 'executed' ? 'badge-emerald' : 'badge-amber'}`}>{act.status}</span>
                      </div>
                      <div style={{ color: 'var(--text-muted)', marginTop: 2 }}>{act.reason || act.result}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="glass-card" style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
            Выберите контакт для просмотра памяти и настроек категории
          </div>
        )}
      </div>

      {/* CREATE CATEGORY MODAL */}
      {isCatModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: 16,
        }}>
          <div className="glass-card" style={{ width: '100%', maxWidth: 540, maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <FolderPlus size={22} color="var(--primary-glow)" />
                <h3 style={{ fontSize: 18, color: '#fff' }}>Добавить категорию контакта</h3>
              </div>
              <button className="btn btn-secondary" onClick={() => setIsCatModalOpen(false)} style={{ padding: '4px 10px' }}>
                ✕
              </button>
            </div>

            {catError && (
              <div style={{
                padding: '10px 14px',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#fca5a5',
                fontSize: 13,
                marginBottom: 16,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}>
                <AlertCircle size={16} />
                <span>{catError}</span>
              </div>
            )}

            <form onSubmit={handleCreateCategory}>
              <div className="form-group">
                <label className="form-label">Название категории</label>
                <input
                  id="input-category-name"
                  className="form-input"
                  placeholder="например: Близкие друзья, Партнеры, Студенты"
                  value={catName}
                  onChange={e => {
                    setCatName(e.target.value);
                    if (!catId) {
                      setCatId(e.target.value.toLowerCase().replace(/\s+/g, '_'));
                    }
                  }}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">ID категории (латиница)</label>
                  <input
                    id="input-category-id"
                    className="form-input"
                    placeholder="close_friends"
                    value={catId}
                    onChange={e => setCatId(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Цвет бейджа</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <input
                      type="color"
                      value={catColor}
                      onChange={e => setCatColor(e.target.value)}
                      style={{ width: 38, height: 38, border: 'none', borderRadius: 6, cursor: 'pointer', background: 'transparent' }}
                    />
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {COLOR_PALETTE.map(c => (
                        <span
                          key={c}
                          onClick={() => setCatColor(c)}
                          style={{
                            width: 20,
                            height: 20,
                            borderRadius: '50%',
                            background: c,
                            cursor: 'pointer',
                            outline: catColor === c ? '2px solid #fff' : 'none',
                          }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Описание категории</label>
                <input
                  id="input-category-desc"
                  className="form-input"
                  placeholder="Для кого предназначена категория"
                  value={catDesc}
                  onChange={e => setCatDesc(e.target.value)}
                />
              </div>

              <div className="form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <label className="form-label" style={{ marginBottom: 0 }}>
                    Инструкция нейросети (Промпт для генерации ответов)
                  </label>
                </div>
                <textarea
                  id="input-category-prompt"
                  className="form-textarea"
                  rows={4}
                  placeholder="Опишите, как модель должна общаться с контактами этой категории. Например: 'Собеседник — близкий друг. Тон: теплый, неформальный, на ты, без официоза. Отвечай кратко, по-приятельски, как реальный человек в Telegram.'"
                  value={catPrompt}
                  onChange={e => setCatPrompt(e.target.value)}
                />
                <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginTop: 4 }}>
                  💡 Этот промпт автоматически передается в Gemini при подготовке автоответов и черновиков для контактов этой категории.
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 20 }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsCatModalOpen(false)}>
                  Отмена
                </button>
                <button id="btn-submit-category" type="submit" className="btn btn-primary" disabled={savingCat}>
                  {savingCat ? 'Сохранение...' : 'Сохранить категорию'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
