import React, { useEffect, useState } from 'react';
import { api, ActionDraft } from '../api/client';
import { Check, X, Edit3, Send, MessageSquare, ShieldAlert } from 'lucide-react';

export const ApprovalQueuePage: React.FC = () => {
  const [drafts, setDrafts] = useState<ActionDraft[]>([]);
  const [editedTexts, setEditedTexts] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadDrafts = async () => {
    try {
      setLoading(true);
      const data = await api.getPendingActions();
      setDrafts(data);
      const texts: Record<number, string> = {};
      data.forEach(d => {
        texts[d.id] = d.proposed_text;
      });
      setEditedTexts(texts);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDrafts();
  }, []);

  const handleApprove = async (id: number) => {
    try {
      setErrorMsg(null);
      const currentText = editedTexts[id];
      const res = await api.approveAction(id, currentText);
      if (res.success) {
        await loadDrafts();
      }
    } catch (e: any) {
      setErrorMsg(`Response Guard отклонил отправку: ${e.message}`);
    }
  };

  const handleReject = async (id: number) => {
    await api.rejectAction(id, "Отклонено пользователем из интерфейса");
    await loadDrafts();
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h2 style={{ fontSize: 22 }}>Очередь подтверждения черновиков (Human-in-the-loop)</h2>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            AI генерирует черновик ответа; вы можете отредактировать текст или одобрить отправку в один клик
          </p>
        </div>
        <span className="badge badge-amber" style={{ fontSize: 13, padding: '6px 14px' }}>
          Ожидают проверки: {drafts.length}
        </span>
      </div>

      {errorMsg && (
        <div style={{
          background: 'var(--rose-glow)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: 'var(--radius-md)',
          padding: '12px 18px',
          marginBottom: 20,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          color: '#fca5a5',
          fontSize: 14,
        }}>
          <ShieldAlert size={20} color="#ef4444" />
          <span>{errorMsg}</span>
        </div>
      )}

      {drafts.length === 0 ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
          <MessageSquare size={48} style={{ opacity: 0.3, margin: '0 auto 16px auto', display: 'block' }} />
          <h3 style={{ fontSize: 18, color: '#fff', marginBottom: 6 }}>Все черновики обработаны</h3>
          <p style={{ fontSize: 14 }}>Новые предложенные AI ответы появятся здесь автоматически при входящих сообщениях.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {drafts.map(d => (
            <div key={d.id} id={`draft-item-${d.id}`} className="glass-card" style={{ borderLeft: '4px solid var(--amber)' }}>
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <div>
                  <span style={{ fontWeight: 700, fontSize: 15, color: '#fff' }}>{d.sender_name}</span>
                  <span style={{ color: 'var(--text-dim)', fontSize: 13, marginLeft: 8 }}>({d.chat_title})</span>
                </div>
                <span className="badge badge-amber" style={{ fontSize: 11 }}>
                  Причина: {d.reason}
                </span>
              </div>

              {/* Incoming Context */}
              <div style={{
                background: 'rgba(0,0,0,0.25)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '12px 14px',
                marginBottom: 16,
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600, marginBottom: 4 }}>
                  Входящее сообщение:
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-main)', fontStyle: 'italic' }}>
                  "{d.incoming_text}"
                </div>
              </div>

              {/* Proposed Response Editable Textarea */}
              <div className="form-group">
                <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Edit3 size={14} color="var(--primary-glow)" />
                  Предложенный AI-ответ (доступен для редактирования):
                </label>
                <textarea
                  id={`draft-textarea-${d.id}`}
                  className="form-textarea"
                  rows={3}
                  value={editedTexts[d.id] || ''}
                  onChange={e => setEditedTexts({ ...editedTexts, [d.id]: e.target.value })}
                />
              </div>

              {/* Actions: Approve & Reject */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 12 }}>
                <button
                  id={`btn-reject-draft-${d.id}`}
                  className="btn btn-danger"
                  onClick={() => handleReject(d.id)}
                >
                  <X size={15} />
                  Отклонить
                </button>
                <button
                  id={`btn-approve-draft-${d.id}`}
                  className="btn btn-success"
                  onClick={() => handleApprove(d.id)}
                >
                  <Send size={15} />
                  Одобрить и отправить
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
