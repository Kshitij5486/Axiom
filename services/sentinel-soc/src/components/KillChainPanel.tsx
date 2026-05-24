import { motion } from 'framer-motion'
import { X } from 'lucide-react'
import { useSentinelStore } from '../store/sentinelStore'

export default function KillChainPanel() {
  const { killChain, setKillChain } = useSentinelStore()
  if (!killChain) return null

  return (
    <motion.div
      initial={{ x: 300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 300, opacity: 0 }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      style={{
        position: 'fixed', right: 0, top: '56px',
        width: '280px', height: 'calc(100vh - 56px)',
        background: 'white', borderLeft: '1px solid rgba(0,73,83,0.1)',
        borderRadius: '24px 0 0 24px',
        boxShadow: '0 8px 20px rgba(0,0,0,0.1)',
        zIndex: 30, padding: '20px', overflowY: 'auto',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <span style={{ fontFamily: 'Playfair Display, serif', fontSize: '16px', fontStyle: 'italic', color: '#3E2723' }}>
          Ransomware Kill Chain
        </span>
        <button onClick={() => setKillChain(null)} style={{
          background: '#F0ECE6', border: 'none', borderRadius: '50%',
          width: '28px', height: '28px', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#5D4037',
        }}><X size={14} /></button>
      </div>

      {/* Source device */}
      <div style={{
        background: 'rgba(192,57,43,0.08)', borderRadius: '12px',
        padding: '10px', marginBottom: '16px',
        border: '1px solid rgba(192,57,43,0.2)',
      }}>
        <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '9px', fontWeight: 700, color: '#C0392B', letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: '4px' }}>Source Device</div>
        <div style={{ fontFamily: 'monospace', fontSize: '13px', color: '#3E2723', fontWeight: 600 }}>{killChain.sourceDevice}</div>
      </div>

      {/* Timeline */}
      <div style={{ position: 'relative' }}>
        {killChain.propagationPath.map((node, i) => (
          <div key={node.nodeIp} style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
            {/* Timeline line */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
              <div style={{
                width: '10px', height: '10px', borderRadius: '50%',
                background: '#C0392B', border: '2px solid white',
                boxShadow: '0 0 0 2px rgba(192,57,43,0.3)',
                flexShrink: 0,
              }} />
              {i < killChain.propagationPath.length - 1 && (
                <div style={{ width: '2px', flex: 1, background: 'rgba(0,73,83,0.15)', minHeight: '24px' }} />
              )}
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                <span style={{
                  background: '#F0ECE6', color: '#5D4037',
                  borderRadius: '117px', padding: '1px 7px',
                  fontFamily: 'Inter Tight, sans-serif', fontSize: '9px',
                }}>{new Date(node.timestamp).toLocaleTimeString()}</span>
              </div>
              <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '12px', fontWeight: 600, color: '#3E2723', marginBottom: '4px' }}>
                {node.nodeIp}
              </div>
              <div style={{ background: 'rgba(0,73,83,0.08)', height: '6px', borderRadius: '6px', overflow: 'hidden' }}>
                <div style={{
                  width: `${node.confidence * 100}%`, height: '100%',
                  background: '#004953', borderRadius: '6px',
                }} />
              </div>
              <div style={{ fontFamily: 'Albert Sans, sans-serif', fontSize: '10px', color: 'rgba(93,64,55,0.5)', marginTop: '2px' }}>
                {Math.round(node.confidence * 100)}% confidence
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Affected patients */}
      {killChain.affectedPatients.length > 0 && (
        <div style={{
          background: 'rgba(192,57,43,0.06)', borderRadius: '12px',
          padding: '10px', marginTop: '8px',
        }}>
          <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '9px', fontWeight: 700, color: '#C0392B', letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: '6px' }}>
            Affected Patients ({killChain.affectedPatients.length})
          </div>
          {killChain.affectedPatients.map(pid => (
            <div key={pid} style={{
              fontFamily: 'monospace', fontSize: '11px', color: '#3E2723',
              padding: '3px 0', borderBottom: '1px solid rgba(0,73,83,0.06)',
            }}>{pid}</div>
          ))}
        </div>
      )}
    </motion.div>
  )
}
