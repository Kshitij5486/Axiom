import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import * as d3 from 'd3'
import { X } from 'lucide-react'
import { useSentinelStore } from '../store/sentinelStore'

function ConfidenceGauge({ value }: { value: number }) {
  const ref = useRef<SVGSVGElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const svg = d3.select(ref.current)
    svg.selectAll('*').remove()
    const r    = 40
    const arc  = d3.arc().innerRadius(r-8).outerRadius(r).startAngle(-Math.PI/2)
    const bg   = (arc as any)({ endAngle: Math.PI/2 })
    const fill = (arc as any)({ endAngle: -Math.PI/2 + Math.PI * value })
    svg.append('path').attr('d', bg).attr('fill','rgba(0,73,83,0.1)').attr('transform',`translate(50,55)`)
    svg.append('path').attr('d', fill).attr('fill','#004953').attr('transform',`translate(50,55)`)
    svg.append('text').text(`${Math.round(value*100)}%`)
      .attr('x',50).attr('y',60).attr('text-anchor','middle')
      .attr('font-family','Playfair Display, serif').attr('font-size','18px')
      .attr('font-weight','700').attr('fill','#3E2723')
    svg.append('text').text('confidence')
      .attr('x',50).attr('y',76).attr('text-anchor','middle')
      .attr('font-family','Albert Sans, sans-serif').attr('font-size','10px')
      .attr('fill','rgba(93,64,55,0.5)')
  }, [value])
  return <svg ref={ref} width="100" height="80" />
}

function DualTimeline({ patientEvents, deviceEvents, overlapStart, overlapEnd }: {
  patientEvents: any[]; deviceEvents: any[];
  overlapStart: number; overlapEnd: number
}) {
  const ref = useRef<SVGSVGElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const W = 500, H = 120
    const svg = d3.select(ref.current).attr('width', W).attr('height', H)
    svg.selectAll('*').remove()

    const now   = Date.now()
    const start = now - 600000
    const xScale = d3.scaleTime().domain([start, now]).range([40, W-20])

    // Overlap region
    svg.append('rect')
      .attr('x', xScale(overlapStart)).attr('y', 10)
      .attr('width', xScale(overlapEnd) - xScale(overlapStart))
      .attr('height', H - 20)
      .attr('fill', 'rgba(0,73,83,0.06)').attr('rx', 4)

    // Patient timeline (top)
    svg.append('text').text('Patient Anomalies')
      .attr('x', 40).attr('y', 32)
      .attr('font-family', 'Inter Tight, sans-serif').attr('font-size', '10px')
      .attr('fill', 'rgba(93,64,55,0.5)')
    svg.append('line')
      .attr('x1', 40).attr('y1', 42).attr('x2', W-20).attr('y2', 42)
      .attr('stroke', 'rgba(0,73,83,0.2)').attr('stroke-width', 1)

    // Device timeline (bottom)
    svg.append('text').text('Device Threats')
      .attr('x', 40).attr('y', 82)
      .attr('font-family', 'Inter Tight, sans-serif').attr('font-size', '10px')
      .attr('fill', 'rgba(93,64,55,0.5)')
    svg.append('line')
      .attr('x1', 40).attr('y1', 92).attr('x2', W-20).attr('y2', 92)
      .attr('stroke', 'rgba(0,73,83,0.2)').attr('stroke-width', 1)

    // Demo events on timelines
    const demoPatient = [now-400000, now-200000, now-100000]
    const demoDevice  = [now-350000, now-150000, now-50000]

    demoPatient.forEach(t => {
      svg.append('circle')
        .attr('cx', xScale(t)).attr('cy', 42).attr('r', 5)
        .attr('fill', '#D68910').attr('stroke', 'white').attr('stroke-width', 2)
    })

    demoDevice.forEach(t => {
      svg.append('circle')
        .attr('cx', xScale(t)).attr('cy', 92).attr('r', 5)
        .attr('fill', '#C0392B').attr('stroke', 'white').attr('stroke-width', 2)
    })

    // Connecting dashed lines between overlapping events
    svg.append('line')
      .attr('x1', xScale(now-200000)).attr('y1', 42)
      .attr('x2', xScale(now-150000)).attr('y2', 92)
      .attr('stroke', 'rgba(0,73,83,0.3)')
      .attr('stroke-dasharray', '3,3').attr('stroke-width', 1)

    // X axis ticks
    const axis = d3.axisBottom(xScale).ticks(5).tickFormat(d => {
      const date = new Date(d as number)
      return `${date.getHours()}:${String(date.getMinutes()).padStart(2,'0')}`
    })
    svg.append('g').attr('transform', `translate(0,${H-10})`).call(axis)
      .selectAll('text').attr('font-size', '9px').attr('fill', 'rgba(93,64,55,0.5)')
    svg.select('.domain').attr('stroke', 'rgba(0,73,83,0.2)')
    svg.selectAll('.tick line').attr('stroke', 'rgba(0,73,83,0.2)')
  }, [patientEvents, deviceEvents, overlapStart, overlapEnd])

  return <svg ref={ref} style={{ width: '100%' }} />
}

export default function CorrelationModal() {
  const { selectedCorrelation, setSelectedCorrelation } = useSentinelStore()
  if (!selectedCorrelation) return null
  const c = selectedCorrelation

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,73,83,0.2)',
          backdropFilter: 'blur(4px)', zIndex: 40,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
        onClick={() => setSelectedCorrelation(null)}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          onClick={e => e.stopPropagation()}
          style={{
            background: 'white', borderRadius: '18.8px',
            boxShadow: '0 8px 20px rgba(0,0,0,0.1)',
            border: '1px solid rgba(0,73,83,0.1)',
            padding: '32px', maxWidth: '640px', width: '90%',
            maxHeight: '85vh', overflowY: 'auto',
            position: 'relative',
          }}
        >
          {/* Close */}
          <button onClick={() => setSelectedCorrelation(null)} style={{
            position: 'absolute', top: '16px', right: '16px',
            background: '#F0ECE6', border: 'none', borderRadius: '50%',
            width: '32px', height: '32px', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#5D4037',
          }}><X size={14} /></button>

          {/* Header */}
          <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: '22px', fontStyle: 'italic', color: '#3E2723', marginBottom: '16px' }}>
            Correlation Detail
          </h2>

          {/* Badges */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
            <span style={{
              background: 'rgba(192,57,43,0.1)', color: '#C0392B',
              borderRadius: '117px', padding: '4px 12px',
              fontFamily: 'Inter Tight, sans-serif', fontSize: '10px', fontWeight: 700,
            }}>{c.type.replace(/_/g,' ')}</span>
            <span style={{
              background: 'rgba(214,137,16,0.1)', color: '#D68910',
              borderRadius: '117px', padding: '4px 12px',
              fontFamily: 'Inter Tight, sans-serif', fontSize: '10px', fontWeight: 700,
            }}>{c.severity}</span>
          </div>

          {/* Summary */}
          <p style={{
            fontFamily: 'Albert Sans, sans-serif', fontSize: '13px',
            color: '#5D4037', marginBottom: '24px', lineHeight: 1.6,
          }}>{c.summary}</p>

          {/* Dual timeline */}
          <div style={{
            background: '#F9F7F2', borderRadius: '12px',
            padding: '16px', marginBottom: '20px',
            border: '1px solid rgba(0,73,83,0.08)',
          }}>
            <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '10px', fontWeight: 700, color: 'rgba(93,64,55,0.4)', textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: '12px' }}>
              Event Timeline
            </div>
            <DualTimeline
              patientEvents={c.patientAnomalyTimeline}
              deviceEvents={c.deviceThreatTimeline}
              overlapStart={c.overlapStart}
              overlapEnd={c.overlapEnd}
            />
          </div>

          {/* Confidence gauge + info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px', marginBottom: '24px' }}>
            <ConfidenceGauge value={c.confidence} />
            <div>
              {c.patientId && (
                <div style={{ marginBottom: '8px' }}>
                  <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '10px', color: 'rgba(93,64,55,0.4)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Patient</div>
                  <div style={{ fontFamily: 'Playfair Display, serif', fontSize: '16px', color: '#3E2723' }}>{c.patientName || c.patientId}</div>
                </div>
              )}
              <div>
                <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '10px', color: 'rgba(93,64,55,0.4)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Device IP</div>
                <div style={{ fontFamily: 'monospace', fontSize: '14px', color: '#3E2723', fontWeight: 600 }}>{c.deviceIp}</div>
              </div>
            </div>
          </div>

          {/* At risk patients */}
          {c.atRiskPatients && c.atRiskPatients.length > 0 && (
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontFamily: 'Inter Tight, sans-serif', fontSize: '10px', fontWeight: 700, color: 'rgba(93,64,55,0.4)', textTransform: 'uppercase', letterSpacing: '0.2em', marginBottom: '8px' }}>
                At-Risk Patients ({c.atRiskPatients.length})
              </div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {c.atRiskPatients.map(pid => (
                  <span key={pid} style={{
                    background: 'rgba(192,57,43,0.08)', color: '#C0392B',
                    borderRadius: '117px', padding: '3px 10px',
                    fontFamily: 'monospace', fontSize: '11px',
                  }}>{pid}</span>
                ))}
              </div>
            </div>
          )}

          {/* View patient button */}
          {c.patientId && (
            <a href="https://axiom-dashboard-pi.vercel.app/dashboard.html" style={{
              display: 'block', background: '#004953', color: '#F9F7F2',
              border: 'none', borderRadius: '117px', padding: '14px 32px',
              fontFamily: 'Inter Tight, sans-serif', fontSize: '11px',
              fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em',
              textAlign: 'center', textDecoration: 'none',
              boxShadow: '0 10px 30px rgba(0,73,83,0.2)',
              transition: 'transform 0.2s cubic-bezier(0.16,1,0.3,1)',
            }}
              onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.05)')}
              onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
            >View Patient Dashboard</a>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
