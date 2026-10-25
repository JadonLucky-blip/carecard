import type { ActivityDietLimit, HomeCareInstruction, Source } from '../types'

interface HomeCareListProps {
  instructions: HomeCareInstruction[]
  limits: ActivityDietLimit[]
  onShowSource: (source: Source) => void
}

export function HomeCareList({ instructions, limits, onShowSource }: HomeCareListProps) {
  const items = [...instructions, ...limits]
  if (items.length === 0) return null

  return (
    <section aria-labelledby="homecare-heading" className="rounded-lg border p-4">
      <h2 id="homecare-heading" className="text-xl font-bold text-gray-900">
        Home care &amp; limits
      </h2>
      <ul className="mt-2 list-disc space-y-1 pl-5">
        {items.map((item, i) => (
          <li key={i}>
            <button
              type="button"
              onClick={() => onShowSource(item.source)}
              className="text-left text-gray-800 underline-offset-2 hover:underline"
            >
              {item.text}
            </button>
            {item.grounding?.status === 'check' && (
              <span className="ml-2 text-xs text-amber-700">(please check)</span>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
