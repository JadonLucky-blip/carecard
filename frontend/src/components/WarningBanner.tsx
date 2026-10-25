import type { Source, WarningSign } from '../types'

const URGENCY_LABEL: Record<string, string> = {
  call_911: 'Call 911',
  go_to_ER: 'Go to the ER',
  call_doctor: 'Call your doctor',
}

interface WarningBannerProps {
  signs: WarningSign[]
  onShowSource: (source: Source) => void
}

export function WarningBanner({ signs, onShowSource }: WarningBannerProps) {
  if (signs.length === 0) {
    return (
      <section aria-labelledby="warning-heading" className="rounded-lg border-2 border-amber-400 bg-amber-50 p-4">
        <h2 id="warning-heading" className="text-xl font-bold text-amber-900">
          Warning signs
        </h2>
        <p className="mt-1 text-amber-900">
          Your papers don't list warning signs. Ask your care team.
        </p>
      </section>
    )
  }

  return (
    <section aria-labelledby="warning-heading" className="rounded-lg border-2 border-red-600 bg-red-50 p-4">
      <h2 id="warning-heading" className="text-xl font-bold text-red-800">
        Go back / call 911 if...
      </h2>
      <ul className="mt-2 space-y-2">
        {signs.map((sign, i) => (
          <li key={i} className="flex items-start gap-2">
            <span className="mt-0.5 shrink-0 rounded bg-red-600 px-2 py-0.5 text-xs font-bold uppercase tracking-wide text-white">
              {URGENCY_LABEL[sign.urgency] ?? sign.urgency}
            </span>
            <button
              type="button"
              onClick={() => onShowSource(sign.source)}
              className="text-left text-red-900 underline-offset-2 hover:underline"
            >
              {sign.text}
              {sign.grounding?.status === 'check' && (
                <span className="ml-2 text-xs font-normal text-amber-700">(please check)</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
