import type { ThreatEvent, Device, CorrelationEvent } from '../types/sentinel'

export const MOCK_DEVICES: Device[] = [
  { ip:'10.0.0.1', deviceType:'ehr_system',     hospitalId:'hospital-A', trustScore:0.95, status:'TRUSTED',     lastThreat:null,           axiomPatientId:null,    trafficHistory:[50,55,48,60,52,58,61,49,55,53], destinationHistory:[3,4,3,5,4,3,4,3,4,5] },
  { ip:'10.0.0.5', deviceType:'medical_device', hospitalId:'hospital-A', trustScore:0.2,  status:'UNTRUSTED',   lastThreat:Date.now()-5000, axiomPatientId:'pt-01', trafficHistory:[10,80,120,200,180,210,195,220,205,215], destinationHistory:[1,2,8,12,10,11,9,13,10,12] },
  { ip:'10.0.1.10',deviceType:'federated_node', hospitalId:'hospital-B', trustScore:0.8,  status:'TRUSTED',     lastThreat:null,           axiomPatientId:null,    trafficHistory:[30,32,28,35,31,33,29,34,32,31], destinationHistory:[2,2,1,2,2,2,1,2,2,2] },
  { ip:'10.0.0.8', deviceType:'workstation',    hospitalId:'hospital-C', trustScore:0.45, status:'LOW_TRUST',   lastThreat:Date.now()-60000,axiomPatientId:null,    trafficHistory:[20,22,25,18,30,24,21,26,23,25], destinationHistory:[5,6,7,5,8,6,7,5,6,7] },
  { ip:'10.0.1.12',deviceType:'federated_node', hospitalId:'hospital-C', trustScore:0.29, status:'UNTRUSTED',   lastThreat:Date.now()-3000, axiomPatientId:null,    trafficHistory:[40,45,200,300,280,290,310,285,295,305], destinationHistory:[2,3,15,20,18,19,21,17,20,18] },
  { ip:'10.0.0.3', deviceType:'axiom_service',  hospitalId:'hospital-A', trustScore:1.0,  status:'TRUSTED',     lastThreat:null,           axiomPatientId:null,    trafficHistory:[100,102,98,105,101,103,99,104,102,101], destinationHistory:[1,1,1,1,1,1,1,1,1,1] },
]

export const MOCK_THREATS: ThreatEvent[] = [
  { id:'t1', timestamp:Date.now()-30000,  severity:'HIGH',     type:'SYN_FLOOD',        srcIp:'192.168.1.50', destIp:'10.0.0.1',  hospitalId:'hospital-A', description:'SYN flood detected: 101 packets in 10s' },
  { id:'t2', timestamp:Date.now()-60000,  severity:'MEDIUM',   type:'GEO_BLOCK',        srcIp:'20.233.83.145',destIp:'10.0.0.2',  hospitalId:'hospital-B', description:'Traffic from blocked country: AE' },
  { id:'t3', timestamp:Date.now()-90000,  severity:'CRITICAL', type:'DATA_EXFILTRATION',srcIp:'10.0.0.5',    destIp:'1.2.3.4',   hospitalId:'hospital-A', description:'EHR exfiltration: 11.2MB in 5min' },
  { id:'t4', timestamp:Date.now()-120000, severity:'MEDIUM',   type:'PORT_SCAN',        srcIp:'10.0.0.8',    destIp:'10.0.0.9',  hospitalId:'hospital-C', description:'Port scan: 23 distinct ports' },
  { id:'t5', timestamp:Date.now()-150000, severity:'HIGH',     type:'FEDERATED_ATTACK', srcIp:'10.0.1.99',   destIp:'10.0.1.1',  hospitalId:'hospital-A', description:'Unknown node to Flower server' },
]

export const MOCK_CORRELATIONS: CorrelationEvent[] = [
  {
    id:'c1', type:'DEVICE_COMPROMISE_CLINICAL_IMPACT', severity:'HIGH',
    patientId:'pt-01', patientName:'Amit Singh', deviceIp:'10.0.0.5',
    summary:'ECG monitor trust dropped to 0.2 while patient showed creatinine spike',
    confidence:0.87, patientAnomalyTimeline:[], deviceThreatTimeline:[],
    overlapStart:Date.now()-300000, overlapEnd:Date.now(),
  },
  {
    id:'c2', type:'RANSOMWARE_PATIENT_RISK', severity:'CRITICAL',
    patientId:null, patientName:null, deviceIp:'10.0.0.8',
    summary:'EHR exfiltration in Hospital A — 3 patients at risk',
    confidence:0.95, patientAnomalyTimeline:[], deviceThreatTimeline:[],
    overlapStart:Date.now()-180000, overlapEnd:Date.now(),
    atRiskPatients:['pt-01','pt-02','pt-03'], hospitalId:'hospital-A',
  },
  {
    id:'c3', type:'FEDERATED_POISONING_CLINICAL_IMPACT', severity:'HIGH',
    patientId:'pt-05', patientName:'Priya Patel', deviceIp:'10.0.1.12',
    summary:'Byzantine node detected — recommendation CI widened for 2 patients',
    confidence:0.72, patientAnomalyTimeline:[], deviceThreatTimeline:[],
    overlapStart:Date.now()-600000, overlapEnd:Date.now(),
  },
]

// Random threat generator for live simulation
const THREAT_TYPES: ThreatEvent['type'][] = [
  'SYN_FLOOD','GEO_BLOCK','PORT_SCAN','BEACONING',
  'FEDERATED_ATTACK','DATA_EXFILTRATION','LATERAL_MOVEMENT'
]
const SEVERITIES: ThreatEvent['severity'][] = ['MEDIUM','MEDIUM','HIGH','HIGH','CRITICAL']
const HOSPITALS = ['hospital-A','hospital-B','hospital-C']
const SRC_IPS = ['192.168.1.50','10.0.0.5','10.0.0.8','20.233.83.145','10.0.1.99']
const DESCRIPTIONS: Record<string, string> = {
  SYN_FLOOD:        'SYN flood detected: {n} packets in 10s',
  GEO_BLOCK:        'Traffic from blocked country: {c}',
  PORT_SCAN:        'Port scan: {n} distinct ports',
  BEACONING:        'Beaconing detected: CV=0.08 requests={n}',
  FEDERATED_ATTACK: 'Unknown node to Flower server: 10.0.1.{n}',
  DATA_EXFILTRATION:'EHR exfiltration: {n}MB in 5min',
  LATERAL_MOVEMENT: 'Lateral movement: {n} distinct IPs in 60s',
}
const COUNTRIES = ['CN','RU','KP','IR','VN']

export function generateRandomThreat(): ThreatEvent {
  const type = THREAT_TYPES[Math.floor(Math.random() * THREAT_TYPES.length)]
  const sev  = SEVERITIES[Math.floor(Math.random() * SEVERITIES.length)]
  const n    = Math.floor(Math.random() * 100 + 20)
  const c    = COUNTRIES[Math.floor(Math.random() * COUNTRIES.length)]
  const desc = (DESCRIPTIONS[type] || type)
    .replace('{n}', String(n))
    .replace('{c}', c)

  return {
    id:          `t-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    timestamp:   Date.now(),
    severity:    sev,
    type,
    srcIp:       SRC_IPS[Math.floor(Math.random() * SRC_IPS.length)],
    destIp:      `10.0.${Math.floor(Math.random()*3)}.${Math.floor(Math.random()*10)+1}`,
    hospitalId:  HOSPITALS[Math.floor(Math.random() * HOSPITALS.length)],
    description: desc,
  }
}
