import type { CareCardResult } from './types'

// Points at the local FastAPI dev server. For the demo video, run both
// servers on the same laptop and open the frontend's network URL on a
// phone - the backend only needs to be reachable from that laptop.
const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export async function processPhotos(photos: File[]): Promise<CareCardResult> {
  const form = new FormData()
  for (const photo of photos) {
    form.append('photos', photo)
  }

  const response = await fetch(`${API_BASE}/api/process`, {
    method: 'POST',
    body: form,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`Couldn't process these photos (${response.status}): ${detail}`)
  }

  return response.json()
}
