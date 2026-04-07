import { useState } from 'react'
import { motion } from 'motion/react'
import PageHeader from '../components/PageHeader'
import PageBg from '../components/PageBg'
import { api } from '../lib/api'

const zones = ['NORM', 'DUO', 'ULTRA', 'VIP', 'STREET', 'LOFT']
const durations = ['1 час', '3 часа', '5 часов', 'Ночь']

export default function Booking() {
  const [zone, setZone] = useState('')
  const [duration, setDuration] = useState('')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  if (submitted) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center relative overflow-hidden" style={{ padding: '20px' }}>
        <PageBg />
        <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="relative z-10 text-center">
          <h2 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '32px', letterSpacing: '0.05em', marginBottom: '10px' }}>ЗАЯВКА ПРИНЯТА</h2>
          <p style={{ color: '#888', fontSize: '14px', marginBottom: '30px' }}>Мы свяжемся для подтверждения</p>
          <div style={{ width: '60px', height: '60px', borderRadius: '50%', background: 'rgba(196,30,30,0.1)', border: '1px solid rgba(196,30,30,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 30px' }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#c41e1e" strokeWidth="2.5"><path d="M20 6L9 17l-5-5"/></svg>
          </div>
          <button
            onClick={() => { setSubmitted(false); setZone(''); setDuration(''); setName(''); setPhone(''); setDate(''); setTime('') }}
            className="bg-k-card border border-k-border active:scale-95 transition-transform"
            style={{ padding: '16px 40px', borderRadius: '16px', fontSize: '16px', fontFamily: "'Bebas Neue', sans-serif", letterSpacing: '0.08em', cursor: 'pointer', color: '#f0f0f0' }}
          >
            НОВАЯ БРОНЬ
          </button>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col relative" style={{ paddingTop: '20px', paddingLeft: '16px', paddingRight: '16px', paddingBottom: '120px' }}>
      <PageBg />
      <div className="relative z-10">
        <PageHeader title="БРОНЬ" subtitle="Забронируй место" />
      </div>

      <div className="relative z-10 flex flex-col gap-5 flex-1">
        <Field label="Зона">
          <div className="grid grid-cols-3 gap-2">
            {zones.map((z) => (
              <Chip key={z} active={zone === z} onClick={() => setZone(z)}>{z}</Chip>
            ))}
          </div>
        </Field>

        <Field label="Длительность">
          <div className="grid grid-cols-4 gap-2">
            {durations.map((d) => (
              <Chip key={d} active={duration === d} onClick={() => setDuration(d)} small>{d}</Chip>
            ))}
          </div>
        </Field>

        <Field label="Дата">
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="input-field [color-scheme:dark]" />
        </Field>

        <Field label="Время">
          <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className="input-field [color-scheme:dark]" />
        </Field>

        <Field label="Имя">
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Как вас зовут" className="input-field" />
        </Field>

        <Field label="Телефон">
          <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+7 (___) ___-__-__" className="input-field" />
        </Field>

        {error && (
          <motion.p
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ color: '#e53535', fontSize: '13px', textAlign: 'center', padding: '10px 0 0' }}
          >
            {error}
          </motion.p>
        )}

        <button
          onClick={handleSubmit}
          className="w-full btn-primary font-display text-[20px] tracking-wider rounded-xl mt-1"
          style={{ padding: '16px', cursor: 'pointer', color: '#fff' }}
        >
          ЗАБРОНИРОВАТЬ
        </button>
      </div>

    </div>
  )

  async function handleSubmit() {
    if (!zone || !duration || !date || !time || !name || !phone) {
      setError('Пожалуйста, укажите все поля для бронирования')
      setTimeout(() => setError(''), 3000)
      return
    }
    setError('')
    try {
      await api.submitBooking({ zone, duration, date, time, name, phone })
      setSubmitted(true)
    } catch {
      setError('Ошибка отправки. Попробуйте позже')
      setTimeout(() => setError(''), 3000)
    }
  }
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-k-dim text-[12px] tracking-wider uppercase block mb-1.5">{label}</label>
      {children}
    </div>
  )
}

function Chip({ children, active, onClick, small }: { children: React.ReactNode; active: boolean; onClick: () => void; small?: boolean }) {
  return (
    <button
      onClick={onClick}
      className={`${small ? 'py-2.5 text-[12px]' : 'py-3 text-[13px]'} rounded-xl font-medium transition-all active:scale-95 ${
        active
          ? 'bg-k-red text-white glow-red'
          : 'bg-k-card border border-k-border text-k-muted'
      }`}
    >
      {children}
    </button>
  )
}
