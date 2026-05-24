import { useEffect, useRef, useCallback } from 'react'
import { useSentinelStore } from '../store/sentinelStore'
import type { ThreatEvent, Device, CorrelationEvent } from '../types/sentinel'

export function useSentinelSSE() {
  const esRef    = useRef<EventSource | null>(null)
  const queue    = useRef<string[]>([])
  const raf      = useRef<number>(0)
  const retry    = useRef<number>(1000)
  const retryTmo = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  const store = useSentinelStore()
  const { addThreat, setDevices, addCorrelation, updateStats, setSseConnected, setCriticalFlash } = store

  const processQueue = useCallback(() => {
    const batch = queue.current.splice(0, 5)
    batch.forEach(raw => {
      try {
        const d = JSON.parse(raw)
        if (d.status === 'connected') return

        if (d.severity && (d.threat_type || d.src_ip)) {
          const t: ThreatEvent = {
            id:          `${Date.now()}-${Math.random().toString(36).slice(2)}`,
            timestamp:   d.timestamp ? d.timestamp * 1000 : Date.now(),
            severity:    d.severity,
            type:        d.threat_type || 'GEO_BLOCK',
            srcIp:       d.src_ip || '',
            destIp:      d.dest_ip || '',
            hospitalId:  d.hospital_id || '',
            description: d.detail || d.status || '',
            sniDomain:   d.sni_domain,
            detail:      d.detail,
          }
          addThreat(t)
          if (t.severity === 'CRITICAL') {
            setCriticalFlash(true)
            setTimeout(() => setCriticalFlash(false), 600)
            playAlarm()
          }
        }

        if (d.correlation_type) {
          const c: CorrelationEvent = {
            id:                     `c-${Date.now()}-${Math.random().toString(36).slice(2)}`,
            type:                   d.correlation_type,
            severity:               d.severity || 'HIGH',
            patientId:              d.patient_id || null,
            patientName:            null,
            deviceIp:               d.device_ip || '',
            summary:                d.detail || d.correlation_type,
            confidence:             d.correlation_confidence || 0.8,
            patientAnomalyTimeline: [],
            deviceThreatTimeline:   [],
            overlapStart:           Date.now() - 300000,
            overlapEnd:             Date.now(),
            atRiskPatients:         d.at_risk_patients || [],
            hospitalId:             d.hospital_id || '',
          }
          addCorrelation(c)
        }
      } catch {}
    })
    raf.current = requestAnimationFrame(processQueue)
  }, [addThreat, addCorrelation, updateStats, setSseConnected, setCriticalFlash])

  const connect = useCallback(() => {
    esRef.current?.close()
    try {
      const es = new EventSource('http://localhost:8090/sentinel/stream')
      esRef.current = es
      es.onopen = () => { setSseConnected(true); retry.current = 1000 }
      es.onmessage = (e) => { if (e.data) queue.current.push(e.data) }
      es.onerror = () => {
        setSseConnected(false)
        es.close()
        retryTmo.current = setTimeout(() => {
          retry.current = Math.min(retry.current * 2, 30000)
          connect()
        }, retry.current)
      }
    } catch { setSseConnected(false) }
  }, [setSseConnected])

  // Poll devices and stats
  useEffect(() => {
    const poll = async () => {
      try {
        const [sr, dr] = await Promise.all([
          fetch('http://localhost:8090/sentinel/stats'),
          fetch('http://localhost:8090/sentinel/devices'),
        ])
        const s = await sr.json()
        updateStats({ threatsPerHour: s.threats_total || 0, activeQuarantines: s.active_quarantines || 0 })
        const dj = await dr.json()
        if (dj.devices) {
          setDevices(dj.devices.map((d: any) => ({
            ip: d.ip, deviceType: d.device_type || 'unknown',
            hospitalId: d.hospital_id || '',
            trustScore: parseFloat(d.trust_score) || 1.0,
            status: d.quarantined ? 'QUARANTINED'
                  : parseFloat(d.trust_score) < 0.3 ? 'UNTRUSTED'
                  : parseFloat(d.trust_score) < 0.5 ? 'LOW_TRUST' : 'TRUSTED',
            lastThreat: null, axiomPatientId: null,
            trafficHistory:     Array.from({length:20}, () => Math.random()*100),
            destinationHistory: Array.from({length:20}, () => Math.random()*10),
          })))
        }
      } catch {}
    }
    poll()
    const i = setInterval(poll, 8000)
    return () => clearInterval(i)
  }, [updateStats, setDevices])

  useEffect(() => {
    connect()
    raf.current = requestAnimationFrame(processQueue)
    return () => {
      esRef.current?.close()
      cancelAnimationFrame(raf.current)
      clearTimeout(retryTmo.current)
    }
  }, [connect, processQueue])
}

function playAlarm() {
  try {
    const ctx  = new AudioContext()
    const osc  = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.type      = 'square'
    osc.frequency.value = 880
    gain.gain.value     = 0.3
    osc.start()
    osc.stop(ctx.currentTime + 0.2)
  } catch {}
}
