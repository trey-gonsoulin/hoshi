import { Input } from '@/components/ui/input'

// Computed once at module load — the list is static for a given browser/OS
const TZ_LIST: string[] = (() => {
  try {
    return Intl.supportedValuesOf('timeZone')
  } catch {
    return []
  }
})()

interface TimezonePickerProps {
  value: string
  onChange: (value: string) => void
  id?: string
}

export function TimezonePicker({ value, onChange, id = 'tz' }: TimezonePickerProps) {
  return (
    <>
      <Input
        id={id}
        list={`${id}-list`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="e.g. America/New_York"
        autoComplete="off"
      />
      <datalist id={`${id}-list`}>
        {TZ_LIST.map((tz) => (
          <option key={tz} value={tz} />
        ))}
      </datalist>
    </>
  )
}
