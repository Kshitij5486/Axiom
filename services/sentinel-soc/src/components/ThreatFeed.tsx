import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, ShieldAlert } from 'lucide-react'
import { useSentinelStore } from '../store/sentinelStore'
import type { ThreatEvent } from '../types/sentinel'

const SEV_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  CRITICAL: { bg: 'rgba(192,57,43,0.1)',  text: '#C0392B', border: 'rgba(192,57,43,0.2)' },
  HIGH:     { bg: 'rgba(214,137,16,0.1)', text: '#D68910', border: 'rgba(214,137,16,0.2)' },
  MEDIUM:   { bg: 'rgba(0,73,83,0.08)',   text: '#004953', border: 'rgba(0,73,83,0.15)'  },
}

const DEMO_THREATS: ThreatEvent[] = [
  { id:'d1', timestamp: Date.now()-30000, severity:'HIGH',     type:'SYN_FLOOD',       srcIp:'192.168.1.50', destIp:'10.0.0.1',  hospitalId:'hospital-A', description:'SYN flood detected: 101 packets in 10s' },
  { id:'d2', timestamp: Date.now()-60000, severity:'MEDIUM',   type:'GEO_BLOCK',       srcIp:'20.233.83.145',destIp:'10.0.0.2', hospitalId:'hospital-B', description:'Traffic from blocked country: AE' },
  { id:'d3', timestamp: Date.now()-90000, severity:'CRITICAL', type:'DATA_EXFILTRATION',srcIp:'10.0.0.5',   destIp:'1.2.3.4',  hospitalId:'hospital-A', description:'EHR exfiltration: 11.2MB in 5min' },
  { id:'d4', timestamp: Date.now()-120000,severity:'MEDIUM',   type:'PORT_SCAN',       srcIp:'10.0.0.8',    destIp:'10.0.0.9', hospitalId:'hospital-C', description:'Port scan: 23 distinct ports' },
  { id:'d5', timestamp: Date.now()-150000,severity:'HIGH',     type:'FEDERATED_ATTACK',srcIp:'10.0.1.99',   destIp:'10.0.1.1', hospitalId:'hospital-A', description:'Unknown node to Flower server' },
]

export default function ThreatFeed() {
  const { threats, pinnedThreats, unpinThreat,
          setHighlightedNode, setSelectedThreat } = useSentinelStore()
  const [sevFilter,  setSevFilter]  = useState('ALL')
  const [typeFilter, setTypeFilter] = useState('ALL')
  const [expanded,   setExpanded]   = useState<string | null>(null)

  const allThreats = threats.length > 0 ? threats : DEMO_THREATS

  const filtered = allThreats.filter(t =>
    (sevFilter  === 'ALL' || t.severity === sevFilter) &&
    (typeFilter === 'ALL' || t.type === typeFilter)
  )

  const handleCard = (t: ThreatEvent) => {
    setExpanded(expanded === t.id ? null : t.id)
    setHighlightedNode(t.srcIp)
    setSelectedThreat(t)
  }

  const [quarantined, setQuarantined] = useState<Set<string>>(new Set())

  const quarantine = async (ip: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setQuarantined(prev => new Set([...prev, ip]))
    try {
      await fetch(`http://172.30.88.1:8090/sentinel/quarantine/${ip}`, { method: 'POST' })
    } catch {}
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{
        background: 'white', borderBottom: '1px solid rgba(0,73,83,0.08)',
        padding: '12px 16px', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <span style={{ fontFamily: 'Playfair Display, serif', fontSize: '14px', fontStyle: 'italic', color: '#3E2723' }}>
            Threat Intelligence
          </span>
          <span style={{
            background: 'rgba(0,73,83,0.08)', color: '#004953',
            borderRadius: '117px', padding: '2px 8px',
            fontFamily: 'Inter Tight, sans-serif', fontSize: '10px', fontWeight: 700,
          }}>{allThreats.length}</span>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {['ALL','CRITICAL','HIGH','MEDIUM'].map(s => (
            <button key={s} onClick={() => setSevFilter(s)} style={{
              padding: '3px 10px', borderRadius: '117px', border: 'none',
              cursor: 'pointer', fontFamily: 'Inter Tight, sans-serif',
              fontSize: '9px', fontWeight: 700, letterSpacing: '0.1em',
              background: sevFilter === s ? '#004953' : '#F0ECE6',
              color:      sevFilter === s ? '#F9F7F2' : '#5D4037',
              transition: 'all 0.2s',
            }}>{s}</button>
          ))}
        </div>
      </div>

      {/* Pinned CRITICAL */}
      {pinnedThreats.length > 0 && (
        <div style={{ background: 'rgba(192,57,43,0.04)', padding: '8px 12px', flexShrink: 0 }}>
          <div style={{
            fontFamily: 'Inter Tight, sans-serif', fontSize: '9px',
            fontWeight: 700, color: '#C0392B', letterSpacing: '0.2em',
            marginBottom: '6px',
          }}>PINNED CRITICAL</div>
          {pinnedThreats.map(t => (
            <div key={t.id} style={{
              background: 'white', borderRadius: '12px',
              border: '1px solid rgba(192,57,43,0.2)',
              borderLeft: '3px solid #C0392B',
              padding: '8px 10px', marginBottom: '6px',
              display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
            }}>
              <div>
                <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '11px', fontWeight: 600, color: '#3E2723' }}>
                  {t.type.replace(/_/g, ' ')}
                </div>
                <div style={{ fontFamily: 'Albert Sans, sans-serif', fontSize: '10px', color: '#5D4037', marginTop: '2px' }}>
                  {t.srcIp}
                </div>
              </div>
              <button onClick={() => unpinThreat(t.id)} style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: '#5D4037', padding: '2px',
              }}><X size={12} /></button>
            </div>
          ))}
        </div>
      )}

      {/* Feed */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
        <AnimatePresence initial={false}>
          {filtered.map(t => (
            <ThreatCard
              key={t.id} threat={t}
              expanded={expanded === t.id}
              isQuarantined={quarantined.has(t.srcIp)}
              onClick={() => handleCard(t)}
              onQuarantine={(e) => quarantine(t.srcIp, e)}
            />
          ))}
        </AnimatePresence>
        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'rgba(93,64,55,0.4)' }}>
            <ShieldAlert size={32} style={{ margin: '0 auto 8px', opacity: 0.3 }} />
            <div style={{ fontFamily: 'Albert Sans, sans-serif', fontSize: '12px' }}>No threats match filter</div>
          </div>
        )}
      </div>
    </div>
  )
}

function ThreatCard({ threat: t, expanded, isQuarantined, onClick, onQuarantine }: {
  threat: ThreatEvent; expanded: boolean; isQuarantined?: boolean
  onClick: () => void; onQuarantine: (e: React.MouseEvent) => void
}) {
  const sev   = SEV_COLORS[t.severity] || SEV_COLORS.MEDIUM
  const ts    = new Date(t.timestamp).toLocaleTimeString()

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -20, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.97 }}
      transition={{ type: 'spring', damping: 20, stiffness: 300 }}
      onClick={onClick}
      style={{
        background: 'white', borderRadius: '18.8px',
        border: '1px solid rgba(0,73,83,0.08)',
        boxShadow: '0 20px 40px rgba(62,39,35,0.05)',
        padding: '14px', marginBottom: '10px', cursor: 'pointer',
        transition: 'box-shadow 0.3s cubic-bezier(0.16,1,0.3,1)',
      }}
      onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 8px 20px rgba(0,0,0,0.1)')}
      onMouseLeave={e => (e.currentTarget.style.boxShadow = '0 20px 40px rgba(62,39,35,0.05)')}
    >
      {/* Row 1: timestamp + severity */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
        <span style={{ fontFamily: 'Albert Sans, sans-serif', fontSize: '10px', color: 'rgba(93,64,55,0.4)' }}>{ts}</span>
        <span style={{
          background: sev.bg, color: sev.text,
          border: `1px solid ${sev.border}`,
          borderRadius: '117px', padding: '2px 8px',
          fontFamily: 'Inter Tight, sans-serif', fontSize: '9px', fontWeight: 700,
          textTransform: 'uppercase', letterSpacing: '0.1em',
        }}>{t.severity}</span>
      </div>

      {/* Row 2: type + IP */}
      <div style={{ marginBottom: '4px' }}>
        <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '12px', fontWeight: 600, color: '#3E2723' }}>
          {t.type.replace(/_/g, ' ')}
        </div>
        <div style={{ fontFamily: 'monospace', fontSize: '11px', color: 'rgba(93,64,55,0.5)' }}>
          {t.srcIp} → {t.destIp}
        </div>
      </div>

      {/* Row 3: hospital + description */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
        <span style={{
          background: '#F0ECE6', color: '#5D4037',
          borderRadius: '117px', padding: '2px 8px',
          fontFamily: 'Inter Tight, sans-serif', fontSize: '10px',
        }}>{t.hospitalId || 'unknown'}</span>
      </div>
      <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '11px', color: 'rgba(93,64,55,0.7)', fontStyle: 'italic' }}>
        {t.description}
      </div>

      {/* Expanded */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ marginTop: '12px' }}>
              <pre style={{
                background: '#F0ECE6', borderRadius: '12px', padding: '10px',
                fontFamily: 'monospace', fontSize: '10px', color: '#5D4037',
                overflowX: 'auto', whiteSpace: 'pre-wrap',
              }}>{JSON.stringify(t, null, 2)}</pre>
              <button onClick={onQuarantine} style={{
                marginTop: '8px', width: '100%',
                background: isQuarantined ? '#1E8449' : '#C0392B',
                color: 'white', border: 'none', borderRadius: '117px',
                padding: '8px', cursor: isQuarantined ? 'default' : 'pointer',
                fontFamily: 'Inter Tight, sans-serif',
                fontSize: '10px', fontWeight: 700,
                textTransform: 'uppercase', letterSpacing: '0.1em',
                boxShadow: '0 10px 30px rgba(0,73,83,0.2)',
                transition: 'all 0.3s cubic-bezier(0.16,1,0.3,1)',
              }}>
                {isQuarantined ? '✓ Quarantined' : 'Quarantine IP'}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
