import { useEffect } from 'react'
import { useSentinelSSE } from './hooks/useSentinelSSE'
import Navbar from './components/Navbar'
import ThreeScene from './components/ThreeScene'
import ThreatFeed from './components/ThreatFeed'
import DeviceRegistry from './components/DeviceRegistry'
import CorrelationStrip from './components/CorrelationStrip'
import GeoIPMap from './components/GeoIPMap'
import KillChainPanel from './components/KillChainPanel'
import CorrelationModal from './components/CorrelationModal'
import CriticalOverlay from './components/CriticalOverlay'
import { useSentinelStore } from './store/sentinelStore'
import { startMockSSE } from './mock/mockSSE'
import { IS_MOCK } from './config'

export default function App() {
  useSentinelSSE()

  // Use mock data in production (Vercel)
  useEffect(() => {
    if (IS_MOCK) {
      startMockSSE()
    }
  }, [])
  const { selectedCorrelation, killChain } = useSentinelStore()

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column',
                  background: '#F9F7F2', fontFamily: 'Albert Sans, sans-serif' }}>
      <Navbar />
      <CriticalOverlay />
      <div style={{
        flex: 1,
        display: 'grid',
        gridTemplateColumns: '320px 1fr 280px',
        gridTemplateRows: '1fr 120px',
        height: 'calc(100vh - 56px)',
        marginTop: '56px',
        overflow: 'hidden',
      }}>
        <div style={{ overflowY: 'auto', borderRight: '1px solid rgba(0,73,83,0.1)' }}>
          <ThreatFeed />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <ThreeScene />
          </div>
          <div style={{ height: '180px', flexShrink: 0 }}>
            <GeoIPMap />
          </div>
        </div>
        <div style={{ overflowY: 'auto', borderLeft: '1px solid rgba(0,73,83,0.1)' }}>
          <DeviceRegistry />
        </div>
        <div style={{ gridColumn: '1 / -1', borderTop: '1px solid rgba(0,73,83,0.08)' }}>
          <CorrelationStrip />
        </div>
      </div>
      {killChain && <KillChainPanel />}
      {selectedCorrelation && <CorrelationModal />}
    </div>
  )
}
