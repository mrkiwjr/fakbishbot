export default function PageBg() {
  return (
    <div className="absolute inset-0 pointer-events-none">
      <img src="/images/hero.jpg" alt="" className="w-full h-full object-cover blur-[16px] scale-110 opacity-20" />
      <div
        className="absolute inset-0"
        style={{
          background: `
            linear-gradient(to bottom, rgba(8,8,8,0.5) 0%, rgba(8,8,8,0.75) 50%, #080808 100%),
            radial-gradient(ellipse at 50% 30%, rgba(196,30,30,0.08) 0%, transparent 60%)
          `,
        }}
      />
    </div>
  )
}
