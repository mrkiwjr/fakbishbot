import { Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import Home from './pages/Home'
import Tariffs from './pages/Tariffs'
import Booking from './pages/Booking'
import Promos from './pages/Promos'
import PromoCode from './pages/PromoCode'
import AdminPanel from './pages/AdminPanel'

export default function App() {
  return (
    <div className="min-h-screen relative bg-k-black noise-overlay cyber-grid">
      {/* floating particles */}
      {Array.from({ length: 25 }, (_, i) => (
        <div key={i} className="particle" />
      ))}

      <div className="relative z-10">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/tariffs" element={<Tariffs />} />
          <Route path="/booking" element={<Booking />} />
          <Route path="/promos" element={<Promos />} />
          <Route path="/promo-code" element={<PromoCode />} />
          <Route path="/admin" element={<AdminPanel />} />
        </Routes>
      </div>

      <NavBar />
    </div>
  )
}
