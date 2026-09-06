const API_BASE = '/api';

export interface TelegramStatus {
  is_connected: boolean;
  mode: string;
  active_mode: string;
  account?: {
    telegram_user_id: string;
    username?: string;
    first_name?: string;
    phone?: string;
    is_simulator: boolean;
  };
  circuit_breaker: {
    is_tripped: boolean;
    reason: string;
    tripped_at: number;
  };
  saved_messages_count?: number;
}

export interface ChatItem {
  id: number;
  telegram_chat_id: string;
  type: string;
  title: string;
  enabled: boolean;
  auto_reply_enabled: boolean;
  summary_enabled: boolean;
}

export interface ContactItem {
  id: number;
  telegram_user_id: string;
  display_name: string;
  username?: string;
  phone?: string;
  category: string;
  ai_mode: string;
  profile_id?: number;
  is_whitelisted: boolean;
  is_blacklisted: boolean;
  notes?: string;
}

export interface RuleItem {
  id: number;
  name: string;
  scope: string;
  subject?: string;
  action: string;
  priority: number;
  conditions: Record<string, any>;
  is_active: boolean;
}

export interface AiProfileItem {
  id: number;
  name: string;
  description?: string;
  system_policy: string;
  style: string;
  max_tokens: number;
  forbidden_topics: string[];
  allowed_actions: string[];
  is_default: boolean;
}

export interface ActionDraft {
  id: number;
  message_id: number;
  chat_id: string;
  chat_title: string;
  sender_id: string;
  sender_name: string;
  incoming_text: string;
  proposed_text: string;
  reason: string;
  created_at: string;
}

export interface MessageItem {
  id: number;
  chat_id: string;
  chat_title: string;
  sender_id: string;
  sender_name: string;
  direction: string;
  text: string;
  created_at: string;
}

export interface AnalysisItem {
  id: number;
  message_id: number;
  sender_name: string;
  intent: string;
  importance: number;
  urgency: number;
  needs_reply: boolean;
  summary: string;
  topics: string[];
  action_items: string[];
  created_at: string;
}

export interface TaskItem {
  id: number;
  contact_id?: number;
  title: string;
  status: string;
  due_at?: string;
}

export interface SavedMessageItem {
  id: string;
  text: string;
  timestamp: string;
  type: string;
}

export interface CategoryItem {
  id: string;
  name: string;
  color: string;
  icon?: string;
  description: string;
  prompt_instruction: string;
  is_custom: boolean;
  contact_count?: number;
}

export interface AiConfigItem {
  provider: string;
  gemini_model: string;
  gemini_proxy?: string;
  has_gemini_key: boolean;
  gemini_key_masked: string;
  available_models: { id: string; name: string }[];
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export const api = {
  // Telegram status & mode
  getStatus: () => request<TelegramStatus>('/telegram/status'),
  switchMode: (mode: string) => request<TelegramStatus>('/telegram/switch-mode', {
    method: 'POST',
    body: JSON.stringify({ mode }),
  }),
  disconnectTelegram: () => request<{ status: string }>('/telegram/disconnect', { method: 'POST' }),
  connectTelegram: (payload: any) => request<any>('/telegram/connect', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),

  // Categories
  getCategories: () => request<CategoryItem[]>('/categories'),
  createCategory: (cat: Partial<CategoryItem>) => request<CategoryItem>('/categories', {
    method: 'POST',
    body: JSON.stringify(cat),
  }),
  deleteCategory: (id: string) => request<any>(`/categories/${id}`, { method: 'DELETE' }),

  // AI & Gemini
  getAiConfig: () => request<AiConfigItem>('/ai/config'),
  saveAiConfig: (data: { gemini_api_key?: string; gemini_model?: string; gemini_proxy?: string; provider?: string }) => request<any>('/ai/config', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  testAiConnection: (data: { gemini_api_key?: string; gemini_model?: string; gemini_proxy?: string }) => request<any>('/ai/test', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // Chats
  getChats: () => request<ChatItem[]>('/chats'),
  updateChat: (id: number, data: Partial<ChatItem>) => request<ChatItem>(`/chats/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  // Contacts
  getContacts: () => request<ContactItem[]>('/contacts'),
  syncContacts: () => request<{
    success: boolean;
    total_fetched: number;
    added: number;
    updated: number;
    message: string;
  }>('/contacts/sync', { method: 'POST' }),
  getContactDetails: (id: number) => request<any>(`/contacts/${id}/details`),
  updateContact: (id: number, data: Partial<ContactItem>) => request<ContactItem>(`/contacts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  // Rules
  getRules: () => request<RuleItem[]>('/rules'),
  createRule: (rule: Partial<RuleItem>) => request<RuleItem>('/rules', {
    method: 'POST',
    body: JSON.stringify(rule),
  }),
  updateRule: (id: number, rule: Partial<RuleItem>) => request<RuleItem>(`/rules/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(rule),
  }),
  deleteRule: (id: number) => request<any>(`/rules/${id}`, { method: 'DELETE' }),

  // AI Profiles
  getProfiles: () => request<AiProfileItem[]>('/ai-profiles'),
  createProfile: (prof: Partial<AiProfileItem>) => request<AiProfileItem>('/ai-profiles', {
    method: 'POST',
    body: JSON.stringify(prof),
  }),
  updateProfile: (id: number, prof: Partial<AiProfileItem>) => request<AiProfileItem>(`/ai-profiles/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(prof),
  }),
  getAiProfiles: () => request<AiProfileItem[]>('/ai-profiles'),
  createAiProfile: (profile: Partial<AiProfileItem>) => request<AiProfileItem>('/ai-profiles', {
    method: 'POST',
    body: JSON.stringify(profile),
  }),
  updateAiProfile: (id: number, profile: Partial<AiProfileItem>) => request<AiProfileItem>(`/ai-profiles/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(profile),
  }),

  // Messages & Analysis
  getMessages: () => request<MessageItem[]>('/messages'),
  getAnalyses: () => request<AnalysisItem[]>('/analyses'),
  getAuditLogs: () => request<any[]>('/audit-logs'),
  getTasks: () => request<TaskItem[]>('/tasks'),
  toggleTask: (id: number) => request<TaskItem>(`/tasks/${id}/toggle`, { method: 'POST' }),

  // Actions (Draft Approval)
  getPendingActions: () => request<ActionDraft[]>('/actions/pending'),
  approveAction: (id: number, edited_text?: string) => request<any>(`/actions/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ edited_text }),
  }),
  rejectAction: (id: number, reason?: string) => request<any>(`/actions/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  }),

  // Summaries & Saved Messages
  runSummary: (title?: string) => request<any>('/summaries/run', {
    method: 'POST',
    body: JSON.stringify({ title }),
  }),
  getSavedMessages: () => request<SavedMessageItem[]>('/saved-messages'),

  // Simulator
  sendSimulatedMessage: (payload: {
    chat_id: string;
    sender_id: string;
    sender_name: string;
    text: string;
    chat_title?: string;
  }) => request<any>('/simulator/send', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  resetCircuitBreaker: () => request<any>('/simulator/circuit-breaker/reset', { method: 'POST' }),
  wipeAllData: () => request<any>('/privacy/wipe', { method: 'POST' }),
};
