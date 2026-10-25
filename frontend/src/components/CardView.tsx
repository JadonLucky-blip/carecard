import { useState } from 'react'
import type { CareCardResult, Source } from '../types'
import { WarningBanner } from './WarningBanner'
import { MedsChecklist } from './MedsChecklist'
import { Appointments } from './Appointments'
import { HomeCareList } from './HomeCareList'
import { SourceHighlight } from './SourceHighlight'

interface CardViewProps {
  result: CareCardResult
  photoUrls: string[]
  onStartOver: () => void
}

export function CardView({ result, photoUrls, onStartOver }: CardViewProps) {
  const [activeSource, setActiveSource] = useState<Source | null>(null)
  const { card, grounding_score, schedules, ocr } = result

  return (
    <main className="mx-auto max-w-xl px-4 py-6 print:max-w-full">
      <div className="flex items-center justify-between print:hidden">
        <h1 className="text-2xl font-bold text-teal-800">Your CareCard</h1>
        <div className="flex gap-2">
          <button type="button" onClick={() => window.print()} className="rounded border px-3 py-1.5 text-sm font-medium hover:bg-gray-50">
            Print
          </button>
          <button type="button" onClick={onStartOver} className="rounded border px-3 py-1.5 text-sm font-medium hover:bg-gray-50">
            Start over
          </button>
        </div>
      </div>

      <p className="mt-1 text-sm text-gray-500 print:hidden" title="Share of extracted items that matched the exact text in your photos">
        Grounding score: {Math.round(grounding_score)}% of items traced directly to your papers
      </p>

      <div className="mt-4 space-y-4">
        {/* Spec requirement: the warning section always comes first, both
            visually and in reading/DOM order - it's the single most
            safety-critical thing on the card. */}
        <WarningBanner signs={card.return_now_warning_signs} onShowSource={setActiveSource} />

        {card.diagnosis_plain && (
          <section className="rounded-lg border p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Diagnosis</h2>
            <button
              type="button"
              onClick={() => setActiveSource(card.diagnosis_plain!.source)}
              className="mt-1 text-left text-lg font-semibold text-gray-900 underline-offset-2 hover:underline"
            >
              {card.diagnosis_plain.text}
            </button>
          </section>
        )}

        <MedsChecklist medications={card.medications} schedules={schedules} onShowSource={setActiveSource} />

        <Appointments appointments={card.follow_up_appointments} onShowSource={setActiveSource} />

        <HomeCareList
          instructions={card.home_care_instructions}
          limits={card.activity_and_diet_limits}
          onShowSource={setActiveSource}
        />
      </div>

      <footer className="mt-6 border-t pt-4 text-sm text-gray-500">
        CareCard helps you understand your instructions. It does not replace your doctor or pharmacist.
      </footer>

      {activeSource && (
        <SourceHighlight source={activeSource} pages={ocr.pages} photoUrls={photoUrls} onClose={() => setActiveSource(null)} />
      )}
    </main>
  )
}
