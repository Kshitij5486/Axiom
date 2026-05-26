// In production (Vercel), use mock API
// In development, use real backend
export const IS_MOCK = (import.meta as any).env?.VITE_USE_MOCK === 'true' ||
                       (import.meta as any).env?.PROD

export const API_BASE = IS_MOCK
  ? ''  // mock — no real API calls
  : 'http://localhost:8090'

export const GRAPH_API = IS_MOCK
  ? ''
  : 'http://localhost:8091'

export const CORR_API = IS_MOCK
  ? ''
  : 'http://localhost:8092'
