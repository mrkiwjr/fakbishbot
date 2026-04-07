import { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import PageHeader from '../components/PageHeader'
import PageBg from '../components/PageBg'

export default function PromoCode() {
  const [revealed, setRevealed] = useState(false)
  const [code, setCode] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleReveal = async () => {
    setLoading(true)
    await new Promise((r) => setTimeout(r, 800))
    setCode('KATANA-X7K9')
    setRevealed(true)
    setLoading(false)
  }

  const handleCopy = async () => {
    if (!code) return
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {}
  }

  return (
    <div className="min-h-screen px-5 pt-14 pb-20 relative overflow-hidden">
      <PageBg />
      <div className="relative z-10">
        <PageHeader title="ПРОМОКОД" subtitle="Один промокод в неделю" />
      </div>

      <div className="relative z-10 flex flex-col items-center mt-10">
        <AnimatePresence mode="wait">
          {!revealed ? (
            <motion.div
              key="get"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full text-center"
            >
              <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-k-red/8 border border-k-red/20 flex items-center justify-center">
                <span className="font-display text-[48px] text-k-red leading-none">券</span>
              </div>
              <p className="text-k-muted text-[14px] mb-8 leading-relaxed">
                Получи персональный промокод<br />на скидку в компьютерном клубе
              </p>
              <button
                onClick={handleReveal}
                disabled={loading}
                className="w-full btn-primary btn-pulse font-display text-[22px] tracking-[0.12em] py-5 rounded-xl disabled:opacity-50 disabled:shadow-none"
              >
                {loading ? '···' : 'ПОЛУЧИТЬ'}
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="show"
              initial={{ opacity: 0, scale: 0.8, filter: 'blur(10px)' }}
              animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="w-full text-center"
            >
              <div className="bg-k-card border border-k-red/20 rounded-2xl px-6 py-8 glow-red">
                <p className="text-k-dim text-[12px] tracking-[0.35em] uppercase mb-4 font-mono">Твой промокод</p>
                <button onClick={handleCopy} className="font-display text-[36px] tracking-[0.18em] block mx-auto mb-4 hover:text-k-red transition-colors">
                  {code}
                </button>
                <AnimatePresence>
                  {copied && (
                    <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-k-red text-[13px] mb-2 font-mono">
                      Скопировано
                    </motion.p>
                  )}
                </AnimatePresence>
                <p className="text-k-dim text-[13px] leading-relaxed">
                  Покажи этот код администратору
                </p>
              </div>

              <button onClick={handleCopy} className="mt-5 bg-k-card border border-k-border px-8 py-3 rounded-xl text-[14px] font-medium active:scale-95 transition-transform">
                {copied ? 'Скопировано' : 'Скопировать код'}
              </button>

              {/* how to use */}
              <div className="mt-8 bg-k-card border border-k-border rounded-2xl px-5 py-5 text-left">
                <p className="text-k-dim text-[11px] tracking-[0.2em] uppercase mb-3 font-mono">Как использовать</p>
                <div className="flex flex-col gap-2.5 text-k-muted text-[14px]">
                  <div className="flex gap-3">
                    <span className="text-k-red font-mono shrink-0 text-[13px]">01</span>
                    <span>Покажи промокод администратору</span>
                  </div>
                  <div className="flex gap-3">
                    <span className="text-k-red font-mono shrink-0 text-[13px]">02</span>
                    <span>Скидка применится к твоему сеансу</span>
                  </div>
                  <div className="flex gap-3">
                    <span className="text-k-red font-mono shrink-0 text-[13px]">03</span>
                    <span>Новый промокод доступен через неделю</span>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

    </div>
  )
}
