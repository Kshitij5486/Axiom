import { useState, useEffect, useRef } from 'react'
import * as THREE from 'three'
import * as d3 from 'd3'
import { motion, AnimatePresence } from 'framer-motion'
import { useSentinelStore } from '../store/sentinelStore'
import type { Device } from '../types/sentinel'

const DEVICE_TYPE_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  ehr_system:     { bg: '#eff6ff', text: '#2563eb', border: '#bfdbfe' },
  medical_device: { bg: '#f0fdfa', text: '#0d9488', border: '#99f6e4' },
  workstation:    { bg: '#f8fafc', text: '#64748b', border: '#e2e8f0' },
  axiom_service:  { bg: '#faf5ff', text: '#9333ea', border: '#e9d5ff' },
  federated_node: { bg: '#fffbeb', text: '#d97706', border: '#fde68a' },
  unknown:        { bg: '#f8fafc', text: '#94a3b8', border: '#e2e8f0' },
}

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  TRUSTED:     { bg: 'rgba(30,132,73,0.1)',   text: '#1E8449' },
  LOW_TRUST:   { bg: 'rgba(214,137,16,0.1)',  text: '#D68910' },
  UNTRUSTED:   { bg: 'rgba(192,57,43,0.1)',   text: '#C0392B' },
  QUARANTINED: { bg: '#004953',               text: '#F9F7F2' },
}

const DEMO_DEVICES: Device[] = [
  { ip:'10.0.0.1', deviceType:'ehr_system',     hospitalId:'hospital-A', trustScore:0.95, status:'TRUSTED',     lastThreat:null,           axiomPatientId:null,    trafficHistory:[50,55,48,60,52], destinationHistory:[3,4,3,5,4] },
  { ip:'10.0.0.5', deviceType:'medical_device', hospitalId:'hospital-A', trustScore:0.2,  status:'UNTRUSTED',   lastThreat:Date.now()-5000, axiomPatientId:'pt-01', trafficHistory:[10,80,120,200,180], destinationHistory:[1,2,8,12,10] },
  { ip:'10.0.1.10',deviceType:'federated_node', hospitalId:'hospital-B', trustScore:0.8,  status:'TRUSTED',     lastThreat:null,           axiomPatientId:null,    trafficHistory:[30,32,28,35,31], destinationHistory:[2,2,1,2,2] },
  { ip:'10.0.0.8', deviceType:'workstation',    hospitalId:'hospital-C', trustScore:0.45, status:'LOW_TRUST',   lastThreat:Date.now()-60000,axiomPatientId:null,    trafficHistory:[20,22,25,18,30], destinationHistory:[5,6,7,5,8] },
  { ip:'10.0.1.12',deviceType:'federated_node', hospitalId:'hospital-C', trustScore:0.29, status:'UNTRUSTED',   lastThreat:Date.now()-3000, axiomPatientId:null,    trafficHistory:[40,45,200,300,280], destinationHistory:[2,3,15,20,18] },
  { ip:'10.0.0.3', deviceType:'axiom_service',  hospitalId:'hospital-A', trustScore:1.0,  status:'TRUSTED',     lastThreat:null,           axiomPatientId:null,    trafficHistory:[100,102,98,105,101], destinationHistory:[1,1,1,1,1] },
]

// SVG Trust Ring
function TrustRing({ score }: { score: number }) {
  const r    = 13
  const circ = 2 * Math.PI * r
  const dash = circ * score
  const color = score >= 0.7 ? '#1E8449' : score >= 0.3 ? '#D68910' : '#C0392B'

  return (
    <svg width="32" height="32" viewBox="-16 -16 32 32">
      <circle r={r} stroke="rgba(0,73,83,0.1)" strokeWidth="3" fill="none" />
      <circle
        r={r}
        stroke={color}
        strokeWidth="3"
        fill="none"
        strokeDasharray={`${dash} ${circ - dash}`}
        strokeDashoffset={circ / 4}
        strokeLinecap="round"
        style={{ transition: 'stroke-dasharray 0.8s cubic-bezier(0.16,1,0.3,1)' }}
      />
      <text
        textAnchor="middle"
        dominantBaseline="middle"
        fontSize="7"
        fontFamily="Playfair Display, serif"
        fontWeight="700"
        fill={color}
      >{Math.round(score * 10) / 10}</text>
    </svg>
  )
}

// Mini D3 sparkline
function Sparkline({ data, color = '#004953' }: { data: number[]; color?: string }) {
  const ref = useRef<SVGSVGElement>(null)
  useEffect(() => {
    if (!ref.current || data.length < 2) return
    const svg = d3.select(ref.current)
    svg.selectAll('*').remove()
    const W = 160, H = 36
    const x = d3.scaleLinear().domain([0, data.length-1]).range([0, W])
    const y = d3.scaleLinear().domain([0, Math.max(...data)]).range([H-2, 2])
    const line  = d3.line<number>().x((_,i)=>x(i)).y(d=>y(d)).curve(d3.curveCatmullRom)
    const area  = d3.area<number>().x((_,i)=>x(i)).y0(H).y1(d=>y(d)).curve(d3.curveCatmullRom)
    svg.append('path').datum(data).attr('d', area)
      .attr('fill', `${color}11`)
    svg.append('path').datum(data).attr('d', line)
      .attr('fill','none').attr('stroke', color).attr('stroke-width', 1.5)
  }, [data, color])
  return <svg ref={ref} width="160" height="36" />
}

// Mini Three.js graph for device neighbourhood
function MiniThreeGraph({ ip }: { ip: string }) {
  const mountRef = useRef<HTMLDivElement>(null)
  const { devices } = useSentinelStore()

  useEffect(() => {
    if (!mountRef.current) return
    const W = 200, H = 200
    const scene    = new THREE.Scene()
    scene.background = new THREE.Color('#F9F7F2')
    const camera   = new THREE.PerspectiveCamera(60, 1, 0.1, 100)
    camera.position.set(0, 0, 20)
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(W, H)
    mountRef.current.appendChild(renderer.domElement)
    scene.add(new THREE.AmbientLight(0xffffff, 1))

    // Central node
    const cGeo = new THREE.SphereGeometry(2, 12, 12)
    const cMat = new THREE.MeshPhongMaterial({ color: '#004953' })
    const center = new THREE.Mesh(cGeo, cMat)
    scene.add(center)

    // Neighbour nodes
    const neighbours = devices.slice(0, 5)
    neighbours.forEach((d, i) => {
      const angle = (i / neighbours.length) * Math.PI * 2
      const x = Math.cos(angle) * 7
      const z = Math.sin(angle) * 7
      const geo = new THREE.SphereGeometry(1.2, 8, 8)
      const mat = new THREE.MeshPhongMaterial({
        color: d.trustScore < 0.3 ? '#C0392B' : d.trustScore < 0.7 ? '#D68910' : '#1E8449'
      })
      const mesh = new THREE.Mesh(geo, mat)
      mesh.position.set(x, 0, z)
      scene.add(mesh)

      const pts = [new THREE.Vector3(0,0,0), new THREE.Vector3(x,0,z)]
      const lineGeo = new THREE.BufferGeometry().setFromPoints(pts)
      const lineMat = new THREE.LineBasicMaterial({ color: '#004953', transparent: true, opacity: 0.3 })
      scene.add(new THREE.Line(lineGeo, lineMat))
    })

    let raf = 0
    const animate = () => {
      raf = requestAnimationFrame(animate)
      scene.rotation.y += 0.008
      renderer.render(scene, camera)
    }
    animate()

    return () => {
      cancelAnimationFrame(raf)
      renderer.dispose()
      mountRef.current?.removeChild(renderer.domElement)
    }
  }, [ip, devices])

  return <div ref={mountRef} style={{ width: '200px', height: '200px', borderRadius: '12px', overflow: 'hidden' }} />
}

export default function DeviceRegistry() {
  const { devices, setSelectedDevice, quarantineDevice } = useSentinelStore()
  const [expanded, setExpanded] = useState<string | null>(null)
  const [sortBy,   setSortBy]   = useState<'trust' | 'type'>('trust')

  const allDevices = devices.length > 0 ? devices : DEMO_DEVICES
  const sorted = [...allDevices].sort((a, b) =>
    sortBy === 'trust' ? a.trustScore - b.trustScore : a.deviceType.localeCompare(b.deviceType)
  )

  const handleQuarantine = async (ip: string, e: React.MouseEvent) => {
    e.stopPropagation()
    quarantineDevice(ip)
    const btn = e.currentTarget as HTMLButtonElement
    btn.textContent = '✓ Quarantined'
    btn.style.background = '#1E8449'
    try { await fetch(`http://172.30.88.1:8090/sentinel/quarantine/${ip}`, { method: 'POST' }) } catch {}
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{
        background: 'white', borderBottom: '1px solid rgba(0,73,83,0.08)',
        padding: '12px 16px', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontFamily: 'Playfair Display, serif', fontSize: '14px', fontStyle: 'italic', color: '#3E2723' }}>
            Device Trust Registry
          </span>
          <span style={{
            background: 'rgba(0,73,83,0.08)', color: '#004953',
            borderRadius: '117px', padding: '2px 8px',
            fontFamily: 'Inter Tight, sans-serif', fontSize: '10px', fontWeight: 700,
          }}>{allDevices.length}</span>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          {[['trust','Trust Score'],['type','Device Type']].map(([v,l]) => (
            <button key={v} onClick={() => setSortBy(v as any)} style={{
              padding: '3px 10px', borderRadius: '117px', border: 'none',
              cursor: 'pointer', fontFamily: 'Inter Tight, sans-serif',
              fontSize: '9px', fontWeight: 700,
              background: sortBy === v ? '#004953' : '#F0ECE6',
              color: sortBy === v ? '#F9F7F2' : '#5D4037',
              transition: 'all 0.2s',
            }}>{l}</button>
          ))}
        </div>
      </div>

      {/* List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
        {sorted.map(device => {
          const typeStyle   = DEVICE_TYPE_STYLES[device.deviceType] || DEVICE_TYPE_STYLES.unknown
          const statusStyle = STATUS_STYLES[device.status] || STATUS_STYLES.TRUSTED
          const isExpanded  = expanded === device.ip

          return (
            <motion.div
              key={device.ip}
              layout
              onClick={() => { setExpanded(isExpanded ? null : device.ip); setSelectedDevice(device) }}
              style={{
                background: 'white', borderRadius: '18.8px',
                border: '1px solid rgba(0,73,83,0.08)',
                boxShadow: '0 20px 40px rgba(62,39,35,0.05)',
                padding: '14px', marginBottom: '10px', cursor: 'pointer',
              }}
            >
              {/* Row 1: IP + type badge */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontFamily: 'monospace', fontSize: '12px', fontWeight: 600, color: '#3E2723' }}>
                  {device.ip}
                </span>
                <span style={{
                  background: typeStyle.bg, color: typeStyle.text,
                  border: `1px solid ${typeStyle.border}`,
                  borderRadius: '117px', padding: '2px 7px',
                  fontFamily: 'Inter Tight, sans-serif', fontSize: '9px',
                  fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em',
                }}>{device.deviceType.replace(/_/g,' ')}</span>
              </div>

              {/* Row 2: hospital + last threat */}
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{
                  background: '#F0ECE6', color: '#5D4037',
                  borderRadius: '117px', padding: '2px 8px',
                  fontFamily: 'Inter Tight, sans-serif', fontSize: '10px',
                }}>{device.hospitalId || 'unknown'}</span>
                {device.lastThreat && (
                  <span style={{ fontFamily: 'Albert Sans, sans-serif', fontSize: '10px', color: 'rgba(93,64,55,0.4)' }}>
                    {new Date(device.lastThreat).toLocaleTimeString()}
                  </span>
                )}
              </div>

              {/* Row 3: trust ring + status */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <TrustRing score={device.trustScore} />
                <span style={{
                  background: statusStyle.bg, color: statusStyle.text,
                  borderRadius: '117px', padding: '3px 10px',
                  fontFamily: 'Inter Tight, sans-serif', fontSize: '9px',
                  fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em',
                }}>{device.status}</span>
              </div>

              {/* Expanded */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                    style={{ overflow: 'hidden' }}
                  >
                    <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid rgba(0,73,83,0.08)' }}>
                      {/* Sparklines */}
                      <div style={{ marginBottom: '8px' }}>
                        <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '9px', color: 'rgba(93,64,55,0.4)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.15em' }}>Packet Rate</div>
                        <Sparkline data={device.trafficHistory} color="#004953" />
                      </div>
                      <div style={{ marginBottom: '12px' }}>
                        <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '9px', color: 'rgba(93,64,55,0.4)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.15em' }}>Unique Destinations</div>
                        <Sparkline data={device.destinationHistory} color="#14b8a6" />
                      </div>

                      {/* Patient link */}
                      {device.axiomPatientId && (
                        <div style={{
                          background: '#F0ECE6', borderRadius: '12px',
                          border: '1px solid rgba(0,73,83,0.08)', padding: '10px',
                          marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '10px',
                        }}>
                          <div style={{
                            width: '32px', height: '32px', borderRadius: '50%',
                            background: '#004953', display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontFamily: 'Playfair Display, serif', fontSize: '14px', color: '#F9F7F2', fontWeight: 700,
                          }}>{device.axiomPatientId.slice(0,2).toUpperCase()}</div>
                          <div>
                            <div style={{ fontFamily: 'Playfair Display, serif', fontSize: '13px', color: '#3E2723' }}>
                              Patient {device.axiomPatientId}
                            </div>
                            <a href="https://axiom-dashboard-pi.vercel.app/dashboard.html" style={{
                              fontFamily: 'Inter Tight, sans-serif', fontSize: '10px',
                              color: '#004953', textDecoration: 'none', fontWeight: 600,
                            }}>View clinical dashboard →</a>
                          </div>
                        </div>
                      )}

                      {/* Mini Three.js graph */}
                      <div style={{ marginBottom: '10px' }}>
                        <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '9px', color: 'rgba(93,64,55,0.4)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.15em' }}>Causal Neighbourhood</div>
                        <MiniThreeGraph ip={device.ip} />
                      </div>

                      {/* Quarantine */}
                      {device.status !== 'QUARANTINED' && (
                        <button onClick={(e) => handleQuarantine(device.ip, e)} style={{
                          width: '100%', background: '#C0392B', color: 'white',
                          border: 'none', borderRadius: '117px', padding: '8px',
                          cursor: 'pointer', fontFamily: 'Inter Tight, sans-serif',
                          fontSize: '10px', fontWeight: 700, textTransform: 'uppercase',
                          letterSpacing: '0.1em', boxShadow: '0 10px 30px rgba(0,73,83,0.2)',
                          transition: 'transform 0.2s',
                        }}
                          onMouseEnter={e=>(e.currentTarget.style.transform='scale(1.05)')}
                          onMouseLeave={e=>(e.currentTarget.style.transform='scale(1)')}
                        >Quarantine Device</button>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
