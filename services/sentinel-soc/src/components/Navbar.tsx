import { useEffect, useRef, useState } from 'react'
import { Shield, Bell, Wifi, WifiOff } from 'lucide-react'
import { useSentinelStore } from '../store/sentinelStore'
import { useCountUp } from '../hooks/useCountUp'

export default function Navbar() {
  const { stats, sseConnected, threats, pinnedThreats } = useSentinelStore()
  const [visible, setVisible] = useState(true)
  const [bellOpen, setBellOpen] = useState(false)
  const lastY = useRef(0)

  const packetRate    = useCountUp(stats.packetRate)
  const threatsHour   = useCountUp(stats.threatsPerHour)
  const blockedIPs    = useCountUp(stats.blockedIPs)
  const quarantines   = useCountUp(stats.activeQuarantines)

  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY
      setVisible(y < lastY.current || y < 10)
      lastY.current = y
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav style={{
      position: 'fixed', top: '12px', left: '50%',
      transform: `translateX(-50%) translateY(${visible ? 0 : -80}px)`,
      opacity: visible ? 1 : 0,
      width: 'calc(100% - 32px)', maxWidth: '1500px', height: '56px',
      background: 'rgba(0,73,83,0.96)', backdropFilter: 'blur(20px)',
      border: '1px solid rgba(255,255,255,0.1)',
      borderRadius: '117px',
      display: 'flex', alignItems: 'center', padding: '0 14px', gap: '10px',
      boxShadow: '0 20px 60px rgba(0,73,83,0.25)',
      zIndex: 100,
      transition: 'transform 0.4s cubic-bezier(0.16,1,0.3,1), opacity 0.4s cubic-bezier(0.16,1,0.3,1)',
    }}>
      {/* Logo */}
      <div style={{
        width: '36px', height: '36px', background: '#F9F7F2',
        borderRadius: '50%', display: 'flex', alignItems: 'center',
        justifyContent: 'center', cursor: 'pointer', flexShrink: 0,
        transition: 'transform 1s cubic-bezier(0.16,1,0.3,1)',
        fontFamily: 'Playfair Display, serif', fontSize: '16px',
        fontWeight: 700, color: '#004953',
      }}
        onMouseEnter={e => (e.currentTarget.style.transform = 'rotate(360deg)')}
        onMouseLeave={e => (e.currentTarget.style.transform = 'rotate(0deg)')}
      >A</div>

      <div style={{ width: '1px', height: '28px', background: 'rgba(255,255,255,0.1)' }} />

      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Shield size={14} color='rgba(249,247,242,0.7)' />
        <span style={{
          fontFamily: 'Playfair Display, serif', color: '#F9F7F2',
          fontSize: '14px', fontWeight: 700, letterSpacing: '0.18em'
        }}>AXIOM SENTINEL</span>
      </div>

      <div style={{ width: '1px', height: '28px', background: 'rgba(255,255,255,0.1)' }} />

      {/* Counter pills */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Pill label="PKT/S" value={packetRate} color="rgba(249,247,242,0.6)" />
        <Pill label="THREATS/H" value={threatsHour}
              color={threatsHour > 0 ? '#C0392B' : 'rgba(249,247,242,0.6)'}
              border={threatsHour > 0} />
        <Pill label="BLOCKED" value={blockedIPs} color="rgba(249,247,242,0.6)" />
        <Pill label="QUARANTINE" value={quarantines}
              color={quarantines > 0 ? '#C0392B' : 'rgba(249,247,242,0.6)'}
              border={quarantines > 0} critical={quarantines > 0} />
      </div>

      {/* Right */}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          padding: '6px 12px', borderRadius: '117px',
          background: 'rgba(255,255,255,0.07)',
        }}>
          <span style={{
            fontFamily: 'Inter Tight, sans-serif', fontSize: '12px',
            color: 'rgba(249,247,242,0.85)', fontWeight: 500,
          }}>Dr. Priya Sharma</span>
          <span style={{
            fontSize: '9px', fontWeight: 700, padding: '2px 8px',
            borderRadius: '117px', background: 'rgba(249,247,242,0.14)',
            color: '#F9F7F2', letterSpacing: '0.1em',
          }}>PHYSICIAN</span>
        </div>

        {/* Bell */}
        <div style={{ position: 'relative' }}>
          <button onClick={() => setBellOpen(!bellOpen)} style={{
            width: '36px', height: '36px', borderRadius: '50%',
            background: bellOpen ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.07)',
            border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center',
            justifyContent: 'center', color: 'rgba(249,247,242,0.65)', position: 'relative',
          }}>
            <Bell size={16} />
            {pinnedThreats.length > 0 && (
              <span style={{
                position: 'absolute', top: '6px', right: '6px',
                width: '8px', height: '8px', borderRadius: '50%', background: '#C0392B',
              }} />
            )}
          </button>
          {bellOpen && (
            <div style={{
              position: 'absolute', top: '44px', right: 0, width: '280px',
              background: 'white', borderRadius: '18.8px',
              boxShadow: '0 20px 40px rgba(62,39,35,0.15)',
              border: '1px solid rgba(0,73,83,0.1)', padding: '12px', zIndex: 200,
            }}>
              <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '10px', fontWeight: 700, color: 'rgba(93,64,55,0.4)', textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: '8px' }}>
                Pinned Alerts {pinnedThreats.length > 0 ? `(${pinnedThreats.length})` : ''}
              </div>
              {pinnedThreats.length === 0
                ? <div style={{ fontFamily: 'Albert Sans, sans-serif', fontSize: '12px', color: 'rgba(93,64,55,0.4)', textAlign: 'center', padding: '12px' }}>No pinned alerts</div>
                : pinnedThreats.map(t => (
                  <div key={t.id} style={{
                    background: 'rgba(192,57,43,0.06)', borderRadius: '12px',
                    padding: '8px 10px', marginBottom: '6px', borderLeft: '3px solid #C0392B',
                  }}>
                    <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '11px', fontWeight: 600, color: '#3E2723' }}>{t.type.replace(/_/g,' ')}</div>
                    <div style={{ fontFamily: 'Albert Sans, sans-serif', fontSize: '10px', color: '#5D4037', marginTop: '2px' }}>{t.srcIp}</div>
                  </div>
                ))
              }
            </div>
          )}
        </div>

        {/* WS dot */}
        <div style={{
          width: '9px', height: '9px', borderRadius: '50%',
          background: sseConnected ? '#1E8449' : '#C0392B',
          boxShadow: sseConnected ? '0 0 0 0 rgba(30,132,73,0.6)' : 'none',
          animation: sseConnected ? 'pulseLive 2s infinite' : 'none',
          flexShrink: 0,
        }} />
      </div>

      {/* Nav links */}
      <div style={{ display: 'flex', gap: '4px', marginLeft: '8px' }}>
        {[
          { label: 'Dashboard',       href: 'http://localhost:3000/dashboard.html' },
          { label: 'Causal Graph',    href: 'http://localhost:3000/causal_graph.html' },
          { label: 'Counterfactual',  href: 'http://localhost:3000/counterfactual.html' },
          { label: 'Population',      href: 'http://localhost:3000/population.html' },
        ].map(l => (
          <a key={l.label} href={l.href} style={{
            padding: '5px 12px', borderRadius: '117px', border: 'none',
            cursor: 'pointer', fontFamily: 'Inter Tight, sans-serif',
            fontSize: '10px', fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.1em', color: 'rgba(249,247,242,0.5)',
            background: 'transparent', textDecoration: 'none',
            transition: 'color 0.2s',
          }}
            onMouseEnter={e => (e.currentTarget.style.color = '#F9F7F2')}
            onMouseLeave={e => (e.currentTarget.style.color = 'rgba(249,247,242,0.5)')}
          >{l.label}</a>
        ))}
      </div>

      <style>{`
        @keyframes pulseLive {
          0%   { box-shadow: 0 0 0 0 rgba(30,132,73,0.6) }
          70%  { box-shadow: 0 0 0 8px rgba(30,132,73,0) }
          100% { box-shadow: 0 0 0 0 rgba(30,132,73,0) }
        }
      `}</style>
    </nav>
  )
}

function Pill({ label, value, color, border, critical }: {
  label: string; value: number; color: string; border?: boolean; critical?: boolean
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '5px',
      padding: '4px 10px', borderRadius: '117px',
      background: critical ? 'rgba(192,57,43,0.15)' : 'rgba(255,255,255,0.07)',
      border: border ? `1px solid ${color}` : '1px solid transparent',
    }}>
      <span style={{
        fontFamily: 'Inter Tight, sans-serif', fontSize: '9px',
        fontWeight: 700, color: 'rgba(249,247,242,0.4)',
        letterSpacing: '0.15em',
      }}>{label}</span>
      <span style={{
        fontFamily: 'Playfair Display, serif', fontSize: '13px',
        fontWeight: 700, color, transition: 'color 0.3s',
      }}>{value}</span>
    </div>
  )
}
