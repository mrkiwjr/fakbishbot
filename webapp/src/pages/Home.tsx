import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { useNavigate } from 'react-router-dom'
import Ticker from '../components/Ticker'
import { Send, MessageSquare, X, Shield } from 'lucide-react'
import { api } from '../lib/api'

export default function Home() {
  const navigate = useNavigate()
  const [showFeedback, setShowFeedback] = useState(false)
  const [fio, setFio] = useState('')
  const [comment, setComment] = useState('')
  const [sent, setSent] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)

  useEffect(() => {
    api.checkAdmin()
      .then(() => setIsAdmin(true))
      .catch(() => setIsAdmin(false))
  }, [])

  const handleSend = async () => {
    if (!fio.trim() || !comment.trim()) return
    try {
      await api.submitFeedback(fio.trim(), comment.trim())
      setSent(true)
      setTimeout(() => {
        setSent(false)
        setShowFeedback(false)
        setFio('')
        setComment('')
      }, 2000)
    } catch {
      // fallback
    }
  }

  return (
    <div className="flex flex-col min-h-screen relative overflow-hidden pb-[60px]">
      {/* hero.jpg — full background */}
      <div className="absolute inset-0 pointer-events-none">
        <img src="/images/hero.jpg" alt="" className="w-full h-full object-cover opacity-40" />
        <div
          className="absolute inset-0"
          style={{
            background: `
              linear-gradient(to bottom, rgba(8,8,8,0.3) 0%, rgba(8,8,8,0.5) 40%, rgba(8,8,8,0.85) 70%, #080808 100%),
              radial-gradient(ellipse at 50% 20%, rgba(196,30,30,0.15) 0%, transparent 60%)
            `,
          }}
        />
      </div>

      {/* admin button */}
      {isAdmin && (
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.8 }}
          onClick={() => navigate('/admin')}
          className="absolute top-5 right-5 z-20 w-11 h-11 rounded-full bg-k-card/70 backdrop-blur-md border border-k-border/50 flex items-center justify-center active:scale-90 transition-transform"
        >
          <Shield size={18} className="text-k-red" />
        </motion.button>
      )}

      {/* content */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-8 pt-20 pb-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="text-center mb-6"
        >
          <h1 className="font-display text-[64px] leading-[0.85] tracking-[0.06em] drop-shadow-lg">
            KATANA
          </h1>
          <div className="flex items-center justify-center gap-3 mt-2">
            <div className="h-px w-12 bg-gradient-to-r from-transparent to-k-red/60" />
            <span className="text-k-muted text-[11px] tracking-[0.5em] font-mono uppercase">cyber space</span>
            <div className="h-px w-12 bg-gradient-to-l from-transparent to-k-red/60" />
          </div>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-k-muted text-[15px] text-center leading-relaxed mb-8 max-w-[280px]"
        >
          Компьютерный клуб<br />нового поколения
        </motion.p>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5 }}
          className="inline-flex items-center gap-2.5 bg-k-card/50 backdrop-blur-md rounded-full px-6 py-3 border border-k-border/50"
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
          </span>
          <span className="text-[14px] text-k-muted">
            <span className="text-emerald-400 font-medium">Открыто</span> · 24/7
          </span>
        </motion.div>
      </div>

      {/* bottom */}
      <div className="relative z-10 px-6">
        {/* two buttons row */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.55 }}
          style={{ display: 'flex', gap: '10px', marginBottom: '12px' }}
        >
          <a
            href="https://t.me/katanaistra"
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-2 bg-k-card/50 backdrop-blur-md border border-k-border/50 rounded-2xl active:scale-[0.97] transition-all"
            style={{ padding: '14px 16px' }}
          >
            <Send size={16} className="text-k-red" />
            <span className="font-display text-[15px] tracking-wider">Канал</span>
          </a>
          <button
            onClick={() => setShowFeedback(true)}
            className="flex-1 flex items-center justify-center gap-2 bg-k-card/50 backdrop-blur-md border border-k-border/50 rounded-2xl active:scale-[0.97] transition-all"
            style={{ padding: '14px 16px' }}
          >
            <MessageSquare size={16} className="text-k-red" />
            <span className="font-display text-[15px] tracking-wider">Отзыв</span>
          </button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="flex items-center justify-around py-3 mb-1"
        >
          <Stat val="4" label="Зоны" />
          <Sep />
          <Stat val="30+" label="ПК" />
          <Sep />
          <Stat val="RTX" label="Видео" red />
          <Sep />
          <Stat val="24/7" label="Режим" />
        </motion.div>
      </div>

      <Ticker />

      {/* Feedback modal */}
      <AnimatePresence>
        {showFeedback && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-end justify-center"
            style={{ background: 'rgba(0,0,0,0.7)' }}
            onClick={() => setShowFeedback(false)}
          >
            <motion.div
              initial={{ y: 300 }}
              animate={{ y: 0 }}
              exit={{ y: 300 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              onClick={(e) => e.stopPropagation()}
              className="w-full rounded-t-3xl border-t border-k-border/50"
              style={{ background: '#111111', padding: '24px 20px 100px' }}
            >
              {/* handle */}
              <div style={{ width: '40px', height: '4px', borderRadius: '2px', background: '#333', margin: '0 auto 20px' }} />

              {sent ? (
                <div style={{ textAlign: 'center', padding: '40px 0' }}>
                  <p style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '24px', letterSpacing: '0.05em', marginBottom: '8px' }}>СПАСИБО!</p>
                  <p style={{ color: '#888', fontSize: '14px' }}>Ваш отзыв отправлен</p>
                </div>
              ) : (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <span style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '22px', letterSpacing: '0.05em' }}>ОСТАВИТЬ ОТЗЫВ</span>
                    <button onClick={() => setShowFeedback(false)} style={{ color: '#555', background: 'none', border: 'none', cursor: 'pointer' }}>
                      <X size={22} />
                    </button>
                  </div>

                  <div style={{ marginBottom: '14px' }}>
                    <label style={{ color: '#555', fontSize: '12px', letterSpacing: '0.1em', textTransform: 'uppercase', display: 'block', marginBottom: '6px' }}>ФИО</label>
                    <input
                      type="text"
                      value={fio}
                      onChange={(e) => setFio(e.target.value)}
                      placeholder="Иванов Иван Иванович"
                      className="input-field"
                    />
                  </div>

                  <div style={{ marginBottom: '20px' }}>
                    <label style={{ color: '#555', fontSize: '12px', letterSpacing: '0.1em', textTransform: 'uppercase', display: 'block', marginBottom: '6px' }}>Комментарий</label>
                    <textarea
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      placeholder="Напишите ваш отзыв..."
                      rows={4}
                      className="input-field"
                      style={{ resize: 'none' }}
                    />
                  </div>

                  <button
                    onClick={handleSend}
                    disabled={!fio.trim() || !comment.trim()}
                    className="btn-primary"
                    style={{ width: '100%', fontFamily: "'Bebas Neue', sans-serif", fontSize: '20px', letterSpacing: '0.1em', padding: '14px', borderRadius: '12px', cursor: 'pointer', color: '#fff' }}
                  >
                    ОТПРАВИТЬ
                  </button>
                </>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function Stat({ val, label, red }: { val: string; label: string; red?: boolean }) {
  return (
    <div className="flex flex-col items-center">
      <span className={`font-display text-[20px] leading-none ${red ? 'text-k-red' : ''}`}>{val}</span>
      <span className="text-k-dim text-[9px] tracking-wider uppercase mt-1 font-mono">{label}</span>
    </div>
  )
}

function Sep() {
  return <div className="w-px h-6 bg-k-white/10" />
}
