import { useState } from 'react'
import type { Medication, ScheduleEntry, Source } from '../types'

const BUCKET_LABELS: [string, string][] = [
  ['morning', 'Morning'],
  ['midday', 'Midday'],
  ['evening', 'Evening'],
  ['bedtime', 'Bedtime'],
]

function bucketFor(time: string): string {
  const hour = Number(time.split(':')[0] ?? 0)
  if (hour < 12) return 'morning'
  if (hour < 17) return 'midday'
  if (hour < 21) return 'evening'
  return 'bedtime'
}

interface MedsChecklistProps {
  medications: Medication[]
  schedules: ScheduleEntry[]
  onShowSource: (source: Source) => void
}

export function MedsChecklist({ medications, schedules, onShowSource }: MedsChecklistProps) {
  const [taken, setTaken] = useState<Set<string>>(new Set())

  function toggle(key: string) {
    setTaken((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const scheduleByMed = new Map<number, ScheduleEntry>()
  schedules.forEach((s) => scheduleByMed.set(s.medication_index, s))

  const buckets: Record<string, { med: Medication; medIndex: number; time: string }[]> = {
    morning: [],
    midday: [],
    evening: [],
    bedtime: [],
  }
  const asNeeded: { med: Medication; medIndex: number }[] = []
  const unparsed: { med: Medication; medIndex: number }[] = []

  medications.forEach((med, medIndex) => {
    const schedule = scheduleByMed.get(medIndex)
    if (!schedule || schedule.unparsed) {
      unparsed.push({ med, medIndex })
      return
    }
    if (schedule.as_needed) {
      asNeeded.push({ med, medIndex })
      return
    }
    schedule.times_of_day.forEach((time) => {
      buckets[bucketFor(time)].push({ med, medIndex, time })
    })
  })

  return (
    <section aria-labelledby="meds-heading" className="rounded-lg border p-4">
      <h2 id="meds-heading" className="text-xl font-bold text-gray-900">
        Today's medicines
      </h2>

      {medications.length === 0 && (
        <p className="mt-1 text-gray-600">No medications are listed in your papers.</p>
      )}

      {BUCKET_LABELS.map(
        ([key, label]) =>
          buckets[key].length > 0 && (
            <div key={key} className="mt-4">
              <h3 className="font-semibold text-teal-800">{label}</h3>
              <ul className="mt-1 space-y-2">
                {buckets[key].map(({ med, medIndex, time }) => (
                  <MedRow
                    key={`${medIndex}-${time}`}
                    med={med}
                    time={time}
                    checked={taken.has(`${medIndex}-${time}`)}
                    onToggle={() => toggle(`${medIndex}-${time}`)}
                    onShowSource={onShowSource}
                  />
                ))}
              </ul>
            </div>
          ),
      )}

      {asNeeded.length > 0 && (
        <div className="mt-4">
          <h3 className="font-semibold text-teal-800">As needed</h3>
          <ul className="mt-1 space-y-2">
            {asNeeded.map(({ med, medIndex }) => (
              <MedRow
                key={medIndex}
                med={med}
                checked={false}
                onToggle={() => {}}
                onShowSource={onShowSource}
                hideCheckbox
                note={
                  scheduleByMed.get(medIndex)?.max_per_day
                    ? `Up to ${scheduleByMed.get(medIndex)?.max_per_day} times a day`
                    : undefined
                }
              />
            ))}
          </ul>
        </div>
      )}

      {unparsed.length > 0 && (
        <div className="mt-4">
          <h3 className="font-semibold text-amber-800">Check with your pharmacist</h3>
          <ul className="mt-1 space-y-2">
            {unparsed.map(({ med, medIndex }) => (
              <MedRow key={medIndex} med={med} checked={false} onToggle={() => {}} onShowSource={onShowSource} hideCheckbox />
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

interface MedRowProps {
  med: Medication
  time?: string
  checked: boolean
  onToggle: () => void
  onShowSource: (source: Source) => void
  note?: string
  hideCheckbox?: boolean
}

function MedRow({ med, time, checked, onToggle, onShowSource, note, hideCheckbox }: MedRowProps) {
  return (
    <li className="flex items-start gap-3 rounded border p-2">
      {!hideCheckbox && (
        <input
          type="checkbox"
          checked={checked}
          onChange={onToggle}
          aria-label={`Mark ${med.name_as_written}${time ? ` at ${time}` : ''} as taken`}
          className="mt-1 h-5 w-5 accent-teal-700"
        />
      )}
      <div className="flex-1">
        <div className="flex flex-wrap items-center gap-2">
          {time && <span className="font-mono text-sm text-gray-500">{time}</span>}
          <button
            type="button"
            onClick={() => onShowSource(med.source)}
            className="text-left font-semibold text-gray-900 underline-offset-2 hover:underline"
          >
            {med.name_as_written}
          </button>
          {med.new_changed_or_stopped && med.new_changed_or_stopped !== 'continue' && (
            <span className="rounded bg-teal-100 px-1.5 py-0.5 text-xs font-medium text-teal-800">
              {med.new_changed_or_stopped}
            </span>
          )}
          {med.grounding?.status === 'check' && <span className="text-xs text-amber-700">(please check)</span>}
        </div>
        <p className="text-sm text-gray-600">
          {[med.dose, med.route, med.frequency_as_written].filter(Boolean).join(' · ')}
          {med.purpose && ` — for ${med.purpose}`}
        </p>
        {note && <p className="text-sm text-gray-500">{note}</p>}
      </div>
    </li>
  )
}
