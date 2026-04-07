const phrases = [
  'ВСЁ НАЧИНАЕТСЯ С ТОЧКИ',
  'EVERYTHING STARTS WITH A POINT',
  'KATANA × CYBER SPACE',
  'ИГРАЙ НА МАКСИМУМ',
  'PLAY AT YOUR BEST',
]

export default function Ticker() {
  const segment = phrases.join('  ·  ')
  const full = `${segment}  ·  ${segment}  ·  `

  return (
    <div className="overflow-hidden border-t border-k-border/30">
      <div className="ticker-track whitespace-nowrap py-2">
        <span className="font-display text-[12px] tracking-[0.3em] text-k-red/50 select-none">
          {full}
        </span>
      </div>
    </div>
  )
}
