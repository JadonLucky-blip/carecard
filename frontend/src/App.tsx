import { useState } from 'react'
import { PhotoUpload } from './components/PhotoUpload'
import { CardView } from './components/CardView'
import { processPhotos } from './api'
import type { CareCardResult } from './types'

function App() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CareCardResult | null>(null)
  const [photoUrls, setPhotoUrls] = useState<string[]>([])

  async function handleSubmit(photos: File[]) {
    setBusy(true)
    setError(null)
    try {
      const data = await processPhotos(photos)
      // Owned here (not in PhotoUpload) because CardView's source-highlight
      // view needs these same URLs after the upload step is done with them.
      setPhotoUrls(photos.map((p) => URL.createObjectURL(p)))
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  function startOver() {
    photoUrls.forEach((url) => URL.revokeObjectURL(url))
    setPhotoUrls([])
    setResult(null)
    setError(null)
  }

  if (result) {
    return <CardView result={result} photoUrls={photoUrls} onStartOver={startOver} />
  }

  return <PhotoUpload onSubmit={handleSubmit} busy={busy} error={error} />
}

export default App
