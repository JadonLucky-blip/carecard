import { useEffect, useMemo, useRef, useState } from 'react'

const MAX_PHOTOS = 6

interface PhotoUploadProps {
  onSubmit: (photos: File[]) => void
  busy: boolean
  error: string | null
}

export function PhotoUpload({ onSubmit, busy, error }: PhotoUploadProps) {
  const [photos, setPhotos] = useState<File[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  // Create preview URLs once per `photos` change, not once per render,
  // and revoke the old ones - otherwise every re-render leaks a blob URL.
  const previewUrls = useMemo(() => photos.map((p) => URL.createObjectURL(p)), [photos])
  useEffect(() => {
    return () => previewUrls.forEach((url) => URL.revokeObjectURL(url))
  }, [previewUrls])

  function addFiles(files: FileList | null) {
    if (!files) return
    const next = [...photos, ...Array.from(files)].slice(0, MAX_PHOTOS)
    setPhotos(next)
  }

  function removeAt(index: number) {
    setPhotos(photos.filter((_, i) => i !== index))
  }

  return (
    <main className="mx-auto max-w-xl px-4 py-8">
      <h1 className="text-3xl font-bold text-teal-800">CareCard</h1>
      <p className="mt-1 text-gray-700">
        Take a photo of your discharge papers to get a one-page plan: what
        medicine to take and when, warning signs that mean go back, and your
        next appointment.
      </p>

      <div className="mt-6 rounded-lg border-2 border-dashed border-teal-300 bg-teal-50 p-6 text-center">
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          capture="environment"
          multiple
          aria-label="Upload a photo of your discharge papers"
          className="sr-only"
          onChange={(e) => addFiles(e.target.files)}
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={photos.length >= MAX_PHOTOS}
          className="rounded-md bg-teal-700 px-5 py-3 text-lg font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
        >
          {photos.length === 0 ? 'Add a photo' : 'Add another photo'}
        </button>
        <p className="mt-2 text-sm text-gray-600">Up to {MAX_PHOTOS} photos, one per page.</p>
      </div>

      {photos.length > 0 && (
        <ul className="mt-4 grid grid-cols-3 gap-3" aria-label="Selected photos">
          {photos.map((_photo, i) => (
            <li key={i} className="relative">
              <img
                src={previewUrls[i]}
                alt={`Page ${i + 1} preview`}
                className="aspect-square w-full rounded-md border object-cover"
              />
              <button
                type="button"
                onClick={() => removeAt(i)}
                aria-label={`Remove page ${i + 1}`}
                className="absolute -right-2 -top-2 flex h-7 w-7 items-center justify-center rounded-full bg-gray-800 text-white"
              >
                &times;
              </button>
            </li>
          ))}
        </ul>
      )}

      {error && (
        <p role="alert" className="mt-4 rounded-md bg-red-50 p-3 text-red-800">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={() => onSubmit(photos)}
        disabled={photos.length === 0 || busy}
        aria-busy={busy}
        className="mt-6 w-full rounded-md bg-teal-700 px-5 py-3 text-lg font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
      >
        {busy ? 'Reading your papers...' : 'Create my card'}
      </button>
      {/* Visually hidden live region so screen reader users hear the status
          change even though it's conveyed visually by the button's own text. */}
      <p role="status" className="sr-only">
        {busy ? 'Reading your papers, please wait.' : ''}
      </p>

      <p className="mt-6 text-sm text-gray-500">
        Nothing is saved on a server. Your photos are processed and then
        discarded; your card lives only in this browser tab.
      </p>
    </main>
  )
}
