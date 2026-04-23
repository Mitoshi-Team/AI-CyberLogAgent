let lastCheckedAt = 0
let lastKnownReady = false

const CACHE_WINDOW_MS = 2000

export const checkBackendReady = async ({ force = false } = {}) => {
  const now = Date.now()
  if (!force && now - lastCheckedAt < CACHE_WINDOW_MS) {
    return lastKnownReady
  }

  try {
    const response = await fetch('/health', {
      method: 'GET',
      cache: 'no-store',
    })
    lastKnownReady = response.ok
  } catch {
    lastKnownReady = false
  }

  lastCheckedAt = now
  return lastKnownReady
}
