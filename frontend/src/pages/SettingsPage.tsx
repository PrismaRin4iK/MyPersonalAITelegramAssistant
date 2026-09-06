import React, { useState, useEffect } from 'react';
import { api, TelegramStatus, AiConfigItem } from '../api/client';
import { 
  Shield, 
  Trash2, 
  CheckCircle2, 
  Smartphone, 
  LogOut, 
  AlertCircle, 
  Zap, 
  ArrowRight,
  RefreshCw,
  QrCode,
  Cpu,
  Eye,
  EyeOff,
  Check,
  ExternalLink
} from 'lucide-react';

interface SettingsPageProps {
  onNavigate?: (tab: string) => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ onNavigate }) => {
  // Telegram status
  const [status, setStatus] = useState<TelegramStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState<boolean>(true);

  // Telegram credentials form state
  const [apiId, setApiId] = useState<string>('');
  const [apiHash, setApiHash] = useState<string>('');
  const [phone, setPhone] = useState<string>('');
  const [code, setCode] = useState<string>('');
  const [password2fa, setPassword2fa] = useState<string>('');
  const [step, setStep] = useState<'input' | 'code' | 'qr' | '2fa'>('input');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [qrImageUrl, setQrImageUrl] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // AI & Gemini settings state
  const [aiConfig, setAiConfig] = useState<AiConfigItem | null>(null);
  const [geminiKeyInput, setGeminiKeyInput] = useState<string>('');
  const [geminiModelInput, setGeminiModelInput] = useState<string>('gemini-3.6-flash');
  const [geminiProxyInput, setGeminiProxyInput] = useState<string>('');
  const [showGeminiKey, setShowGeminiKey] = useState<boolean>(false);
  const [savingAi, setSavingAi] = useState<boolean>(false);
  const [testingAi, setTestingAi] = useState<boolean>(false);
  const [aiTestResult, setAiTestResult] = useState<{ success: boolean; model?: string; analysis?: any; warning?: string | null; error?: string } | null>(null);
  const [aiMsg, setAiMsg] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const st = await api.getStatus();
      setStatus(st);
    } catch (e) {
      console.error("Failed to load telegram status", e);
    } finally {
      setLoadingStatus(false);
    }
  };

  const fetchAiConfig = async () => {
    try {
      const cfg = await api.getAiConfig();
      setAiConfig(cfg);
      if (cfg.gemini_model) {
        setGeminiModelInput(cfg.gemini_model);
      }
      if (cfg.gemini_proxy !== undefined) {
        setGeminiProxyInput(cfg.gemini_proxy || '');
      }
    } catch (e) {
      console.error("Failed to load AI config", e);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchAiConfig();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleRequestCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiId || !apiHash || !phone) {
      setStatusMsg("Заполните api_id, api_hash и номер телефона");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch('/api/telegram/request-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, api_id: Number(apiId), api_hash: apiHash }),
      });
      const data = await res.json();
      if (data.success) {
        setStep('code');
        setStatusMsg(`Код авторизации отправлен на номер ${data.phone}! ⚠️ ВНИМАНИЕ: Код приходит ВНУТРИ приложения Telegram (в чат 'Telegram' / Служебные уведомления), а НЕ по СМС!`);
      } else {
        setStatusMsg(`Ошибка: ${data.error || 'Не удалось отправить код'}`);
      }
    } catch (err: any) {
      setStatusMsg(`Ошибка запроса: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRequestQr = async () => {
    if (!apiId || !apiHash) {
      setStatusMsg("Заполните api_id и api_hash для генерации QR-кода");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch('/api/telegram/request-qr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_id: Number(apiId), api_hash: apiHash }),
      });
      const data = await res.json();
      if (data.success && data.qr_image_url) {
        setQrImageUrl(data.qr_image_url);
        setStep('qr');
        setStatusMsg("Сканируйте QR-код из мобильного приложения Telegram (Настройки -> Устройства -> Привязать устройство)");
        startQrPolling();
      } else {
        setStatusMsg(`Ошибка генерации QR: ${data.error || 'Не удалось создать QR-код'}`);
      }
    } catch (err: any) {
      setStatusMsg(`Ошибка: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const startQrPolling = () => {
    const timer = setInterval(async () => {
      try {
        const res = await fetch('/api/telegram/check-qr', { method: 'POST' });
        const data = await res.json();
        if (data.success && data.authorized) {
          clearInterval(timer);
          setStatusMsg("Успешный вход по QR-коду! Сессия Telegram подключена и зашифрована.");
          setStep('input');
          await fetchStatus();
        } else if (data.requires_2fa) {
          clearInterval(timer);
          setStatusMsg("QR-код успешно отсканирован! Введите ваш 2FA облачный пароль Telegram.");
          setStep('2fa');
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
  };

  const handleCompleteLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch('/api/telegram/complete-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code || null, password_2fa: password2fa || null }),
      });
      const data = await res.json();
      if (data.success) {
        setStatusMsg("Telegram сессия успешно подключена и зашифрована!");
        setStep('input');
        await fetchStatus();
      } else if (data.requires_2fa) {
        setStatusMsg("Требуется 2FA облачный пароль Telegram");
        setStep('2fa');
      } else {
        setStatusMsg(`Ошибка входа: ${data.error}`);
      }
    } catch (err: any) {
      setStatusMsg(`Ошибка входа: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDisconnect = async () => {
    if (confirm("Вы уверены, что хотите отключить текущий аккаунт Telegram от ассистента?")) {
      try {
        await api.disconnectTelegram();
        setStatusMsg("Telegram аккаунт успешно отключен.");
        setStep('input');
        await fetchStatus();
      } catch (err: any) {
        setStatusMsg(`Ошибка отключения: ${err.message}`);
      }
    }
  };

  const handleWipeData = async () => {
    if (confirm("ВНИМАНИЕ: Вы уверены, что хотите полностью стереть все сохраненные сообщения, анализы, память контактов и задачи?")) {
      await api.wipeAllData();
      alert("Все данные успешно и безвозвратно удалены (Privacy by Design).");
      await fetchStatus();
    }
  };

  const handleSaveAiConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingAi(true);
    setAiMsg(null);
    try {
      const payload: any = {
        gemini_model: geminiModelInput,
        gemini_proxy: geminiProxyInput.trim(),
        provider: 'gemini',
      };
      if (geminiKeyInput.trim()) {
        payload.gemini_api_key = geminiKeyInput.trim();
      }
      await api.saveAiConfig(payload);
      await fetchAiConfig();
      setGeminiKeyInput('');
      setAiMsg("Настройки Gemini API успешно сохранены и активированы!");
    } catch (err: any) {
      setAiMsg(`Ошибка сохранения: ${err.message}`);
    } finally {
      setSavingAi(false);
    }
  };

  const handleTestAi = async () => {
    setTestingAi(true);
    setAiTestResult(null);
    try {
      const payload: any = {
        gemini_model: geminiModelInput,
        gemini_proxy: geminiProxyInput.trim(),
      };
      if (geminiKeyInput.trim()) {
        payload.gemini_api_key = geminiKeyInput.trim();
      }
      const res = await api.testAiConnection(payload);
      setAiTestResult(res);
      if (res.success) {
        fetchAiConfig();
      }
    } catch (err: any) {
      setAiTestResult({ success: false, error: err.message });
    } finally {
      setTestingAi(false);
    }
  };

  const isConnected = Boolean(status?.is_connected && status?.account);

  return (
    <div style={{ maxWidth: 840 }}>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 22 }}>Настройки подключения и AI-анализа</h2>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          Статус авторизации Telegram MTProto, интеграция Google Gemini API и безопасность
        </p>
      </div>

      {statusMsg && (
        <div style={{
          padding: '12px 16px',
          borderRadius: 'var(--radius-sm)',
          background: 'rgba(56, 189, 248, 0.12)',
          border: '1px solid var(--border-accent)',
          marginBottom: 20,
          color: 'var(--primary-glow)',
          fontSize: 13,
        }}>
          {statusMsg}
        </div>
      )}

      {/* 1. STATUS CARD: CONNECTED VS NOT CONNECTED */}
      {isConnected && status?.account ? (
        <div className="glass-card" style={{
          marginBottom: 24,
          border: '1px solid rgba(16, 185, 129, 0.4)',
          background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(15, 23, 42, 0.7))',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <div style={{
                width: 58,
                height: 58,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #10b981, #059669)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 24,
                fontWeight: 'bold',
                color: '#fff',
                boxShadow: '0 0 20px rgba(16, 185, 129, 0.35)',
              }}>
                {status.account.first_name ? status.account.first_name[0].toUpperCase() : 'TG'}
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <h3 style={{ fontSize: 20, color: '#fff', fontWeight: 600 }}>
                    {status.account.first_name || 'Пользователь Telegram'}
                  </h3>
                  <span className="badge badge-emerald" style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px' }}>
                    <span className="pulse-dot" style={{ background: '#10b981' }} />
                    АККАУНТ ПОДКЛЮЧЕН
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 16, marginTop: 6, fontSize: 13, color: 'var(--text-muted)', flexWrap: 'wrap' }}>
                  {status.account.username && (
                    <span>Юзернейм: <strong style={{ color: '#fff' }}>@{status.account.username}</strong></span>
                  )}
                  {status.account.phone && (
                    <span>Телефон: <strong style={{ color: '#fff' }}>{status.account.phone}</strong></span>
                  )}
                  <span>ID: <code style={{ color: 'var(--primary-glow)' }}>{status.account.telegram_user_id}</code></span>
                </div>
              </div>
            </div>

            <button 
              id="btn-disconnect-tg"
              className="btn btn-danger" 
              onClick={handleDisconnect}
              style={{ display: 'flex', alignItems: 'center', gap: 8 }}
            >
              <LogOut size={16} />
              Отключить аккаунт
            </button>
          </div>

          <hr style={{ border: 'none', borderTop: '1px solid rgba(255, 255, 255, 0.08)', margin: '18px 0' }} />

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
            <div style={{ fontSize: 13, color: 'rgba(255, 255, 255, 0.85)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <CheckCircle2 size={16} color="var(--emerald)" />
              <span>Сессия MTProto зашифрована (AES-128 Fernet). Входящие сообщения автоматически поступают в очередь AI-анализа.</span>
            </div>

            {onNavigate && (
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-primary" onClick={() => onNavigate('dashboard')}>
                  Перейти в Дашборд
                  <ArrowRight size={14} />
                </button>
                <button className="btn btn-secondary" onClick={() => onNavigate('contacts')}>
                  Люди и группы
                </button>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="glass-card" style={{
          marginBottom: 24,
          border: '1px solid rgba(239, 68, 68, 0.3)',
          background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.06), rgba(15, 23, 42, 0.7))',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <div style={{
                width: 48,
                height: 48,
                borderRadius: 'var(--radius-md)',
                background: 'rgba(239, 68, 68, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <AlertCircle size={26} color="#f87171" />
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <h3 style={{ fontSize: 18, color: '#fff' }}>Telegram аккаунт не подключен</h3>
                  <span className="badge badge-rose">ОФФЛАЙН</span>
                </div>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
                  Для анализа переписок, генерации сводок и отправки автоответов авторизуйте аккаунт ниже
                </p>
              </div>
            </div>

            <button 
              className="btn btn-secondary" 
              onClick={fetchStatus}
              title="Проверить статус подключения"
            >
              <RefreshCw size={15} />
              Проверить статус
            </button>
          </div>
        </div>
      )}

      {/* 2. LOGIN FORMS (DISPLAYED ONLY WHEN NOT CONNECTED) */}
      {!isConnected && (
        <div className="glass-card" style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <div style={{
              width: 40,
              height: 40,
              borderRadius: 'var(--radius-md)',
              background: 'var(--primary-gradient)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Smartphone size={20} color="#fff" />
            </div>
            <div>
              <h3 style={{ fontSize: 16 }}>Авторизация Telegram MTProto</h3>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Получите api_id и api_hash на официальном портале Telegram Development Tools (my.telegram.org)
              </span>
            </div>
          </div>

          {step === 'qr' && qrImageUrl ? (
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <h4 style={{ fontSize: 18, marginBottom: 8, color: '#fff' }}>Отсканируйте QR-код в приложении Telegram</h4>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
                Откройте Telegram на телефоне ➔ <strong>Настройки</strong> ➔ <strong>Устройства</strong> ➔ <strong>Привязать устройство</strong>
              </p>
              <div style={{ display: 'inline-block', padding: 16, background: '#fff', borderRadius: 16, boxShadow: '0 0 30px rgba(56, 189, 248, 0.2)' }}>
                <img src={qrImageUrl} alt="Telegram QR Login" style={{ width: 220, height: 220, display: 'block' }} />
              </div>
              <div style={{ marginTop: 20 }}>
                <button type="button" className="btn btn-secondary" onClick={() => setStep('input')}>
                  Назад к вводу
                </button>
              </div>
            </div>
          ) : step === '2fa' ? (
            <form onSubmit={handleCompleteLogin}>
              <div style={{ marginBottom: 16, padding: 14, background: 'rgba(56, 189, 248, 0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-accent)' }}>
                <h4 style={{ fontSize: 16, color: 'var(--primary-glow)', marginBottom: 6 }}>
                  🔒 Требуется 2FA Облачный пароль Telegram
                </h4>
                <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                  Вход успешно подтвержден! На вашем аккаунте включена двухфакторная аутентификация. 
                  Введите ваш 2FA облачный пароль Telegram для завершения привязки.
                </p>
              </div>

              <div className="form-group">
                <label className="form-label">2FA Облачный пароль Telegram</label>
                <input
                  id="settings-2fa-password"
                  type="password"
                  className="form-input"
                  placeholder="Введите ваш облачный пароль Telegram"
                  value={password2fa}
                  onChange={e => setPassword2fa(e.target.value)}
                  required
                  autoFocus
                />
              </div>

              <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
                <button type="button" className="btn btn-secondary" onClick={() => setStep('input')}>
                  Отмена
                </button>
                <button id="btn-submit-tg-2fa" type="submit" className="btn btn-success" disabled={submitting}>
                  {submitting ? 'Проверка пароля...' : 'Подтвердить 2FA пароль и завершить вход'}
                </button>
              </div>
            </form>
          ) : step === 'code' ? (
            <form onSubmit={handleCompleteLogin}>
              <div style={{ marginBottom: 16, padding: 14, background: 'rgba(56, 189, 248, 0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-accent)' }}>
                <h4 style={{ fontSize: 16, color: 'var(--primary-glow)', marginBottom: 6 }}>
                  📱 Введите код подтверждения
                </h4>
                <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                  Код отправлен в официальный чат Telegram на ваших устройствах.
                </p>
              </div>

              <div className="form-group">
                <label className="form-label">5-значный код из Telegram</label>
                <input
                  id="settings-login-code"
                  className="form-input"
                  placeholder="12345"
                  value={code}
                  onChange={e => setCode(e.target.value)}
                  required
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label className="form-label">2FA Пароль двухфакторной аутентификации (если включен)</label>
                <input
                  id="settings-2fa-password-optional"
                  type="password"
                  className="form-input"
                  placeholder="Облачный пароль 2FA"
                  value={password2fa}
                  onChange={e => setPassword2fa(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
                <button type="button" className="btn btn-secondary" onClick={() => setStep('input')}>
                  Назад
                </button>
                <button id="btn-submit-tg-login" type="submit" className="btn btn-success" disabled={submitting}>
                  {submitting ? 'Авторизация...' : 'Завершить вход и зашифровать сессию'}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleRequestCode}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="form-group">
                  <label className="form-label">Telegram API ID (число с my.telegram.org)</label>
                  <input
                    id="settings-api-id"
                    className="form-input"
                    placeholder="например: 28471928"
                    value={apiId}
                    onChange={e => setApiId(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Telegram API HASH (32-значная строка)</label>
                  <input
                    id="settings-api-hash"
                    type="password"
                    className="form-input"
                    placeholder="32-значный хэш"
                    value={apiHash}
                    onChange={e => setApiHash(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ 
                padding: '16px', 
                background: 'rgba(56, 189, 248, 0.05)', 
                borderRadius: 'var(--radius-md)', 
                border: '1px solid rgba(56, 189, 248, 0.2)',
                marginBottom: 20,
                marginTop: 8
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                  <div>
                    <h4 style={{ fontSize: 15, color: '#fff', display: 'flex', alignItems: 'center', gap: 8 }}>
                      <QrCode size={18} color="var(--primary-glow)" />
                      Рекомендуемый способ: Вход через QR-код
                    </h4>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      Мгновенный вход без ожидания кодов и СМС. Требуются только API ID и API HASH.
                    </span>
                  </div>
                  <button 
                    type="button" 
                    className="btn btn-primary" 
                    onClick={handleRequestQr}
                    disabled={submitting}
                    style={{ whiteSpace: 'nowrap' }}
                  >
                    📷 Войти по QR-коду
                  </button>
                </div>
              </div>

              <div style={{ marginTop: 12 }}>
                <h4 style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 12 }}>
                  Или вход по номеру телефона:
                </h4>

                <div className="form-group">
                  <label className="form-label">Номер телефона Telegram аккаунта (с кодом страны)</label>
                  <input
                    id="settings-phone"
                    className="form-input"
                    placeholder="+79991234567"
                    value={phone}
                    onChange={e => setPhone(e.target.value)}
                  />
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginTop: 4 }}>
                    📱 Код приходит в системный чат Telegram на активных устройствах, не в SMS.
                  </span>
                </div>

                <button id="btn-request-tg-code" type="submit" className="btn btn-secondary" disabled={submitting}>
                  {submitting ? 'Запрос кода...' : 'Запросить код в Telegram'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* 3. AI & GOOGLE GEMINI CONFIGURATION */}
      <div className="glass-card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16, marginBottom: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 42,
              height: 42,
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, #38bdf8, #818cf8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(56, 189, 248, 0.25)',
            }}>
              <Cpu size={22} color="#fff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <h3 style={{ fontSize: 17, color: '#fff' }}>ИИ-анализ и генерация ответов (Google Gemini)</h3>
                {aiConfig?.has_gemini_key ? (
                  <span className="badge badge-emerald" style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span className="pulse-dot" style={{ background: '#10b981' }} />
                    GEMINI АКТИВЕН
                  </span>
                ) : (
                  <span className="badge badge-amber">ЛОКАЛЬНЫЙ NLP РЕЖИМ</span>
                )}
              </div>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Семантический анализ сообщений, извлечение задач, важность 1-10 и персонализированные автоответы
              </span>
            </div>
          </div>

          <a 
            href="https://aistudio.google.com/app/apikey" 
            target="_blank" 
            rel="noreferrer"
            className="btn btn-secondary"
            style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <span>Получить ключ Gemini API</span>
            <ExternalLink size={13} />
          </a>
        </div>

        {aiMsg && (
          <div style={{
            padding: '10px 14px',
            borderRadius: 'var(--radius-sm)',
            background: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            marginBottom: 16,
            color: '#34d399',
            fontSize: 13,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}>
            <Check size={16} />
            <span>{aiMsg}</span>
          </div>
        )}

        <form onSubmit={handleSaveAiConfig}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.3fr', gap: 16 }}>
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <label className="form-label" style={{ marginBottom: 0 }}>Google Gemini API Key</label>
                {aiConfig?.has_gemini_key && (
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    Текущий ключ: <code style={{ color: 'var(--primary-glow)' }}>{aiConfig.gemini_key_masked}</code>
                  </span>
                )}
              </div>
              <div style={{ position: 'relative' }}>
                <input
                  id="settings-gemini-key"
                  type={showGeminiKey ? 'text' : 'password'}
                  className="form-input"
                  placeholder={aiConfig?.has_gemini_key ? "Ключ установлен. Введите новый для замены" : "AIzaSy..."}
                  value={geminiKeyInput}
                  onChange={e => setGeminiKeyInput(e.target.value)}
                  style={{ paddingRight: 40 }}
                />
                <button
                  type="button"
                  onClick={() => setShowGeminiKey(!showGeminiKey)}
                  style={{
                    position: 'absolute',
                    right: 10,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  {showGeminiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Модель нейросети</label>
              <select
                id="settings-gemini-model"
                className="form-input"
                value={geminiModelInput}
                onChange={e => setGeminiModelInput(e.target.value)}
                style={{ background: 'var(--card-bg)' }}
              >
                {(aiConfig?.available_models && aiConfig.available_models.length > 0) ? (
                  aiConfig.available_models.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))
                ) : (
                  <>
                    <option value="gemini-3.8-flash">Gemini 3.8 Flash (Новейшая быстрая модель 2026)</option>
                    <option value="gemini-3.6-flash">Gemini 3.6 Flash (Стабильная модель)</option>
                    <option value="gemini-3.5-flash">Gemini 3.5 Flash (Проверенная надежная модель)</option>
                    <option value="gemini-flash-latest">Gemini Flash (Latest)</option>
                    <option value="gemini-flash-lite-latest">Gemini Flash-Lite (Latest)</option>
                  </>
                )}
              </select>
            </div>

            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>HTTP / SOCKS5 Прокси для Gemini (необязательно)</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Если доступ к Google API ограничен</span>
              </label>
              <input
                id="settings-gemini-proxy"
                type="text"
                className="form-input"
                placeholder="socks5://127.0.0.1:10808 или http://127.0.0.1:7890 (оставьте пустым, если используете VPN)"
                value={geminiProxyInput}
                onChange={e => setGeminiProxyInput(e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 12, flexWrap: 'wrap' }}>
            <button
              id="btn-save-ai-config"
              type="submit"
              className="btn btn-primary"
              disabled={savingAi}
            >
              {savingAi ? 'Сохранение...' : '💾 Сохранить настройки AI'}
            </button>

            <button
              id="btn-test-ai-connection"
              type="button"
              className="btn btn-secondary"
              onClick={handleTestAi}
              disabled={testingAi}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Zap size={15} color="var(--primary-glow)" />
              {testingAi ? 'Тестирование запроса к Gemini...' : '⚡️ Проверить подключение к Gemini'}
            </button>
          </div>
        </form>

        {/* AI TEST FEEDBACK */}
        {aiTestResult && (
          <div style={{
            marginTop: 18,
            padding: 14,
            borderRadius: 'var(--radius-sm)',
            background: aiTestResult.success ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
            border: `1px solid ${aiTestResult.success ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
          }}>
            {aiTestResult.success ? (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#34d399', fontWeight: 600, fontSize: 14, marginBottom: 8 }}>
                  <CheckCircle2 size={18} />
                  <span>Gemini API работает штатно! Модель: {aiTestResult.model}</span>
                </div>
                {aiTestResult.warning && (
                  <div style={{
                    marginBottom: 10,
                    padding: '8px 12px',
                    borderRadius: 6,
                    background: 'rgba(245, 158, 11, 0.15)',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    color: '#fde047',
                    fontSize: 12,
                    lineHeight: 1.4,
                  }}>
                    ⚠️ {aiTestResult.warning}
                  </div>
                )}
                <div style={{ fontSize: 13, color: 'rgba(255, 255, 255, 0.85)', lineHeight: 1.5 }}>
                  <strong>Результат тестового AI-анализа:</strong>
                  <pre style={{
                    marginTop: 6,
                    padding: 10,
                    borderRadius: 6,
                    background: 'rgba(0, 0, 0, 0.3)',
                    fontSize: 12,
                    color: '#a5f3fc',
                    overflowX: 'auto',
                  }}>
                    {JSON.stringify(aiTestResult.analysis, null, 2)}
                  </pre>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, color: '#fca5a5', fontSize: 13 }}>
                <AlertCircle size={18} color="#f87171" style={{ flexShrink: 0, marginTop: 2 }} />
                <div style={{ flex: 1 }}>
                  <strong style={{ color: '#f87171' }}>Ошибка подключения к Gemini:</strong>
                  <p style={{ marginTop: 4, whiteSpace: 'pre-wrap', lineHeight: 1.4 }}>{aiTestResult.error}</p>
                  <div style={{
                    marginTop: 10,
                    padding: 10,
                    borderRadius: 6,
                    background: 'rgba(0, 0, 0, 0.25)',
                    fontSize: 12,
                    color: 'rgba(255, 255, 255, 0.8)',
                    lineHeight: 1.5,
                  }}>
                    💡 <strong>Рекомендации по устранению:</strong>
                    <ul style={{ paddingLeft: 18, marginTop: 4, display: 'flex', flexDirection: 'column', gap: 3 }}>
                      <li>Если ошибка <strong>503 (High Demand)</strong> или <strong>429 (Quota)</strong> — выберите модель <strong>Gemini 3.6 Flash</strong> или <strong>Gemini 3.5 Flash</strong> и повторите через 15 секунд.</li>
                      <li>Если ошибка сети или ConnectError — включите VPN либо укажите адрес локального прокси в поле выше (например, <code>socks5://127.0.0.1:10808</code>).</li>
                      <li>Убедитесь, что API ключ скопирован корректно из Google AI Studio без лишних пробелов.</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 4. SECURITY & PRIVACY OVERVIEW */}
      <div className="glass-card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <Shield size={22} color="var(--emerald)" />
          <div>
            <h3 style={{ fontSize: 16 }}>Безопасность и шифрование (Zero-Knowledge Session)</h3>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Архитектурные гарантии защиты аккаунта</span>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircle2 size={16} color="var(--emerald)" />
            <span>Сессии Telegram сохраняются в зашифрованном виде (Fernet AES-128-CBC) на вашем диске</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircle2 size={16} color="var(--emerald)" />
            <span>Сессия и 2FA пароли никогда не пишутся в логи и не передаются во внешний интернет</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircle2 size={16} color="var(--emerald)" />
            <span>Response Guard выполняет pre-flight сканирование текста на утечки токенов и ключей</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircle2 size={16} color="var(--emerald)" />
            <span>Данные переписки Telegram не используются для дообучения AI-моделей (API Terms)</span>
          </div>
        </div>
      </div>

      {/* 5. PRIVACY & DATA DELETION */}
      <div className="glass-card" style={{ borderColor: 'rgba(239, 68, 68, 0.3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <h3 style={{ fontSize: 16, color: '#fca5a5' }}>Полное удаление данных (Privacy by Design)</h3>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              Безвозвратное стирание всех сохраненных сообщений, извлеченных фактов памяти, задач и логов
            </p>
          </div>
          <button 
            id="btn-wipe-data"
            className="btn btn-danger"
            onClick={handleWipeData}
          >
            <Trash2 size={16} />
            Стереть все данные
          </button>
        </div>
      </div>
    </div>
  );
};
