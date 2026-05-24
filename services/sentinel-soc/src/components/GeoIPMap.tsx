import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import * as topojson from 'topojson-client'
import { useSentinelStore } from '../store/sentinelStore'

export default function GeoIPMap() {
  const svgRef      = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const projRef     = useRef<d3.GeoProjection | undefined>(undefined)
  const [countries, setCountries] = useState<Set<string>>(new Set())
  const { geoThreats } = useSentinelStore()

  // Load world map once
  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return
    const W = containerRef.current.clientWidth
    const H = 140

    const svg  = d3.select(svgRef.current).attr('width', W).attr('height', H)
    const proj = d3.geoNaturalEarth1().fitSize([W, H], { type: 'Sphere' })
    projRef.current = proj
    const path = d3.geoPath(proj)

    // Ocean background
    svg.append('rect').attr('width', W).attr('height', H).attr('fill', '#F9F7F2')

    fetch('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json')
      .then(r => r.json())
      .then((world: any) => {
        const countries = topojson.feature(world, world.objects.countries) as any
        svg.append('g').selectAll('path')
          .data(countries.features)
          .join('path')
          .attr('d', path as any)
          .attr('fill', '#F0ECE6')
          .attr('stroke', 'rgba(0,73,83,0.15)')
          .attr('stroke-width', 0.5)
        svg.append('g').attr('class', 'dots')
      })
  }, [])

  // Add geo threat dots — D3 enter/update/exit
  useEffect(() => {
    if (!svgRef.current || !projRef.current) return
    const proj = projRef.current
    const svg  = d3.select(svgRef.current)
    const dotsG = svg.select('g.dots')

    // Add new dots
    geoThreats.slice(0, 30).forEach(threat => {
      const coords = proj([threat.lng, threat.lat])
      if (!coords) return
      const [cx, cy] = coords

      // Pulse ring
      const pulse = dotsG.append('circle')
        .attr('cx', cx).attr('cy', cy)
        .attr('r', Math.min(3 + threat.packetCount / 100, 12))
        .attr('fill', '#C0392B').attr('opacity', 0.8)

      // Animate pulse ring
      dotsG.append('circle')
        .attr('cx', cx).attr('cy', cy)
        .attr('r', Math.min(3 + threat.packetCount / 100, 12))
        .attr('fill', 'none')
        .attr('stroke', '#C0392B').attr('stroke-width', 1.5)
        .attr('opacity', 0.8)
        .transition().duration(800)
        .ease(d3.easeCubicOut)
        .attr('r', Math.min(3 + threat.packetCount / 100, 12) * 2.5)
        .attr('opacity', 0)
        .remove()

      // Fade out dot after 10s
      pulse.transition().delay(10000).duration(500).attr('opacity', 0).remove()

      setCountries(prev => new Set([...prev, threat.country]))
    })
  }, [geoThreats])

  // Demo dots
  useEffect(() => {
    if (!svgRef.current || !projRef.current) return
    const demoThreats = [
      { lng: 55.3, lat: 25.2, country: 'AE', packetCount: 120 },
      { lng: 116.4, lat: 39.9, country: 'CN', packetCount: 80 },
      { lng: 37.6, lat: 55.7, country: 'RU', packetCount: 60 },
      { lng: -74.0, lat: 40.7, country: 'US', packetCount: 30 },
    ]
    const proj  = projRef.current
    const svg   = d3.select(svgRef.current)

    setTimeout(() => {
      const dotsG = svg.select('g.dots')
      demoThreats.forEach(t => {
        const coords = proj([t.lng, t.lat])
        if (!coords) return
        const [cx, cy] = coords
        dotsG.append('circle')
          .attr('cx', cx).attr('cy', cy)
          .attr('r', Math.min(3 + t.packetCount / 50, 10))
          .attr('fill', '#C0392B').attr('opacity', 0.7)
        setCountries(prev => new Set([...prev, t.country]))
      })
    }, 1000)
  }, [])

  return (
    <div ref={containerRef} style={{
      width: '100%', height: '180px',
      background: '#F9F7F2',
      borderTop: '1px solid rgba(0,73,83,0.08)',
      position: 'relative',
    }}>
      {/* Counter strip */}
      <div style={{
        position: 'absolute', top: '8px', left: '12px',
        background: 'white', borderRadius: '18.8px',
        boxShadow: '0 20px 40px rgba(62,39,35,0.05)',
        border: '1px solid rgba(0,73,83,0.08)',
        padding: '4px 12px',
        display: 'flex', alignItems: 'center', gap: '6px',
        zIndex: 10,
      }}>
        <span style={{ fontFamily: 'Albert Sans, sans-serif', fontSize: '11px', color: 'rgba(93,64,55,0.5)' }}>Blocked from</span>
        <span style={{ fontFamily: 'Playfair Display, serif', fontSize: '18px', fontWeight: 700, color: '#3E2723' }}>
          {countries.size}
        </span>
        <span style={{ fontFamily: 'Albert Sans, sans-serif', fontSize: '11px', color: 'rgba(93,64,55,0.5)' }}>countries</span>
      </div>
      <svg ref={svgRef} style={{ width: '100%', height: '140px', display: 'block', marginTop: '38px' }} />
    </div>
  )
}
