import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { useSentinelStore } from '../store/sentinelStore'

export default function D3Heatmap({ width, height }: { width: number; height: number }) {
  const svgRef  = useRef<SVGSVGElement>(null)
  const { devices, threats } = useSentinelStore()

  useEffect(() => {
    if (!svgRef.current || devices.length === 0) return
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    // Count threats per device IP
    const threatCount: Record<string, number> = {}
    threats.forEach(t => {
      threatCount[t.srcIp] = (threatCount[t.srcIp] || 0) + 1
    })

    const maxThreats = Math.max(...Object.values(threatCount), 1)
    const colorScale = d3.scaleSequential()
      .domain([0, maxThreats])
      .interpolator(d3.interpolateRgb('#F0ECE6', '#C0392B'))

    // D3 force simulation
    const nodes = devices.map((d, i) => ({
      id:          d.ip,
      deviceType:  d.deviceType,
      trustScore:  d.trustScore,
      threats:     threatCount[d.ip] || 0,
      r:           6 + Math.min((d.trafficHistory[d.trafficHistory.length-1] || 10) / 10, 8),
    }))

    const sim = d3.forceSimulation(nodes as any)
      .force('charge', d3.forceManyBody().strength(-80))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius((d: any) => d.r + 4))
      .stop()

    // Run simulation
    for (let i = 0; i < 120; i++) sim.tick()

    // Draw edges
    const g = svg.append('g')
    devices.forEach((d, i) => {
      if (i === 0) return
      const a = (nodes as any)[i]
      const b = (nodes as any)[i - 1]
      if (!a || !b) return
      g.append('line')
        .attr('x1', a.x).attr('y1', a.y)
        .attr('x2', b.x).attr('y2', b.y)
        .attr('stroke', 'rgba(0,73,83,0.15)')
        .attr('stroke-width', 1)
    })

    // Draw nodes
    const nodeG = svg.selectAll('g.node')
      .data(nodes as any[])
      .join('g')
      .attr('class', 'node')
      .attr('transform', (d: any) => `translate(${d.x},${d.y})`)

    nodeG.append('circle')
      .attr('r', (d: any) => d.r)
      .attr('fill', (d: any) => colorScale(d.threats))
      .attr('stroke', 'rgba(0,73,83,0.3)')
      .attr('stroke-width', 1)

    nodeG.append('text')
      .text((d: any) => d.id.split('.').slice(-1)[0])
      .attr('text-anchor', 'middle')
      .attr('dy', (d: any) => d.r + 11)
      .attr('font-family', 'Inter Tight, sans-serif')
      .attr('font-size', '10px')
      .attr('fill', '#3E2723')

    // Color scale legend
    const legendW = 180
    const defs    = svg.append('defs')
    const grad    = defs.append('linearGradient').attr('id', 'heatLegend')
    grad.append('stop').attr('offset', '0%').attr('stop-color', '#F0ECE6')
    grad.append('stop').attr('offset', '100%').attr('stop-color', '#C0392B')

    const lx = width / 2 - legendW / 2
    const ly = height - 28

    svg.append('rect')
      .attr('x', lx).attr('y', ly)
      .attr('width', legendW).attr('height', 8)
      .attr('rx', 4).attr('fill', 'url(#heatLegend)')

    svg.append('text').text('0 threats/hr')
      .attr('x', lx).attr('y', ly + 20)
      .attr('font-family', 'Albert Sans, sans-serif')
      .attr('font-size', '10px').attr('fill', '#5D4037')

    svg.append('text').text('50+ threats/hr')
      .attr('x', lx + legendW).attr('y', ly + 20)
      .attr('font-family', 'Albert Sans, sans-serif')
      .attr('font-size', '10px').attr('fill', '#5D4037')
      .attr('text-anchor', 'end')

  }, [devices, threats, width, height])

  return <svg ref={svgRef} width={width} height={height} />
}
