import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { useSentinelStore } from '../store/sentinelStore'

const DEVICE_COLORS: Record<string, string> = {
  ehr_system:     '#3b82f6',
  medical_device: '#14b8a6',
  workstation:    '#64748b',
  axiom_service:  '#a855f7',
  federated_node: '#f59e0b',
  unknown:        '#94a3b8',
}

const THREAT_IP_COLOR = '#C0392B'

interface NodeMesh {
  ip:        string
  mesh:      THREE.Mesh
  glow:      THREE.Mesh
  trustScore: number
  deviceType: string
}

export default function ThreeScene() {
  const mountRef   = useRef<HTMLDivElement>(null)
  const sceneRef   = useRef<THREE.Scene | undefined>(undefined)
  const cameraRef  = useRef<THREE.PerspectiveCamera | undefined>(undefined)
  const rendererRef = useRef<THREE.WebGLRenderer | undefined>(undefined)
  const controlsRef = useRef<OrbitControls | undefined>(undefined)
  const nodesRef   = useRef<Map<string, NodeMesh>>(new Map())
  const rafRef     = useRef<number>(0)
  const idleTimer  = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const [heatmap, setHeatmap] = useState(false)

  const { devices, threats, highlightedNodeIp, heatmapMode, setHeatmapMode } = useSentinelStore()

  useEffect(() => {
    if (!mountRef.current) return
    const W = mountRef.current.clientWidth
    const H = mountRef.current.clientHeight

    // Scene
    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#F9F7F2')
    scene.fog = new THREE.Fog('#F9F7F2', 120, 300)
    sceneRef.current = scene

    // Camera
    const camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 1000)
    camera.position.set(0, 30, 80)
    cameraRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(W, H)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    mountRef.current.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Lights
    scene.add(new THREE.AmbientLight(0xffffff, 0.7))
    const dir = new THREE.DirectionalLight(0xffffff, 0.9)
    dir.position.set(60, 60, 60)
    scene.add(dir)

    // OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.autoRotate    = true
    controls.autoRotateSpeed = 0.2
    controlsRef.current = controls

    // Stop auto-rotate on interaction, resume after 5s
    const stopRotate = () => {
      controls.autoRotate = false
      clearTimeout(idleTimer.current)
      idleTimer.current = setTimeout(() => { controls.autoRotate = true }, 5000)
    }
    renderer.domElement.addEventListener('pointerdown', stopRotate)

    // Hospital segment spheres (3 segments)
    const segmentPositions = [
      new THREE.Vector3(-30, 0, 0),
      new THREE.Vector3(30, 0, 0),
      new THREE.Vector3(0, 0, -40),
    ]
    segmentPositions.forEach((pos, i) => {
      const geo = new THREE.SphereGeometry(18, 32, 32)
      const mat = new THREE.MeshPhongMaterial({
        color: new THREE.Color('#004953'),
        transparent: true, opacity: 0.06,
        side: THREE.DoubleSide,
      })
      const mesh = new THREE.Mesh(geo, mat)
      mesh.position.copy(pos)
      scene.add(mesh)

      // Segment label ring
      const ringGeo = new THREE.TorusGeometry(18, 0.3, 8, 64)
      const ringMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color('#004953'), transparent: true, opacity: 0.2
      })
      const ring = new THREE.Mesh(ringGeo, ringMat)
      ring.position.copy(pos)
      ring.rotation.x = Math.PI / 2
      scene.add(ring)
    })

    // Animate
    let t = 0
    const animate = () => {
      rafRef.current = requestAnimationFrame(animate)
      t += 0.01
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // Resize
    const onResize = () => {
      if (!mountRef.current) return
      const w = mountRef.current.clientWidth
      const h = mountRef.current.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(rafRef.current)
      window.removeEventListener('resize', onResize)
      renderer.domElement.removeEventListener('pointerdown', stopRotate)
      clearTimeout(idleTimer.current)
      renderer.dispose()
      mountRef.current?.removeChild(renderer.domElement)
    }
  }, [])

  // Add/update device nodes when devices change
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene) return

    const segmentPositions = [
      new THREE.Vector3(-30, 0, 0),
      new THREE.Vector3(30, 0, 0),
      new THREE.Vector3(0, 0, -40),
    ]

    devices.forEach((device, i) => {
      const existing = nodesRef.current.get(device.ip)
      const segIdx   = i % 3
      const angle    = (i / Math.max(devices.length, 1)) * Math.PI * 2
      const radius   = 10 + (i % 4) * 2
      const pos = new THREE.Vector3(
        segmentPositions[segIdx].x + Math.cos(angle) * radius,
        (i % 3 - 1) * 4,
        segmentPositions[segIdx].z + Math.sin(angle) * radius,
      )

      if (!existing) {
        const color = device.trustScore < 0.3 ? THREAT_IP_COLOR
                    : DEVICE_COLORS[device.deviceType] || '#94a3b8'

        // Main node sphere
        const size = 3 + Math.min(device.trafficHistory.reduce((a,b)=>a+b,0)/2000, 4)
        const geo  = new THREE.SphereGeometry(size, 16, 16)
        const mat  = new THREE.MeshPhongMaterial({
          color: new THREE.Color(color),
          transparent: true, opacity: 0.85, shininess: 60,
        })
        const mesh = new THREE.Mesh(geo, mat)
        mesh.position.copy(pos)
        scene.add(mesh)

        // Trust glow sphere
        const trustColor = device.trustScore >= 1.0 ? '#1E8449'
                         : device.trustScore >= 0.3 ? '#D68910' : '#C0392B'
        const glowOpacity = device.trustScore >= 1.0 ? 0
                          : (1 - device.trustScore) * 0.4
        const glowGeo = new THREE.SphereGeometry(size * 1.3, 16, 16)
        const glowMat = new THREE.MeshBasicMaterial({
          color: new THREE.Color(trustColor),
          transparent: true, opacity: glowOpacity,
        })
        const glow = new THREE.Mesh(glowGeo, glowMat)
        glow.position.copy(pos)
        scene.add(glow)

        nodesRef.current.set(device.ip, {
          ip: device.ip, mesh, glow,
          trustScore: device.trustScore,
          deviceType: device.deviceType,
        })
      } else {
        // Update trust glow
        const trustColor = device.trustScore >= 1.0 ? '#1E8449'
                         : device.trustScore >= 0.3 ? '#D68910' : '#C0392B';
        (existing.glow.material as THREE.MeshBasicMaterial).color.set(trustColor);
        (existing.glow.material as THREE.MeshBasicMaterial).opacity =
          device.trustScore >= 1.0 ? 0 : (1 - device.trustScore) * 0.4
      }
    })

    // Draw edges between peers
    devices.forEach((device, i) => {
      const nodeA = nodesRef.current.get(device.ip)
      if (!nodeA) return
      // Connect to 2 nearest nodes
      const others = devices.slice(Math.max(0,i-2), i)
      others.forEach(other => {
        const nodeB = nodesRef.current.get(other.ip)
        if (!nodeB) return
        const pts = [nodeA.mesh.position, nodeB.mesh.position]
        const geo  = new THREE.BufferGeometry().setFromPoints(pts)
        const mat  = new THREE.LineBasicMaterial({
          color: new THREE.Color('#004953'),
          transparent: true, opacity: 0.15,
        })
        scene.add(new THREE.Line(geo, mat))
      })
    })
  }, [devices])

  // Highlight node on click
  useEffect(() => {
    if (!highlightedNodeIp) return
    const node = nodesRef.current.get(highlightedNodeIp)
    if (!node || !cameraRef.current || !controlsRef.current) return
    const target = node.mesh.position.clone()
    controlsRef.current.target.copy(target)
    // Pulse scale
    let scale = 1
    const pulse = setInterval(() => {
      scale = scale === 1 ? 1.3 : 1
      node.mesh.scale.setScalar(scale)
    }, 200)
    setTimeout(() => {
      clearInterval(pulse)
      node.mesh.scale.setScalar(1)
    }, 1200)
  }, [highlightedNodeIp])

  // Threat pulse — InstancedMesh
  useEffect(() => {
    const scene = sceneRef.current
    if (!scene || threats.length === 0) return
    const latest = threats[0]
    const nodeA = nodesRef.current.get(latest.srcIp)
    const nodeB = nodesRef.current.get(latest.destIp)
    if (!nodeA || !nodeB) return

    const color = latest.severity === 'CRITICAL' ? '#ffffff'
                : latest.severity === 'HIGH' ? '#C0392B' : '#D68910'
    const geo = new THREE.SphereGeometry(1.5, 8, 8)
    const mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(color), transparent: true, opacity: 0.9
    })
    const pulse = new THREE.Mesh(geo, mat)
    pulse.position.copy(nodeA.mesh.position)
    scene.add(pulse)

    const srcPos = nodeA.mesh.position.clone()
    const dstPos = nodeB.mesh.position.clone()
    const start  = performance.now()
    const dur    = 1000

    const animatePulse = () => {
      const t = Math.min((performance.now() - start) / dur, 1)
      pulse.position.lerpVectors(srcPos, dstPos, t)
      if (t < 1) {
        requestAnimationFrame(animatePulse)
      } else {
        scene.remove(pulse)
        // Shift source node color toward danger
        const nodeMat = nodeA.mesh.material as THREE.MeshPhongMaterial
        nodeMat.color.lerp(new THREE.Color('#C0392B'), 0.1)
      }
    }
    requestAnimationFrame(animatePulse)
  }, [threats])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={mountRef} style={{ width: '100%', height: '100%' }} />

      {/* Heatmap toggle */}
      <button
        onClick={() => setHeatmapMode(!heatmapMode)}
        style={{
          position: 'absolute', top: '12px', right: '12px',
          background: heatmapMode ? '#004953' : '#F0ECE6',
          border: '1px solid rgba(0,73,83,0.15)',
          borderRadius: '117px', padding: '6px 14px',
          fontFamily: 'Inter Tight, sans-serif',
          fontSize: '10px', fontWeight: 700,
          textTransform: 'uppercase', letterSpacing: '0.15em',
          color: heatmapMode ? '#F9F7F2' : '#004953',
          cursor: 'pointer',
          transition: 'all 0.3s cubic-bezier(0.16,1,0.3,1)',
        }}
      >
        {heatmapMode ? '3D View' : 'Heat Map'}
      </button>

      {/* Node legend */}
      <div style={{
        position: 'absolute', bottom: '12px', left: '12px',
        display: 'flex', gap: '8px', flexWrap: 'wrap',
      }}>
        {Object.entries(DEVICE_COLORS).filter(([k]) => k !== 'unknown').map(([type, color]) => (
          <div key={type} style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            background: 'rgba(249,247,242,0.9)', borderRadius: '117px',
            padding: '3px 8px', border: '1px solid rgba(0,73,83,0.1)',
          }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: color }} />
            <span style={{
              fontFamily: 'Inter Tight, sans-serif', fontSize: '9px',
              fontWeight: 600, color: '#5D4037', textTransform: 'uppercase',
              letterSpacing: '0.1em',
            }}>{type.replace('_', ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
