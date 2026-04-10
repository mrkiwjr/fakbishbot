const API_BASE = import.meta.env.VITE_API_URL || ''

const DEV_MODE = import.meta.env.DEV

function getInitData(): string {
  if (DEV_MODE) return 'dev'
  try {
    return window.Telegram?.WebApp?.initData || ''
  } catch {
    return ''
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': getInitData(),
      ...options.headers,
    },
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${res.status}`)
  }

  return res.json()
}

export interface Stats {
  users_count: number
  total_promos: number
  active_promos: number
  unused_active_promos: number
  total_issued: number
}

export interface Promo {
  code: string
  expiry_date: string
  created_at: string
  active: number
}

export interface PromoHistoryEntry {
  promo_code: string
  user_id: number
  first_name: string
  username: string | null
  received_at: string
  expiry_date: string
}

export interface Admin {
  user_id: number
  first_name: string
  username: string | null
  added_at: string
  added_by: number
}

export interface User {
  user_id: number
  first_name: string
  username: string | null
  joined_at: string
}

export const api = {
  checkAdmin: () =>
    request<{ is_admin: boolean; is_super_admin: boolean }>('/api/admin/check'),

  getStats: () =>
    request<Stats>('/api/admin/stats'),

  getPromos: () =>
    request<{ promos: Promo[] }>('/api/admin/promos'),

  addPromo: (code: string, days: number) =>
    request<{ success: boolean }>('/api/admin/promos', {
      method: 'POST',
      body: JSON.stringify({ code, days }),
    }),

  deletePromo: (code: string) =>
    request<{ success: boolean }>(`/api/admin/promos/${encodeURIComponent(code)}`, {
      method: 'DELETE',
    }),

  getPromoHistory: () =>
    request<{ history: PromoHistoryEntry[] }>('/api/admin/promo-history'),

  getUsers: () =>
    request<{ users: User[] }>('/api/admin/users'),

  broadcast: (text: string, photo?: File, video?: File, scheduleAt?: string) => {
    const formData = new FormData()
    formData.append('text', text)
    if (photo) formData.append('photo', photo)
    if (video) formData.append('video', video)
    if (scheduleAt) formData.append('schedule_at', scheduleAt)

    return fetch(`${API_BASE}/api/admin/broadcast`, {
      method: 'POST',
      headers: { 'X-Telegram-Init-Data': getInitData() },
      body: formData,
    }).then(async res => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error || `HTTP ${res.status}`)
      }
      return res.json() as Promise<{ sent: number; failed: number; scheduled?: boolean; schedule_at?: string }>
    })
  },

  getAdmins: () =>
    request<{ admins: Admin[]; super_admin_id: number }>('/api/admin/admins'),

  addAdmin: (username: string) =>
    request<{ success: boolean }>('/api/admin/admins', {
      method: 'POST',
      body: JSON.stringify({ username }),
    }),

  removeAdmin: (userId: number) =>
    request<{ success: boolean }>(`/api/admin/admins/${userId}`, {
      method: 'DELETE',
    }),

  submitBooking: (data: { zone: string; duration: string; date: string; time: string; name: string; phone: string }) =>
    request<{ success: boolean }>('/api/booking', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  submitFeedback: (fio: string, comment: string) =>
    request<{ success: boolean }>('/api/feedback', {
      method: 'POST',
      body: JSON.stringify({ fio, comment }),
    }),
}
