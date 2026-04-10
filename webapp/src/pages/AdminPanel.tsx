import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { useNavigate } from 'react-router-dom'
import {
  Plus, List, History, BarChart3, Send,
  Users, Trash2, X, ChevronRight, Loader2, Check, AlertCircle
} from 'lucide-react'
import { api } from '../lib/api'
import type { Stats, Promo, PromoHistoryEntry, Admin, User } from '../lib/api'
import PageBg from '../components/PageBg'
import PageHeader from '../components/PageHeader'

type Section = 'menu' | 'add_promo' | 'promos' | 'history' | 'stats' | 'users' | 'broadcast' | 'admins'

export default function AdminPanel() {
  const navigate = useNavigate()
  const [section, setSection] = useState<Section>('menu')
  const [isSuperAdmin, setIsSuperAdmin] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [stats, setStats] = useState<Stats | null>(null)
  const [promos, setPromos] = useState<Promo[]>([])
  const [history, setHistory] = useState<PromoHistoryEntry[]>([])
  const [admins, setAdmins] = useState<Admin[]>([])
  const [users, setUsers] = useState<User[]>([])

  const [promoCode, setPromoCode] = useState('')
  const [promoDays, setPromoDays] = useState('7')
  const [broadcastText, setBroadcastText] = useState('')
  const [broadcastPhoto, setBroadcastPhoto] = useState<File | null>(null)
  const [broadcastPhotoPreview, setBroadcastPhotoPreview] = useState('')
  const [broadcastVideo, setBroadcastVideo] = useState<File | null>(null)
  const [broadcastVideoName, setBroadcastVideoName] = useState('')
  const [broadcastSchedule, setBroadcastSchedule] = useState('')
  const [broadcastConfirm, setBroadcastConfirm] = useState(false)
  const [adminUsername, setAdminUsername] = useState('')

  useEffect(() => {
    api.checkAdmin()
      .then(r => setIsSuperAdmin(r.is_super_admin))
      .catch(() => navigate('/'))
  }, [navigate])

  const clearMessages = () => { setError(''); setSuccess('') }

  const loadStats = useCallback(async () => {
    setLoading(true)
    clearMessages()
    try {
      setStats(await api.getStats())
      setSection('stats')
    } catch (e: any) { setError(e.message) }
    setLoading(false)
  }, [])

  const loadPromos = useCallback(async () => {
    setLoading(true)
    clearMessages()
    try {
      const r = await api.getPromos()
      setPromos(r.promos)
      setSection('promos')
    } catch (e: any) { setError(e.message) }
    setLoading(false)
  }, [])

  const loadHistory = useCallback(async () => {
    setLoading(true)
    clearMessages()
    try {
      const r = await api.getPromoHistory()
      setHistory(r.history)
      setSection('history')
    } catch (e: any) { setError(e.message) }
    setLoading(false)
  }, [])

  const loadUsers = useCallback(async () => {
    setLoading(true)
    clearMessages()
    try {
      const r = await api.getUsers()
      setUsers(r.users)
      setSection('users')
    } catch (e: any) { setError(e.message) }
    setLoading(false)
  }, [])

  const loadAdmins = useCallback(async () => {
    setLoading(true)
    clearMessages()
    try {
      const r = await api.getAdmins()
      setAdmins(r.admins)
      setSection('admins')
    } catch (e: any) { setError(e.message) }
    setLoading(false)
  }, [])

  const handleAddPromo = async () => {
    if (!promoCode.trim()) return
    const days = parseInt(promoDays)
    if (isNaN(days) || days < 1 || days > 365) {
      setError('Дни: 1-365')
      return
    }
    setLoading(true)
    clearMessages()
    try {
      await api.addPromo(promoCode.trim(), days)
      setSuccess(`Промокод "${promoCode.trim()}" создан`)
      setPromoCode('')
      setPromoDays('7')
    } catch (e: any) { setError(e.message) }
    setLoading(false)
  }

  const handleDeletePromo = async (code: string) => {
    setLoading(true)
    clearMessages()
    try {
      await api.deletePromo(code)
      setPromos(prev => prev.filter(p => p.code !== code))
      setSuccess(`Промокод "${code}" удален`)
    } catch (e: any) { setError(e.message) }
    setLoading(false)
  }

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setBroadcastPhoto(file)
    const url = URL.createObjectURL(file)
    setBroadcastPhotoPreview(url)
  }

  const handleRemovePhoto = () => {
    setBroadcastPhoto(null)
    if (broadcastPhotoPreview) URL.revokeObjectURL(broadcastPhotoPreview)
    setBroadcastPhotoPreview('')
  }

  const handleVideoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setBroadcastVideo(file)
    setBroadcastVideoName(file.name)
    handleRemovePhoto()
  }

  const handleRemoveVideo = () => {
    setBroadcastVideo(null)
    setBroadcastVideoName('')
  }

  const handleBroadcast = async () => {
    if (!broadcastText.trim()) return
    setLoading(true)
    clearMessages()
    try {
      const r = await api.broadcast(
        broadcastText.trim(),
        broadcastPhoto || undefined,
        broadcastVideo || undefined,
        broadcastSchedule || undefined
      )
      if (r.scheduled) {
        setSuccess(`Рассылка запланирована на ${r.schedule_at}`)
      } else {
        setSuccess(`Отправлено: ${r.sent}, ошибок: ${r.failed}`)
      }
      setBroadcastText('')
      handleRemovePhoto()
      handleRemoveVideo()
      setBroadcastSchedule('')
      setBroadcastConfirm(false)
    } catch (e: any) { setError(e.message) }
    setLoading(false)
  }

  const handleAddAdmin = async () => {
    if (!adminUsername.trim()) return
    setLoading(true)
    clearMessages()
    try {
      await api.addAdmin(adminUsername.trim())
      setSuccess('Администратор добавлен')
      setAdminUsername('')
      loadAdmins()
    } catch (e: any) { setError(e.message) }
    setLoading(false)
  }

  const handleRemoveAdmin = async (userId: number) => {
    setLoading(true)
    clearMessages()
    try {
      await api.removeAdmin(userId)
      setAdmins(prev => prev.filter(a => a.user_id !== userId))
      setSuccess('Администратор удален')
    } catch (e: any) { setError(e.message) }
    setLoading(false)
  }

  const goBack = () => {
    clearMessages()
    if (section === 'menu') navigate('/')
    else {
      setSection('menu')
      setBroadcastConfirm(false)
    }
  }

  return (
    <div className="min-h-screen pb-[60px]">
      <PageBg />
      <div className="relative z-10" style={{ paddingTop: '20px', paddingLeft: '24px', paddingRight: '24px' }}>
        {/* Header */}
        <PageHeader
          title={section === 'menu' ? 'ADMIN PANEL' : section.toUpperCase().replace('_', ' ')}
          subtitle={section === 'menu' ? 'Management' : undefined}
          onBack={goBack}
        />

        {/* Messages */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-2"
            >
              <AlertCircle size={16} className="text-red-400 shrink-0" />
              <span className="text-red-300 text-[13px]">{error}</span>
              <button onClick={() => setError('')} className="ml-auto"><X size={14} className="text-red-400" /></button>
            </motion.div>
          )}
          {success && (
            <motion.div
              initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-2"
            >
              <Check size={16} className="text-emerald-400 shrink-0" />
              <span className="text-emerald-300 text-[13px]">{success}</span>
              <button onClick={() => setSuccess('')} className="ml-auto"><X size={14} className="text-emerald-400" /></button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading */}
        {loading && (
          <div className="flex justify-center py-8">
            <Loader2 size={24} className="text-k-red animate-spin" />
          </div>
        )}

        {/* Sections */}
        {!loading && (
          <AnimatePresence mode="wait">
            <motion.div
              key={section}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
              {section === 'menu' && <Menu
                isSuperAdmin={isSuperAdmin}
                onNavigate={(s) => {
                  clearMessages()
                  if (s === 'stats') loadStats()
                  else if (s === 'promos') loadPromos()
                  else if (s === 'history') loadHistory()
                  else if (s === 'admins') loadAdmins()
                  else if (s === 'users') loadUsers()
                  else setSection(s)
                }}
              />}

              {section === 'add_promo' && (
                <div className="space-y-4">
                  <SectionTitle title="ДОБАВИТЬ ПРОМОКОД" />
                  <div>
                    <Label text="Промокод" />
                    <input
                      className="input-field" placeholder="KATANA-2025"
                      value={promoCode} onChange={e => setPromoCode(e.target.value)}
                      maxLength={100}
                    />
                  </div>
                  <div>
                    <Label text="Дней действия" />
                    <input
                      className="input-field" type="number" placeholder="7"
                      value={promoDays} onChange={e => setPromoDays(e.target.value)}
                      min={1} max={365}
                    />
                  </div>
                  <button onClick={handleAddPromo} disabled={!promoCode.trim()}
                    className="btn-primary w-full py-3 rounded-xl font-display text-[18px] tracking-wider text-white cursor-pointer">
                    СОЗДАТЬ
                  </button>
                </div>
              )}

              {section === 'promos' && (
                <div className="space-y-3">
                  <SectionTitle title="ПРОМОКОДЫ" count={promos.length} />
                  {promos.length === 0 && <EmptyState text="Промокодов нет" />}
                  {promos.map(p => (
                    <div key={p.code} className="bg-k-card/60 border border-k-border/50 rounded-xl p-3 flex items-center gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${p.active ? 'bg-emerald-400' : 'bg-red-400'}`} />
                          <span className="font-mono text-[13px] truncate">{p.code}</span>
                        </div>
                        <p className="text-k-dim text-[11px] mt-1">
                          до {p.expiry_date} &middot; {p.created_at.split(' ')[0]}
                        </p>
                      </div>
                      <button onClick={() => handleDeletePromo(p.code)}
                        className="p-2 rounded-lg bg-red-500/10 border border-red-500/20 active:scale-95 transition-transform">
                        <Trash2 size={14} className="text-red-400" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {section === 'history' && (
                <div className="space-y-3">
                  <SectionTitle title="ИСТОРИЯ ВЫДАЧИ" count={history.length} />
                  {history.length === 0 && <EmptyState text="История пуста" />}
                  {history.slice(0, 50).map((h, i) => (
                    <div key={i} className="bg-k-card/60 border border-k-border/50 rounded-xl p-3">
                      <div className="flex justify-between items-start">
                        <span className="font-mono text-[13px] text-k-red">{h.promo_code}</span>
                        <span className="text-k-dim text-[10px] font-mono">{h.received_at}</span>
                      </div>
                      <p className="text-[12px] text-k-muted mt-1">
                        {h.first_name} {h.username ? `(@${h.username})` : ''}
                        <span className="text-k-dim"> &middot; ID: {h.user_id}</span>
                      </p>
                      <p className="text-k-dim text-[10px] mt-0.5">до {h.expiry_date}</p>
                    </div>
                  ))}
                </div>
              )}

              {section === 'stats' && stats && (
                <div className="flex flex-col items-center justify-center" style={{ minHeight: 'calc(100vh - 200px)' }}>
                  <SectionTitle title="СТАТИСТИКА" />
                  <div className="grid grid-cols-2 gap-3 w-full mt-3">
                    <StatCard label="Пользователей" value={stats.users_count} />
                    <StatCard label="Всего промокодов" value={stats.total_promos} />
                    <StatCard label="Активных" value={stats.active_promos} color="emerald" />
                    <StatCard label="Неиспользованных" value={stats.unused_active_promos} color="orange" />
                    <StatCard label="Выдано" value={stats.total_issued} color="red" />
                  </div>
                  <button onClick={loadUsers}
                    className="w-full mt-4 py-3 rounded-xl bg-k-card/60 border border-k-border/50 font-display text-[16px] tracking-wider active:scale-[0.98] transition-transform cursor-pointer">
                    КТО ЕСТЬ КТО
                  </button>
                </div>
              )}

              {section === 'users' && (
                <div className="space-y-3">
                  <SectionTitle title="ПОЛЬЗОВАТЕЛИ" count={users.length} />
                  {users.length === 0 && <EmptyState text="Нет пользователей" />}
                  {users.map(u => (
                    <div key={u.user_id} className="bg-k-card/60 border border-k-border/50 rounded-xl p-3">
                      <div className="flex justify-between items-start">
                        <span className="text-[13px] font-medium">{u.first_name}</span>
                        <span className="text-k-dim text-[10px] font-mono">{u.joined_at?.split(' ')[0]}</span>
                      </div>
                      <p className="text-k-dim text-[11px] mt-0.5">
                        {u.username ? `@${u.username}` : 'no username'} &middot; ID: {u.user_id}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {section === 'broadcast' && (
                <div className="flex flex-col justify-center space-y-4 text-center" style={{ minHeight: 'calc(100vh - 200px)' }}>
                  <SectionTitle title="РАССЫЛКА" />
                  {!broadcastConfirm ? (
                    <>
                      <div>
                        <Label text="Текст сообщения" />
                        <textarea
                          className="input-field" rows={5}
                          placeholder="Текст рассылки..."
                          value={broadcastText} onChange={e => setBroadcastText(e.target.value)}
                          style={{ resize: 'none' }}
                        />
                      </div>
                      <div>
                        <Label text="Медиа (необязательно)" />
                        {broadcastPhotoPreview ? (
                          <div className="relative inline-block w-full">
                            <img src={broadcastPhotoPreview} alt="" className="w-full max-h-48 object-cover rounded-xl border border-k-border/50" />
                            <button onClick={handleRemovePhoto}
                              className="absolute top-2 right-2 w-7 h-7 rounded-full bg-k-black/80 border border-k-border flex items-center justify-center">
                              <X size={14} className="text-k-muted" />
                            </button>
                          </div>
                        ) : broadcastVideoName ? (
                          <div className="flex items-center gap-3 p-3 rounded-xl bg-k-card/60 border border-k-border/50">
                            <span className="text-[13px] truncate flex-1">{broadcastVideoName}</span>
                            <button onClick={handleRemoveVideo}
                              className="w-7 h-7 rounded-full bg-k-black/80 border border-k-border flex items-center justify-center shrink-0">
                              <X size={14} className="text-k-muted" />
                            </button>
                          </div>
                        ) : (
                          <div className="flex gap-2">
                            <label className="flex-1 py-4 rounded-xl bg-k-card/60 border border-k-border/50 border-dashed cursor-pointer active:scale-[0.98] transition-transform text-center">
                              <input type="file" accept="image/*" onChange={handlePhotoSelect} className="hidden" />
                              <p className="text-k-dim text-[13px]">Фото</p>
                            </label>
                            <label className="flex-1 py-4 rounded-xl bg-k-card/60 border border-k-border/50 border-dashed cursor-pointer active:scale-[0.98] transition-transform text-center">
                              <input type="file" accept="video/*" onChange={handleVideoSelect} className="hidden" />
                              <p className="text-k-dim text-[13px]">Видео</p>
                            </label>
                          </div>
                        )}
                      </div>
                      <div>
                        <Label text="Запланировать (необязательно)" />
                        <input
                          type="datetime-local"
                          className="input-field [color-scheme:dark]"
                          value={broadcastSchedule}
                          onChange={e => setBroadcastSchedule(e.target.value)}
                        />
                      </div>
                      <button
                        onClick={() => broadcastText.trim() && setBroadcastConfirm(true)}
                        disabled={!broadcastText.trim()}
                        className="btn-primary w-full py-3 rounded-xl font-display text-[18px] tracking-wider text-white cursor-pointer"
                      >
                        ДАЛЕЕ
                      </button>
                    </>
                  ) : (
                    <>
                      <div className="bg-k-card/60 border border-k-border/50 rounded-xl p-4">
                        <p className="text-k-dim text-[11px] font-mono tracking-wider mb-2">ПРЕДПРОСМОТР</p>
                        {broadcastPhotoPreview && (
                          <img src={broadcastPhotoPreview} alt="" className="w-full max-h-48 object-cover rounded-lg mb-3" />
                        )}
                        {broadcastVideoName && (
                          <p className="text-k-muted text-[12px] mb-3">Видео: {broadcastVideoName}</p>
                        )}
                        <p className="text-[13px] whitespace-pre-wrap text-left">{broadcastText}</p>
                        {broadcastSchedule && (
                          <p className="text-k-orange text-[12px] mt-3">Запланировано: {broadcastSchedule.replace('T', ' ')}</p>
                        )}
                      </div>
                      <div className="flex gap-3">
                        <button onClick={() => setBroadcastConfirm(false)}
                          className="flex-1 py-3 rounded-xl bg-k-card border border-k-border text-center font-display text-[16px] tracking-wider cursor-pointer">
                          НАЗАД
                        </button>
                        <button onClick={handleBroadcast}
                          className="btn-primary flex-1 py-3 rounded-xl font-display text-[16px] tracking-wider text-white cursor-pointer">
                          {broadcastSchedule ? 'ЗАПЛАНИРОВАТЬ' : 'ОТПРАВИТЬ'}
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}

              {section === 'admins' && (
                <div className="space-y-4">
                  <SectionTitle title="АДМИНИСТРАТОРЫ" />
                  <div className="flex gap-2">
                    <input
                      className="input-field flex-1"
                      placeholder="@username"
                      value={adminUsername} onChange={e => setAdminUsername(e.target.value)}
                    />
                    <button onClick={handleAddAdmin} disabled={!adminUsername.trim()}
                      className="btn-primary px-4 rounded-xl text-white cursor-pointer">
                      <Plus size={18} />
                    </button>
                  </div>
                  {admins.length === 0 && <EmptyState text="Дополнительных администраторов нет" />}
                  {admins.map(a => (
                    <div key={a.user_id} className="bg-k-card/60 border border-k-border/50 rounded-xl p-3 flex items-center gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-[13px] font-medium">{a.first_name}</p>
                        <p className="text-k-dim text-[11px]">
                          {a.username ? `@${a.username}` : 'no username'} &middot; ID: {a.user_id}
                        </p>
                        <p className="text-k-dim text-[10px]">Добавлен: {a.added_at}</p>
                      </div>
                      <button onClick={() => handleRemoveAdmin(a.user_id)}
                        className="p-2 rounded-lg bg-red-500/10 border border-red-500/20 active:scale-95 transition-transform">
                        <Trash2 size={14} className="text-red-400" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </div>
    </div>
  )
}


function Menu({ isSuperAdmin, onNavigate }: { isSuperAdmin: boolean; onNavigate: (s: Section) => void }) {
  const items: { icon: typeof Plus; label: string; section: Section; desc: string }[] = [
    { icon: Plus, label: 'Добавить промокод', section: 'add_promo', desc: 'Создать новый промокод' },
    { icon: List, label: 'Список промокодов', section: 'promos', desc: 'Просмотр и удаление' },
    { icon: History, label: 'История выдачи', section: 'history', desc: 'Кто получил промокоды' },
    { icon: BarChart3, label: 'Статистика', section: 'stats', desc: 'Показатели бота' },
    { icon: Send, label: 'Рассылка', section: 'broadcast', desc: 'Отправить всем' },
  ]

  if (isSuperAdmin) {
    items.push({ icon: Users, label: 'Управление админами', section: 'admins', desc: 'Добавить / удалить' })
  }

  return (
    <div className="flex flex-col gap-3" style={{ minHeight: 'calc(100vh - 160px)' }}>
      {items.map((item, i) => (
        <motion.button
          key={item.section}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          onClick={() => onNavigate(item.section)}
          className="flex-1 w-full flex items-center gap-4 bg-k-card/60 border border-k-border/50 rounded-2xl px-5 active:scale-[0.98] transition-transform text-left"
        >
          <div className="p-2.5 rounded-xl bg-k-red/10 border border-k-red/20">
            <item.icon size={20} className="text-k-red" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[15px] font-medium">{item.label}</p>
            <p className="text-k-dim text-[11px]">{item.desc}</p>
          </div>
          <ChevronRight size={16} className="text-k-dim" />
        </motion.button>
      ))}
    </div>
  )
}


function SectionTitle({ title, count }: { title: string; count?: number }) {
  return (
    <div className="flex items-center justify-between mb-1">
      <h2 className="font-display text-[20px] tracking-wider">{title}</h2>
      {count !== undefined && (
        <span className="text-k-dim text-[12px] font-mono">{count}</span>
      )}
    </div>
  )
}

function Label({ text }: { text: string }) {
  return (
    <label className="block text-k-dim text-[11px] tracking-[0.1em] uppercase mb-1.5">
      {text}
    </label>
  )
}

function StatCard({ label, value, color }: { label: string; value: number; color?: string }) {
  const colorMap: Record<string, string> = {
    emerald: 'text-emerald-400',
    orange: 'text-k-orange',
    red: 'text-k-red',
  }
  return (
    <div className="bg-k-card/60 border border-k-border/50 rounded-xl p-4 text-center">
      <p className={`font-display text-[28px] leading-none ${colorMap[color || ''] || ''}`}>{value}</p>
      <p className="text-k-dim text-[11px] mt-1 font-mono tracking-wider uppercase">{label}</p>
    </div>
  )
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="text-center py-8">
      <p className="text-k-dim text-[13px]">{text}</p>
    </div>
  )
}
