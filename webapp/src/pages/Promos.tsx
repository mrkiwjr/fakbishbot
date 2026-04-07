import { motion } from 'motion/react'
import PageHeader from '../components/PageHeader'
import PageBg from '../components/PageBg'

export default function Promos() {
  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden" style={{ paddingTop: '20px', paddingLeft: '16px', paddingRight: '16px', paddingBottom: '100px' }}>
      <PageBg />

      <div className="relative z-10">
        <PageHeader title="АКЦИИ" subtitle="Специальные предложения" />
      </div>

      <div className="relative z-10 flex flex-col flex-1">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl overflow-hidden border border-k-red/25 backdrop-blur-sm flex-1 flex flex-col"
        >
          {/* header */}
          <div className="bg-k-red/10 flex items-center justify-between" style={{ padding: '14px 24px' }}>
            <span style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '20px', letterSpacing: '0.05em', color: '#f0f0f0' }}>СЕЙФ КАТАНЫ</span>
            <span className="bg-k-red font-bold uppercase" style={{ fontSize: '10px', letterSpacing: '0.05em', padding: '4px 10px', borderRadius: '8px' }}>Главный приз</span>
          </div>

          {/* stats */}
          <div className="bg-k-dark/70">
            <div className="flex justify-between items-center border-b border-k-border/40" style={{ padding: '16px 24px' }}>
              <span style={{ color: '#888', fontSize: '14px' }}>Стартовый банк</span>
              <span style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '22px', color: '#c41e1e' }}>15 000 ₽</span>
            </div>
            <div className="flex justify-between items-center border-b border-k-border/40" style={{ padding: '16px 24px' }}>
              <span style={{ color: '#888', fontSize: '14px' }}>Несгораемый минимум</span>
              <span style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '22px', color: '#d4872a' }}>5 000 ₽</span>
            </div>
            <div className="flex justify-between items-center border-b border-k-border/40" style={{ padding: '16px 24px' }}>
              <span style={{ color: '#888', fontSize: '14px' }}>Уменьшение за ночь</span>
              <span style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '22px', color: '#555' }}>−500 ₽</span>
            </div>
          </div>

          {/* description */}
          <div className="bg-k-card/70" style={{ padding: '16px 24px' }}>
            <p style={{ color: '#888', fontSize: '13px', lineHeight: '1.6' }}>
              Каждую ночь без победителя сумма уменьшается на 500 ₽. Чем дольше тянешь — тем меньше заберёшь.
            </p>
          </div>

          {/* mechanics */}
          <div className="bg-k-dark/50 flex-1" style={{ padding: '20px 24px' }}>
            <p style={{ color: '#555', fontSize: '11px', letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '16px', fontFamily: "'JetBrains Mono', monospace" }}>Механика</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {[
                'Пополняешь баланс от 1 500 ₽ или активируешь ночной пакет',
                'Получаешь попытку',
                'Выбираешь код',
                'Если сейф открылся — забираешь весь банк',
              ].map((s, i) => (
                <div key={i} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <span style={{ color: '#c41e1e', fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', flexShrink: 0 }}>0{i + 1}</span>
                  <span style={{ color: '#aaa', fontSize: '14px', lineHeight: '1.5' }}>{s}</span>
                </div>
              ))}
            </div>
          </div>

          {/* bottom line */}
          <div className="bg-k-red/10 border-t border-k-red/20" style={{ padding: '16px 24px', textAlign: 'center' }}>
            <p style={{ color: '#f0f0f0', fontSize: '14px', fontWeight: 500 }}>
              Заберёшь 15к сейчас или придёшь когда будет 5к?
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
