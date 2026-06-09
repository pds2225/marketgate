import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import MarketGateDemo from './MarketGateDemo'
import SimulationDemo from './SimulationDemo'

function DemoRouter() {
  const [hash, setHash] = useState(window.location.hash.replace('#', ''))
  useEffect(() => {
    const on = () => setHash(window.location.hash.replace('#', ''))
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return hash === 'simulation' ? <SimulationDemo /> : <MarketGateDemo />
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <DemoRouter />
  </StrictMode>,
)
