import { motion } from 'motion/react'

interface EventCardProps {
  title: string
  date: string
  type: string
  description?: string
  index: number
}

const typeColors: Record<string, string> = {
  'Турнир': 'bg-katana-red',
  'Акция': 'bg-katana-orange',
  'Ивент': 'bg-emerald-600',
  'Ночь': 'bg-purple-700',
}

export default function EventCard({ title, date, type, description, index }: EventCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1, duration: 0.4 }}
      className="relative bg-katana-card katana-border rounded-lg p-4 hover:border-katana-red/40 transition-colors group"
    >
      <div className="absolute top-0 left-0 w-1 h-full bg-katana-red rounded-l-lg opacity-0 group-hover:opacity-100 transition-opacity" />

      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className={`${typeColors[type] || 'bg-katana-gray'} text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded`}>
              {type}
            </span>
            <span className="text-katana-gray-light text-xs">{date}</span>
          </div>
          <h3 className="font-display text-2xl tracking-wide text-katana-white leading-tight">
            {title}
          </h3>
          {description && (
            <p className="text-katana-gray-light text-sm mt-1.5 leading-relaxed">{description}</p>
          )}
        </div>

        <div className="shrink-0 mt-1">
          <div className="w-10 h-10 rounded-lg bg-katana-red/10 border border-katana-red/30 flex items-center justify-center text-katana-red font-display text-lg group-hover:bg-katana-red/20 transition-colors">
            →
          </div>
        </div>
      </div>
    </motion.div>
  )
}
