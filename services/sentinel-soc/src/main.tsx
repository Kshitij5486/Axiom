import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { useSentinelStore } from './store/sentinelStore'
;(window as any).__sentinelStore = useSentinelStore

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
