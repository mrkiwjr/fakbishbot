import { useNavigate } from 'react-router-dom'
import { motion } from 'motion/react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  onBack?: () => void
}

export default function PageHeader({ title, subtitle, onBack }: PageHeaderProps) {
  const navigate = useNavigate()

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px', paddingLeft: '4px' }}
    >
      <button
        onClick={onBack || (() => navigate('/'))}
        style={{
          width: '36px',
          height: '36px',
          flexShrink: 0,
          borderRadius: '12px',
          background: '#161616',
          border: '1px solid #222222',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#888888',
          cursor: 'pointer',
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </button>
      <div>
        <h1 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: '26px', letterSpacing: '0.05em', lineHeight: 1, color: '#f0f0f0' }}>
          {title}
        </h1>
        {subtitle && <p style={{ color: '#555555', fontSize: '11px', marginTop: '2px' }}>{subtitle}</p>}
      </div>
    </motion.div>
  )
}
