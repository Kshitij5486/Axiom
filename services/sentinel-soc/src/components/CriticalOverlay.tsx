import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSentinelStore } from '../store/sentinelStore'

export default function CriticalOverlay() {
  const { criticalFlash, setCriticalFlash, pinnedThreats } = useSentinelStore()
  const [showDismiss, setShowDismiss] = useState(false)

  useEffect(() => {
    if (criticalFlash) {
      setShowDismiss(true)
      const t = setTimeout(() => setShowDismiss(false), 5000)
      return () => clearTimeout(t)
    }
  }, [criticalFlash])

  return (
    <>
      <AnimatePresence>
        {criticalFlash && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 1, 0] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            style={{
              position: 'fixed', inset: 0,
              background: 'rgba(192,57,43,0.15)',
              pointerEvents: 'none', zIndex: 40,
            }}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showDismiss && (
          <motion.button
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ type: 'spring', damping: 20, stiffness: 300 }}
            onClick={() => { setShowDismiss(false); setCriticalFlash(false) }}
            style={{
              position: 'fixed', top: '80px', right: '24px', zIndex: 50,
              background: '#004953', color: '#F9F7F2',
              border: 'none', borderRadius: '117px',
              padding: '8px 16px', cursor: 'pointer',
              fontFamily: 'Inter Tight, sans-serif',
              fontSize: '11px', fontWeight: 700,
              letterSpacing: '0.1em', textTransform: 'uppercase',
              boxShadow: '0 10px 30px rgba(0,73,83,0.2)',
              display: 'flex', alignItems: 'center', gap: '6px',
            }}
          >
            <span style={{
              width: '6px', height: '6px', borderRadius: '50%',
              background: '#C0392B', animation: 'pulseLive 1s infinite',
            }} />
            CRITICAL ALERT — DISMISS
          </motion.button>
        )}
      </AnimatePresence>
    </>
  )
}
