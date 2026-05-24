const DEMO_DEVICES = [
  { ip:'10.0.0.1', deviceType:'ehr_system' as const,     hospitalId:'hospital-A', trustScore:0.95, status:'TRUSTED' as const,   lastThreat:null, axiomPatientId:null,    trafficHistory:[50,55,48,60,52], destinationHistory:[3,4,3,5,4] },
  { ip:'10.0.0.5', deviceType:'medical_device' as const, hospitalId:'hospital-A', trustScore:0.2,  status:'UNTRUSTED' as const, lastThreat:0,    axiomPatientId:'pt-01', trafficHistory:[10,80,120,200,180], destinationHistory:[1,2,8,12,10] },
  { ip:'10.0.1.10',deviceType:'federated_node' as const, hospitalId:'hospital-B', trustScore:0.8,  status:'TRUSTED' as const,   lastThreat:null, axiomPatientId:null,    trafficHistory:[30,32,28,35,31], destinationHistory:[2,2,1,2,2] },
  { ip:'10.0.0.8', deviceType:'workstation' as const,    hospitalId:'hospital-C', trustScore:0.45, status:'LOW_TRUST' as const, lastThreat:0,    axiomPatientId:null,    trafficHistory:[20,22,25,18,30], destinationHistory:[5,6,7,5,8] },
  { ip:'10.0.1.12',deviceType:'federated_node' as const, hospitalId:'hospital-C', trustScore:0.29, status:'UNTRUSTED' as const, lastThreat:0,    axiomPatientId:null,    trafficHistory:[40,45,200,300,280], destinationHistory:[2,3,15,20,18] },
  { ip:'10.0.0.3', deviceType:'axiom_service' as const,  hospitalId:'hospital-A', trustScore:1.0,  status:'TRUSTED' as const,   lastThreat:null, axiomPatientId:null,    trafficHistory:[100,102,98,105,101], destinationHistory:[1,1,1,1,1] },
]

import { create } from 'zustand'
import type { ThreatEvent, Device, CorrelationEvent, KillChainEvent, GeoThreat, SentinelStats } from '../types/sentinel'

interface SentinelState {
  threats:             ThreatEvent[]
  pinnedThreats:       ThreatEvent[]
  devices:             Device[]
  correlations:        CorrelationEvent[]
  geoThreats:          GeoThreat[]
  highlightedNodeIp:   string | null
  heatmapMode:         boolean
  killChain:           KillChainEvent | null
  selectedThreat:      ThreatEvent | null
  selectedDevice:      Device | null
  selectedCorrelation: CorrelationEvent | null
  sseConnected:        boolean
  criticalFlash:       boolean
  stats:               SentinelStats
  addThreat:           (t: ThreatEvent) => void
  unpinThreat:         (id: string) => void
  setDevices:          (d: Device[]) => void
  updateDevice:        (d: Device) => void
  addCorrelation:      (c: CorrelationEvent) => void
  addGeoThreat:        (g: GeoThreat) => void
  setHighlightedNode:  (ip: string | null) => void
  setHeatmapMode:      (v: boolean) => void
  setKillChain:        (k: KillChainEvent | null) => void
  setSelectedThreat:   (t: ThreatEvent | null) => void
  setSelectedDevice:   (d: Device | null) => void
  setSelectedCorrelation: (c: CorrelationEvent | null) => void
  setSseConnected:     (v: boolean) => void
  setCriticalFlash:    (v: boolean) => void
  updateStats:         (s: Partial<SentinelStats>) => void
  quarantineDevice:    (ip: string) => void
}

export const useSentinelStore = create<SentinelState>((set) => ({
  threats: [], pinnedThreats: [], devices: DEMO_DEVICES, correlations: [],
  geoThreats: [], highlightedNodeIp: null, heatmapMode: false,
  killChain: null, selectedThreat: null, selectedDevice: null,
  selectedCorrelation: null, sseConnected: false, criticalFlash: false,
  stats: { packetRate: 0, threatsPerHour: 0, blockedIPs: 0, activeQuarantines: 0 },

  addThreat: (t) => set((s) => ({
    threats:       [t, ...s.threats].slice(0, 100),
    pinnedThreats: t.severity === 'CRITICAL' ? [t, ...s.pinnedThreats].slice(0, 20) : s.pinnedThreats,
    criticalFlash: t.severity === 'CRITICAL',
  })),

  unpinThreat:    (id) => set((s) => ({ pinnedThreats: s.pinnedThreats.filter(t => t.id !== id) })),
  setDevices:     (d) => set({ devices: d }),
  updateDevice:   (d) => set((s) => ({
    devices: s.devices.some(x => x.ip === d.ip)
      ? s.devices.map(x => x.ip === d.ip ? d : x)
      : [...s.devices, d]
  })),
  addCorrelation:      (c) => set((s) => ({ correlations: [c, ...s.correlations].slice(0, 100) })),
  addGeoThreat:        (g) => set((s) => ({ geoThreats:  [g, ...s.geoThreats].slice(0, 200) })),
  setHighlightedNode:  (ip) => set({ highlightedNodeIp: ip }),
  setHeatmapMode:      (v)  => set({ heatmapMode: v }),
  setKillChain:        (k)  => set({ killChain: k }),
  setSelectedThreat:   (t)  => set({ selectedThreat: t }),
  setSelectedDevice:   (d)  => set({ selectedDevice: d }),
  setSelectedCorrelation: (c) => set({ selectedCorrelation: c }),
  setSseConnected:     (v)  => set({ sseConnected: v }),
  setCriticalFlash:    (v)  => set({ criticalFlash: v }),
  updateStats:         (s)  => set((st) => ({ stats: { ...st.stats, ...s } })),
  quarantineDevice:    (ip) => set((s) => ({
    devices: s.devices.map(d => d.ip === ip ? { ...d, status: 'QUARANTINED' as const } : d)
  })),
}))
