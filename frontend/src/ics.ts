import type { FollowUpAppointment } from './types'

/**
 * Discharge papers usually give a follow-up date as relative text
 * ("in 1 week") rather than a calendar date, and CareCard's "nothing is
 * invented" rule means we shouldn't silently assert a precise date we
 * weren't given. So this guesses a placeholder date from simple keywords
 * and always keeps the literal source text in the event title/description,
 * so the patient sees it's a guess and can correct it in their calendar.
 */
function guessDate(when: string): Date {
  const result = new Date()
  const lower = when.toLowerCase()

  if (lower.includes('tomorrow')) {
    result.setDate(result.getDate() + 1)
    return result
  }

  const match = lower.match(/(\d+)\s*(day|week|month)/)
  if (match) {
    const amount = parseInt(match[1], 10)
    const unit = match[2]
    if (unit === 'day') result.setDate(result.getDate() + amount)
    else if (unit === 'week') result.setDate(result.getDate() + amount * 7)
    else if (unit === 'month') result.setMonth(result.getMonth() + amount)
    return result
  }

  // No recognizable timeframe - default to one week out as a placeholder.
  result.setDate(result.getDate() + 7)
  return result
}

function formatIcsDate(d: Date): string {
  return d.toISOString().slice(0, 10).replace(/-/g, '')
}

function escapeIcsText(text: string): string {
  return text.replace(/\\/g, '\\\\').replace(/,/g, '\\,').replace(/\n/g, '\\n')
}

export function buildIcs(appt: FollowUpAppointment): string {
  const dateStr = formatIcsDate(guessDate(appt.when || ''))
  const who = appt.with || 'your care team'
  const summary = escapeIcsText(`Follow-up with ${who}`)
  const description = escapeIcsText(
    [
      `As written on your discharge papers: "${appt.when || 'no date given'}"`,
      appt.phone ? `Phone: ${appt.phone}` : '',
      "CareCard guessed this date from that text - please confirm with the office.",
    ]
      .filter(Boolean)
      .join('\n'),
  )

  return [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//CareCard//EN',
    'BEGIN:VEVENT',
    `UID:${crypto.randomUUID()}@carecard`,
    `DTSTAMP:${formatIcsDate(new Date())}T000000Z`,
    `DTSTART;VALUE=DATE:${dateStr}`,
    `SUMMARY:${summary}`,
    `DESCRIPTION:${description}`,
    'END:VEVENT',
    'END:VCALENDAR',
  ].join('\r\n')
}

export function downloadIcs(appt: FollowUpAppointment): void {
  const blob = new Blob([buildIcs(appt)], { type: 'text/calendar' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `carecard-followup-${(appt.with || 'appointment').replace(/\s+/g, '_')}.ics`
  link.click()
  URL.revokeObjectURL(url)
}
