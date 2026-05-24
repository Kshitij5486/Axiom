import { motion, AnimatePresence } from 'framer-motion'
import { useSentinelStore } from '../store/sentinelStore'
import type { CorrelationEvent } from '../types/sentinel'

const TYPE_COLORS: Record<string, string> = {
  DEVICE_COMPROMISE_CLINICAL_IMPACT:    '#C0392B',
  RANSOMWARE_PATIENT_RISK:              '#C0392B',
  FEDERATED_POISONING_CLINICAL_IMPACT:  '#D68910',
  DEVICE_COMPROMISE_PROPAGATION:        '#D68910',
}

const TYPE_LABELS: Record<string, string> = {
  DEVICE_COMPROMISE_CLINICAL_IMPACT:    'Device Compromise',
  RANSOMWARE_PATIENT_RISK:              'Ransomware Risk',
  FEDERATED_POISONING_CLINICAL_IMPACT:  'Federated Poisoning',
  DEVICE_COMPROMISE_PROPAGATION:        'Propagation Alert',
}

const DEMO_CORRELATIONS: CorrelationEvent[] = [
  {
    id: 'c1', type: 'DEVICE_COMPROMISE_CLINICAL_IMPACT', severity: 'HIGH',
    patientId: 'pt-01', patientName: 'Amit Singh', deviceIp: '10.0.0.5',
    summary: 'ECG monitor trust dropped to 0.2 while patient showed creatinine spike',
    confidence: 0.87, patientAnomalyTimeline: [], deviceThreatTimeline: [],
    overlapStart: Date.now()-300000, overlapEnd: Date.now(),
  },
  {
    id: 'c2', type: 'RANSOMWARE_PATIENT_RISK', severity: 'CRITICAL',
    patientId: null, patientName: null, deviceIp: '10.0.0.8',
    summary: 'EHR exfiltration in Hospital A — 3 patients at risk',
    confidence: 0.95, patientAnomalyTimeline: [], deviceThreatTimeline: [],
    overlapStart: Date.now()-180000, overlapEnd: Date.now(),
    atRiskPatients: ['pt-01', 'pt-02', 'pt-03'], hospitalId: 'hospital-A',
  },
  {
    id: 'c3', type: 'FEDERATED_POISONING_CLINICAL_IMPACT', severity: 'HIGH',
    patientId: 'pt-05', patientName: 'Priya Patel', deviceIp: '10.0.1.12',
    summary: 'Byzantine node detected — recommendation CI widened for 2 patients',
    confidence: 0.72, patientAnomalyTimeline: [], deviceThreatTimeline: [],
    overlapStart: Date.now()-600000, overlapEnd: Date.now(),
  },
]

export default function CorrelationStrip() {
  const { correlations, setSelectedCorrelation } = useSentinelStore()
  const all = correlations.length > 0 ? correlations : DEMO_CORRELATIONS

  return (
    <div style={{
      width: '100%', height: '120px',
      background: 'white',
      padding: '10px 24px',
      display: 'flex', flexDirection: 'column', gap: '6px',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
        <span style={{
          fontFamily: 'Inter Tight, sans-serif', fontSize: '10px',
          fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.2em',
          color: 'rgba(93,64,55,0.4)',
        }}>Active Correlation Alerts</span>
        <span style={{
          background: 'rgba(0,73,83,0.08)', color: '#004953',
          borderRadius: '117px', padding: '1px 7px',
          fontFamily: 'Inter Tight, sans-serif', fontSize: '10px', fontWeight: 700,
        }}>{all.length}</span>
      </div>

      {/* Horizontal scroll */}
      <div style={{
        display: 'flex', gap: '12px', overflowX: 'auto',
        paddingBottom: '4px', flex: 1,
      }}>
        <AnimatePresence>
          {all.map(c => (
            <CorrelationCard key={c.id} event={c} onClick={() => setSelectedCorrelation(c)} />
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}

function CorrelationCard({ event: c, onClick }: { event: CorrelationEvent; onClick: () => void }) {
  const color = TYPE_COLORS[c.type] || '#D68910'
  const label = TYPE_LABELS[c.type] || c.type

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ type: 'spring', damping: 20, stiffness: 300 }}
      onClick={onClick}
      style={{
        background: '#F9F7F2', border: '1px solid rgba(0,73,83,0.1)',
        borderLeft: `3px solid ${color}`,
        borderRadius: '18.8px', flexShrink: 0, width: '288px',
        padding: '10px 12px', cursor: 'pointer',
        transition: 'box-shadow 0.3s cubic-bezier(0.16,1,0.3,1)',
      }}
      onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 8px 20px rgba(0,0,0,0.1)')}
      onMouseLeave={e => (e.currentTarget.style.boxShadow = 'none')}
    >
      {/* Type + severity */}
      <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '4px' }}>
        <span style={{
          background: `${color}15`, color, border: `1px solid ${color}30`,
          borderRadius: '117px', padding: '1px 7px',
          fontFamily: 'Inter Tight, sans-serif', fontSize: '9px', fontWeight: 700,
          textTransform: 'uppercase', letterSpacing: '0.08em',
        }}>{label}</span>
        <span style={{
          background: c.severity === 'CRITICAL' ? 'rgba(192,57,43,0.1)' : 'rgba(214,137,16,0.1)',
          color: c.severity === 'CRITICAL' ? '#C0392B' : '#D68910',
          borderRadius: '117px', padding: '1px 6px',
          fontFamily: 'Inter Tight, sans-serif', fontSize: '9px', fontWeight: 700,
        }}>{c.severity}</span>
      </div>

      {/* Patient name */}
      {c.patientName && (
        <div style={{ fontFamily: 'Playfair Display, serif', fontSize: '13px', fontWeight: 600, color: '#3E2723', marginBottom: '2px' }}>
          {c.patientName}
        </div>
      )}

      {/* Summary */}
      <div style={{
        fontFamily: 'Albert Sans, sans-serif', fontSize: '11px',
        color: 'rgba(93,64,55,0.7)', marginBottom: '6px',
        display: '-webkit-box', WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical', overflow: 'hidden',
      }}>{c.summary}</div>

      {/* Confidence bar */}
      <div style={{ background: 'rgba(0,73,83,0.08)', height: '4px', borderRadius: '4px', overflow: 'hidden' }}>
        <div style={{
          width: `${c.confidence * 100}%`, height: '100%',
          background: '#004953', borderRadius: '4px',
          transition: 'width 0.6s cubic-bezier(0.16,1,0.3,1)',
        }} />
      </div>
    </motion.div>
  )
}
