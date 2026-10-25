import { useEffect, useRef } from 'react'
import type { BoundingBox, OCRPage, Source } from '../types'

interface SourceHighlightProps {
  source: Source
  pages: OCRPage[]
  photoUrls: string[]
  onClose: () => void
}

function unionBox(boxes: BoundingBox[]): BoundingBox | null {
  if (boxes.length === 0) return null
  let x0 = boxes[0].x
  let y0 = boxes[0].y
  let x1 = boxes[0].x + boxes[0].width
  let y1 = boxes[0].y + boxes[0].height
  for (const b of boxes.slice(1)) {
    x0 = Math.min(x0, b.x)
    y0 = Math.min(y0, b.y)
    x1 = Math.max(x1, b.x + b.width)
    y1 = Math.max(y1, b.y + b.height)
  }
  return { x: x0, y: y0, width: x1 - x0, height: y1 - y0 }
}

export function SourceHighlight({ source, pages, photoUrls, onClose }: SourceHighlightProps) {
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    closeRef.current?.focus()
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose()
        return
      }
      // The close button is the only focusable element in this dialog, so
      // trapping focus just means Tab/Shift+Tab always lands back on it -
      // otherwise keyboard focus would escape to the card underneath while
      // the modal is still open.
      if (e.key === 'Tab') {
        e.preventDefault()
        closeRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const page = pages.find((p) => p.page_number === source.page)
  const photoUrl = photoUrls[source.page - 1]
  const box = page ? unionBox(page.lines.filter((l) => source.lines.includes(l.line_number) && l.bbox).map((l) => l.bbox!)) : null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Where this came from in your document"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-lg bg-white p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Where this came from</h2>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded px-2 text-2xl leading-none hover:bg-gray-100"
          >
            &times;
          </button>
        </div>
        <p className="mb-3 italic text-gray-700">"{source.quote}"</p>
        {photoUrl ? (
          <div className="relative inline-block w-full">
            <img src={photoUrl} alt={`Page ${source.page} of your discharge papers`} className="w-full rounded border" />
            {box && page && page.width > 0 && (
              <div
                className="absolute rounded-sm border-2 border-yellow-500"
                style={{
                  left: `${(box.x / page.width) * 100}%`,
                  top: `${(box.y / page.height) * 100}%`,
                  width: `${(box.width / page.width) * 100}%`,
                  height: `${(box.height / page.height) * 100}%`,
                  // A flat semi-transparent fill was washing out and
                  // obstructing the text underneath it, especially on
                  // dense documents. mix-blend-mode: multiply makes this
                  // behave like an actual highlighter pen instead - it
                  // tints the background yellow without ever making dark
                  // text harder to read (multiply only darkens, so text
                  // that was already dark stays dark).
                  backgroundColor: 'rgba(250, 204, 21, 0.55)',
                  mixBlendMode: 'multiply',
                }}
              />
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Photo for page {source.page} isn't available.</p>
        )}
      </div>
    </div>
  )
}
