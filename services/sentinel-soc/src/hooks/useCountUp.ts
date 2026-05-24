import { useEffect, useRef, useState } from 'react'

export function useCountUp(target: number, duration = 300): number {
  const [value, setValue] = useState(target)
  const prev = useRef(target)
  const raf  = useRef(0)

  useEffect(() => {
    const start    = prev.current
    const startTime = performance.now()
    const animate  = (now: number) => {
      const p = Math.min((now - startTime) / duration, 1)
      const e = 1 - Math.pow(1 - p, 3)
      setValue(Math.round(start + (target - start) * e))
      if (p < 1) raf.current = requestAnimationFrame(animate)
      else prev.current = target
    }
    cancelAnimationFrame(raf.current)
    raf.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(raf.current)
  }, [target, duration])

  return value
}
