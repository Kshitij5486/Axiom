import { useSentinelStore } from '../store/sentinelStore'
import { generateRandomThreat, MOCK_DEVICES, MOCK_CORRELATIONS } from './mockData'
import type { CorrelationEvent } from '../types/sentinel'

let mockInterval: ReturnType<typeof setInterval> | null = null
let statsInterval: ReturnType<typeof setInterval> | null = null

const CORR_TYPES: CorrelationEvent['type'][] = [
  'DEVICE_COMPROMISE_CLINICAL_IMPACT',
  'RANSOMWARE_PATIENT_RISK',
  'FEDERATED_POISONING_CLINICAL_IMPACT',
]

export function startMockSSE() {
  const store = useSentinelStore.getState()

  // Set initial data
  store.setDevices(MOCK_DEVICES)
  store.setSseConnected(true)
  store.updateStats({
    packetRate:        847,
    threatsPerHour:    12,
    blockedIPs:        3,
    activeQuarantines: 1,
  })

  // Load initial correlations
  MOCK_CORRELATIONS.forEach(c => store.addCorrelation(c))

  // Generate new threat every 8-20 seconds
  mockInterval = setInterval(() => {
    const threat = generateRandomThreat()
    store.addThreat(threat)

    if (threat.severity === 'CRITICAL') {
      store.setCriticalFlash(true)
      setTimeout(() => store.setCriticalFlash(false), 600)
      playAlarm()
    }

    // Occasionally add a correlation
    if (Math.random() < 0.2) {
      const type = CORR_TYPES[Math.floor(Math.random() * CORR_TYPES.length)]
      store.addCorrelation({
        id:                     `c-${Date.now()}`,
        type,
        severity:               Math.random() < 0.3 ? 'CRITICAL' : 'HIGH',
        patientId:              Math.random() < 0.5 ? `pt-0${Math.floor(Math.random()*5)+1}` : null,
        patientName:            Math.random() < 0.5 ? 'Amit Singh' : null,
        deviceIp:               MOCK_DEVICES[Math.floor(Math.random()*MOCK_DEVICES.length)].ip,
        summary:                getSummary(type),
        confidence:             Math.random() * 0.4 + 0.6,
        patientAnomalyTimeline: [],
        deviceThreatTimeline:   [],
        overlapStart:           Date.now() - 300000,
        overlapEnd:             Date.now(),
      })
    }

    // Slowly degrade/recover device trust scores
    const devices = useSentinelStore.getState().devices
    const updated = devices.map(d => {
      let score = d.trustScore
      if (d.status === 'UNTRUSTED' || d.status === 'LOW_TRUST') {
        score = Math.max(0, score - 0.01)
      } else {
        score = Math.min(1.0, score + 0.001)
      }
      return {
        ...d,
        trustScore: Math.round(score * 100) / 100,
        status: score < 0.3 ? 'UNTRUSTED' as const
               : score < 0.5 ? 'LOW_TRUST' as const
               : 'TRUSTED' as const,
      }
    })
    store.setDevices(updated)

  }, Math.random() * 12000 + 8000)

  // Update stats every 3 seconds
  statsInterval = setInterval(() => {
    const s = useSentinelStore.getState().stats
    useSentinelStore.getState().updateStats({
      packetRate:     Math.floor(800 + Math.random() * 200),
      threatsPerHour: s.threatsPerHour + (Math.random() < 0.3 ? 1 : 0),
      blockedIPs:     s.blockedIPs,
    })
  }, 3000)
}

export function stopMockSSE() {
  if (mockInterval)  clearInterval(mockInterval)
  if (statsInterval) clearInterval(statsInterval)
}

function getSummary(type: CorrelationEvent['type']): string {
  const summaries: Record<string, string> = {
    DEVICE_COMPROMISE_CLINICAL_IMPACT:   'Device trust degraded while patient showed anomaly',
    RANSOMWARE_PATIENT_RISK:             'Ransomware pattern detected — patients at risk',
    FEDERATED_POISONING_CLINICAL_IMPACT: 'Federated attack may affect recommendation quality',
    DEVICE_COMPROMISE_PROPAGATION:       'Compromised device may spread to patient-facing nodes',
  }
  return summaries[type] || type
}

function playAlarm() {
  try {
    const ctx  = new AudioContext()
    const osc  = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.type = 'square'
    osc.frequency.value = 880
    gain.gain.value = 0.3
    osc.start()
    osc.stop(ctx.currentTime + 0.2)
  } catch {}
}
