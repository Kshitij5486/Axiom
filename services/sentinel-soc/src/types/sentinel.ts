export interface ThreatEvent {
  id:             string
  timestamp:      number
  severity:       'CRITICAL' | 'HIGH' | 'MEDIUM'
  type:           'GEO_BLOCK' | 'SYN_FLOOD' | 'RANSOMWARE' | 'FEDERATED_ATTACK' | 'SNI_BLOCK' | 'LATERAL_MOVEMENT' | 'PORT_SCAN' | 'BEACONING' | 'DATA_EXFILTRATION' | 'DEVICE_TRAFFIC_SPIKE'
  srcIp:          string
  destIp:         string
  hospitalId:     string
  description:    string
  geoCoordinate?: [number, number]
  packetVolume?:  number
  sniDomain?:     string
  detail?:        string
}

export interface Device {
  ip:                  string
  deviceType:          'ehr_system' | 'medical_device' | 'workstation' | 'axiom_service' | 'federated_node' | 'unknown'
  hospitalId:          string
  trustScore:          number
  status:              'TRUSTED' | 'LOW_TRUST' | 'UNTRUSTED' | 'QUARANTINED'
  lastThreat:          number | null
  axiomPatientId:      string | null
  trafficHistory:      number[]
  destinationHistory:  number[]
}

export interface TimelineEvent {
  timestamp: number
  label:     string
  severity:  'CRITICAL' | 'HIGH' | 'MEDIUM'
}

export interface CorrelationEvent {
  id:                      string
  type:                    'DEVICE_COMPROMISE_CLINICAL_IMPACT' | 'RANSOMWARE_PATIENT_RISK' | 'FEDERATED_POISONING_CLINICAL_IMPACT' | 'DEVICE_COMPROMISE_PROPAGATION'
  severity:                'CRITICAL' | 'HIGH' | 'MEDIUM'
  patientId:               string | null
  patientName:             string | null
  deviceIp:                string
  summary:                 string
  confidence:              number
  patientAnomalyTimeline:  TimelineEvent[]
  deviceThreatTimeline:    TimelineEvent[]
  overlapStart:            number
  overlapEnd:              number
  atRiskPatients?:         string[]
  hospitalId?:             string
}

export interface KillChainNode {
  nodeIp:     string
  timestamp:  number
  confidence: number
  deviceType: string
}

export interface KillChainEvent {
  propagationPath:  KillChainNode[]
  affectedPatients: string[]
  sourceDevice:     string
}

export interface GeoThreat {
  ip:          string
  lat:         number
  lng:         number
  country:     string
  packetCount: number
  timestamp:   number
}

export interface SentinelStats {
  packetRate:        number
  threatsPerHour:    number
  blockedIPs:        number
  activeQuarantines: number
}
