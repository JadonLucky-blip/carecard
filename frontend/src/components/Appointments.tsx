import type { FollowUpAppointment, Source } from '../types'
import { downloadIcs } from '../ics'

interface AppointmentsProps {
  appointments: FollowUpAppointment[]
  onShowSource: (source: Source) => void
}

export function Appointments({ appointments, onShowSource }: AppointmentsProps) {
  if (appointments.length === 0) return null

  return (
    <section aria-labelledby="appt-heading" className="rounded-lg border p-4">
      <h2 id="appt-heading" className="text-xl font-bold text-gray-900">
        Follow-up appointments
      </h2>
      <ul className="mt-2 space-y-3">
        {appointments.map((appt, i) => (
          <li key={i} className="rounded border p-3">
            <button
              type="button"
              onClick={() => onShowSource(appt.source)}
              className="text-left font-semibold text-gray-900 underline-offset-2 hover:underline"
            >
              {appt.with || 'Follow-up appointment'}
            </button>
            <p className="text-sm text-gray-600">{appt.when}</p>
            <div className="mt-2 flex flex-wrap gap-3 text-sm">
              {appt.phone && (
                <a href={`tel:${appt.phone.replace(/[^\d+]/g, '')}`} className="font-medium text-teal-700 underline">
                  Call {appt.phone}
                </a>
              )}
              <button
                type="button"
                onClick={() => downloadIcs(appt)}
                className="font-medium text-teal-700 underline"
              >
                Add to calendar
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
