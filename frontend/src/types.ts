// Mirrors backend/app/schema.py exactly - keep the two in sync by hand,
// there's no codegen step in the 6-hour build.

export interface Source {
  page: number
  lines: number[]
  quote: string
}

export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

export type GroundingStatus = 'pass' | 'check' | 'dropped'

export interface GroundingResult {
  status: GroundingStatus
  match_score: number
}

interface Groundable {
  source: Source
  grounding?: GroundingResult | null
}

export interface DiagnosisPlain extends Groundable {
  text: string
}

export type MedChangeStatus = 'new' | 'changed' | 'stopped' | 'continue'

export interface Medication extends Groundable {
  name_as_written: string
  dose: string
  route: string
  frequency_as_written: string
  duration: string
  purpose: string
  new_changed_or_stopped?: MedChangeStatus | null
}

export type UrgencyLevel = 'call_911' | 'go_to_ER' | 'call_doctor'

export interface WarningSign extends Groundable {
  text: string
  urgency: UrgencyLevel
}

export interface FollowUpAppointment extends Groundable {
  with: string
  when: string
  phone: string
}

export interface HomeCareInstruction extends Groundable {
  text: string
}

export interface ActivityDietLimit extends Groundable {
  text: string
}

export interface ExtractedCard {
  diagnosis_plain: DiagnosisPlain | null
  medications: Medication[]
  return_now_warning_signs: WarningSign[]
  follow_up_appointments: FollowUpAppointment[]
  home_care_instructions: HomeCareInstruction[]
  activity_and_diet_limits: ActivityDietLimit[]
}

export interface ScheduleEntry {
  medication_index: number
  times_of_day: string[]
  start_date: string | null
  end_date: string | null
  as_needed: boolean
  max_per_day: number | null
  with_food: boolean
  unparsed: boolean
  generic_name: string | null
  brand_name: string | null
}

export interface OCRLine {
  line_number: number
  text: string
  bbox: BoundingBox | null
}

export interface OCRPage {
  page_number: number
  lines: OCRLine[]
  width: number
  height: number
  blurry: boolean
  sharpness_score: number
}

export interface OCRDocument {
  pages: OCRPage[]
}

export interface CareCardResult {
  card: ExtractedCard
  grounding_score: number
  schedules: ScheduleEntry[]
  ocr: OCRDocument
  ocr_used: string
}
