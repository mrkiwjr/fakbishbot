import { motion } from 'motion/react'
import PageHeader from '../components/PageHeader'
import PageBg from '../components/PageBg'

const zones = [
  {
    name: 'NORM / DUO',
    rows: [['1 час', '160 ₽'], ['3 часа', '420 ₽'], ['5 часов', '700 ₽'], ['Ночь', '800 ₽']],
  },
  {
    name: 'ULTRA / VIP',
    accent: true,
    rows: [['1 час', '220 ₽'], ['3 часа', '500 ₽'], ['5 часов', '900 ₽'], ['Ночь', '1 200 ₽']],
  },
  {
    name: 'STREET',
    rows: [['1 час', '250 ₽'], ['3 часа', '620 ₽'], ['5 часов', '1 000 ₽'], ['Ночь', '1 500 ₽']],
  },
  {
    name: 'LOFT',
    rows: [['1 час', '600 ₽'], ['3 часа', '1 500 ₽'], ['5 часов', '—'], ['Ночь', '—']],
  },
]

export default function Tariffs() {
  return (
    <div className="min-h-screen pb-20 flex flex-col relative overflow-hidden" style={{ paddingTop: '20px', paddingLeft: '16px', paddingRight: '16px', paddingBottom: '100px' }}>
      <PageBg />

      <div className="relative z-10">
        <PageHeader title="ТАРИФЫ" subtitle="Ночь — с 22:00 до 06:00" />
      </div>

      <div className="relative z-10 flex flex-col gap-3 flex-1 justify-center">
        {zones.map((z, i) => (
          <motion.div
            key={z.name}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className={`rounded-2xl overflow-hidden border backdrop-blur-sm ${z.accent ? 'border-k-red/30' : 'border-k-border/60'}`}
          >
            <div className={z.accent ? 'bg-k-red/10' : 'bg-k-card/70'} style={{ padding: '12px 24px' }}>
              <span className="font-display text-[18px] tracking-wider">{z.name}</span>
            </div>
            {z.rows.map(([dur, price], j) => (
              <div
                key={dur}
                className={`flex justify-between items-center bg-k-dark/70 ${j < z.rows.length - 1 ? 'border-b border-k-border/40' : ''}`}
                style={{ padding: '14px 24px' }}
              >
                <span className="text-k-muted text-[14px]">{dur}</span>
                <span className={`font-display text-[20px] tracking-wide ${z.accent ? 'text-k-red' : ''}`}>{price}</span>
              </div>
            ))}
          </motion.div>
        ))}
      </div>

      <p className="relative z-10 text-k-dim text-[12px] text-center mt-5 leading-relaxed">
        * LOFT рассчитан на 5+ человек. Цена указана за 3х человек за каждого дополнительного - доплата 100₽.
      </p>
    </div>
  )
}
