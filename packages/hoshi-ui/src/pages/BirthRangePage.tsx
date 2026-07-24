import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { Loader2, Plus, X, BookmarkPlus, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { WarningBanner } from '@/components/WarningBanner'
import { useChartStore } from '@/hooks/useChartStore'
import {
  api,
  type ZodiacMode,
  type ConstraintInput,
  type BirthRangeResultOutput,
  type BirthWindow,
} from '@/api/client'

// Scannable planets and angle bodies, matching birthrange.py
const PLANETS = [
  { id: 'sun', label: 'Sun' },
  { id: 'moon', label: 'Moon' },
  { id: 'mercury', label: 'Mercury' },
  { id: 'venus', label: 'Venus' },
  { id: 'mars', label: 'Mars' },
  { id: 'jupiter', label: 'Jupiter' },
  { id: 'saturn', label: 'Saturn' },
  { id: 'uranus', label: 'Uranus' },
  { id: 'neptune', label: 'Neptune' },
  { id: 'pluto', label: 'Pluto' },
  { id: 'asc', label: 'ASC' },
  { id: 'mc', label: 'MC' },
  { id: 'ic', label: 'IC' },
  { id: 'dsc', label: 'DSC' },
]

const REALSKY_SIGNS = [
  'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra',
  'Scorpius', 'Ophiuchus', 'Sagittarius', 'Capricornus', 'Aquarius', 'Pisces',
]

const TROPICAL_SIGNS = [
  'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra',
  'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces',
]

const ANGLE_IDS = new Set(['asc', 'mc', 'ic', 'dsc'])

function signsForMode(mode: ZodiacMode) {
  return mode === 'tropical' || mode === 'vedic' ? TROPICAL_SIGNS : REALSKY_SIGNS
}

function formatDuration(days: number) {
  if (days < 1) return `${Math.round(days * 24)}h`
  if (days < 7) return `${days.toFixed(1)}d`
  return `${Math.round(days)}d`
}

function formatDate(iso: string) {
  return iso.replace('T', ' ').replace(/:\d\d(\.\d+)?([+-]\d+:\d+|Z)?$/, ' UTC')
}

interface FormState {
  constraints: ConstraintInput[]
  pendingPlanet: string
  pendingSign: string
  fromDate: string
  toDate: string
  mode: ZodiacMode
  useCoords: boolean
  lat: string
  lon: string
}

const today = new Date().toISOString().substring(0, 10)

const defaultForm: FormState = {
  constraints: [],
  pendingPlanet: 'sun',
  pendingSign: 'Aries',
  fromDate: '1900-01-01',
  toDate: today,
  mode: 'realsky',
  useCoords: false,
  lat: '',
  lon: '',
}

export function BirthRangePage() {
  const [form, setForm] = useState<FormState>(defaultForm)
  const [result, setResult] = useState<BirthRangeResultOutput | null>(null)
  const [saveState, setSaveState] = useState<'idle' | 'naming' | 'saved'>('idle')
  const [saveName, setSaveName] = useState('')
  const [saveError, setSaveError] = useState('')

  const { save } = useChartStore()
  const navigate = useNavigate()

  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }))

  const hasAngle = form.constraints.some((c) => ANGLE_IDS.has(c.planet))
  const signs = signsForMode(form.mode)

  function addConstraint() {
    const planet = form.pendingPlanet
    const sign = form.pendingSign
    if (!sign || form.constraints.some((c) => c.planet === planet)) return
    set({ constraints: [...form.constraints, { planet, sign }] })
  }

  function removeConstraint(planet: string) {
    set({ constraints: form.constraints.filter((c) => c.planet !== planet) })
  }

  function updateSign(planet: string, sign: string) {
    set({ constraints: form.constraints.map((c) => c.planet === planet ? { ...c, sign } : c) })
  }

  const mutation = useMutation({
    mutationFn: () => {
      if (form.constraints.length === 0) throw new Error('Add at least one constraint.')
      if (hasAngle && (!form.lat || !form.lon)) {
        throw new Error('Angle constraints (ASC/MC/IC/DSC) require lat and lon.')
      }
      return api.birthRange({
        constraints: form.constraints,
        fromDate: form.fromDate,
        toDate: form.toDate || undefined,
        mode: form.mode,
        lat: form.useCoords && form.lat ? parseFloat(form.lat) : undefined,
        lon: form.useCoords && form.lon ? parseFloat(form.lon) : undefined,
      })
    },
    onSuccess: (data) => {
      setResult(data)
      setSaveState('idle')
      setSaveName('')
      setSaveError('')
    },
  })

  function handleSave() {
    if (!result || result.windows.length === 0) return
    if (saveState === 'idle') {
      setSaveName('')
      setSaveError('')
      setSaveState('naming')
      return
    }
    if (saveState === 'naming') {
      const name = saveName.trim()
      if (!name) { setSaveError('Enter a name.'); return }
      const firstWindow = result.windows[0]
      const birthWindows: BirthWindow[] = result.windows.map((w) => ({
        start: w.start,
        end: w.end,
      }))
      const chart = save(name, {
        date: firstWindow.start.substring(0, 10),
        time: undefined,
        tz: 'UTC',
        lat: form.useCoords && form.lat ? parseFloat(form.lat) : undefined,
        lon: form.useCoords && form.lon ? parseFloat(form.lon) : undefined,
        mode: form.mode,
        houses: 'porphyry',
        details: true,
        aspects: true,
        cusps: true,
        birthWindows,
      })
      setSaveState('saved')
      setTimeout(() => navigate(`/charts/${chart.id}`), 600)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-10 space-y-10">
      {/* Constraints builder */}
      <div className="space-y-5">
        <div className="space-y-1.5">
          <Label>Zodiac mode</Label>
          <select
            value={form.mode}
            onChange={(e) => {
              const mode = e.target.value as ZodiacMode
              const newSigns = signsForMode(mode)
              set({
                mode,
                constraints: form.constraints.map((c) => ({
                  ...c,
                  sign: newSigns.includes(c.sign) ? c.sign : newSigns[0],
                })),
                pendingSign: newSigns[0],
              })
            }}
            className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="realsky">Real-sky</option>
            <option value="tropical">Tropical</option>
            <option value="vedic">Vedic</option>
          </select>
        </div>

        {/* Added constraints */}
        {form.constraints.length > 0 && (
          <div className="space-y-2">
            <Label>Constraints</Label>
            {form.constraints.map((c) => (
              <div key={c.planet} className="flex items-center gap-2">
                <span className="text-sm w-24 text-muted-foreground">
                  {PLANETS.find((p) => p.id === c.planet)?.label ?? c.planet}
                </span>
                <span className="text-sm text-muted-foreground">in</span>
                <select
                  value={c.sign}
                  onChange={(e) => updateSign(c.planet, e.target.value)}
                  className="flex-1 h-8 rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  {signs.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => removeConstraint(c.planet)}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                  aria-label={`Remove ${c.planet}`}
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Add constraint row */}
        <div className="flex items-end gap-2">
          <div className="flex-1 space-y-1.5">
            <Label>Add constraint</Label>
            <select
              value={form.pendingPlanet}
              onChange={(e) => set({ pendingPlanet: e.target.value })}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {PLANETS.filter((p) => !form.constraints.some((c) => c.planet === p.id)).map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 space-y-1.5">
            <Label>&nbsp;</Label>
            <select
              value={form.pendingSign}
              onChange={(e) => set({ pendingSign: e.target.value })}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {signs.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addConstraint}
            disabled={form.constraints.some((c) => c.planet === form.pendingPlanet)}
            className="gap-1 mb-0.5"
          >
            <Plus size={13} /> Add
          </Button>
        </div>

        {/* Date range */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="fromDate">From</Label>
            <Input
              id="fromDate"
              type="date"
              value={form.fromDate}
              onChange={(e) => set({ fromDate: e.target.value })}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="toDate">To</Label>
            <Input
              id="toDate"
              type="date"
              value={form.toDate}
              onChange={(e) => set({ toDate: e.target.value })}
            />
          </div>
        </div>

        {/* Coordinates (required for angle constraints, optional otherwise) */}
        <div className="space-y-1.5">
          <div className="flex items-baseline justify-between">
            <Label>
              Coordinates{' '}
              {hasAngle ? (
                <span className="text-destructive font-normal">(required for angle constraints)</span>
              ) : (
                <span className="text-muted-foreground font-normal">(optional)</span>
              )}
            </Label>
            {!hasAngle && (
              <button
                type="button"
                className="text-xs text-primary hover:underline"
                onClick={() => set({ useCoords: !form.useCoords })}
              >
                {form.useCoords ? 'Hide' : 'Add coordinates'}
              </button>
            )}
          </div>
          {(hasAngle || form.useCoords) && (
            <div className="grid grid-cols-2 gap-4">
              <Input
                placeholder="Latitude (e.g. 40.7128)"
                type="number"
                step="any"
                value={form.lat}
                onChange={(e) => set({ lat: e.target.value })}
              />
              <Input
                placeholder="Longitude (e.g. -74.006)"
                type="number"
                step="any"
                value={form.lon}
                onChange={(e) => set({ lon: e.target.value })}
              />
            </div>
          )}
        </div>

        <div className="flex items-center justify-between pt-1">
          {mutation.isError && (
            <p className="text-sm text-destructive">
              {mutation.error instanceof Error ? mutation.error.message : 'Something went wrong.'}
            </p>
          )}
          {!mutation.isError && <span />}
          <Button
            onClick={() => mutation.mutate()}
            disabled={form.constraints.length === 0 || mutation.isPending}
          >
            {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {mutation.isPending ? 'Searching…' : 'Search'}
          </Button>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-5">
          <div className="h-px bg-border" />

          <WarningBanner warnings={
            result.windows.length === 0
              ? ['No date windows found matching all constraints.']
              : []
          } />

          <div className="flex items-start justify-between gap-4">
            <div className="space-y-0.5">
              <p className="text-sm font-medium">{result.constraints.join(' · ')}</p>
              <p className="text-xs text-muted-foreground">
                {result.windows.length} window{result.windows.length !== 1 ? 's' : ''} found
                {' · '}{result.mode} mode
              </p>
            </div>
            {result.windows.length > 0 && (
              <div className="flex items-center gap-2 flex-shrink-0">
                {saveState === 'naming' && (
                  <Input
                    autoFocus
                    value={saveName}
                    onChange={(e) => setSaveName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSave()
                      if (e.key === 'Escape') setSaveState('idle')
                    }}
                    placeholder="Chart name"
                    className="h-8 text-sm w-40"
                  />
                )}
                {saveError && <p className="text-xs text-destructive">{saveError}</p>}
                <Button variant="outline" size="sm" onClick={handleSave} className="gap-1.5">
                  {saveState === 'saved' ? (
                    <><Check size={13} /> Saved</>
                  ) : (
                    <><BookmarkPlus size={13} /> {saveState === 'naming' ? 'Confirm' : 'Save chart'}</>
                  )}
                </Button>
              </div>
            )}
          </div>

          {result.windows.length > 0 && (
            <table className="text-sm border-collapse w-full">
              <thead>
                <tr className="border-b border-border text-muted-foreground text-xs">
                  <th className="text-left pb-2 pr-6 font-medium">Start</th>
                  <th className="text-left pb-2 pr-6 font-medium">End</th>
                  <th className="text-right pb-2 font-medium">Duration</th>
                </tr>
              </thead>
              <tbody>
                {result.windows.map((w, i) => (
                  <tr key={i} className="border-b border-border/40 last:border-0">
                    <td className="py-1.5 pr-6 tabular-nums">{formatDate(w.start)}</td>
                    <td className="py-1.5 pr-6 tabular-nums">{formatDate(w.end)}</td>
                    <td className="py-1.5 text-right text-muted-foreground">{formatDuration(w.durationDays)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
