import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { Loader2, BookmarkPlus, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ChartResult } from '@/components/ChartResult'
import { useChartStore } from '@/hooks/useChartStore'
import { api, type ChartOutput, type ZodiacMode, type HouseSystem, type ChartCompute } from '@/api/client'

interface FormState {
  date: string
  time: string
  useCoords: boolean
  location: string
  lat: string
  lon: string
  tz: string
  mode: ZodiacMode
  houses: HouseSystem
  details: boolean
  aspects: boolean
}

const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone

const defaultForm: FormState = {
  date: '',
  time: '',
  useCoords: false,
  location: '',
  lat: '',
  lon: '',
  tz: localTz,
  mode: 'realsky',
  houses: 'porphyry',
  details: false,
  aspects: false,
}

function buildRequest(f: FormState): ChartCompute {
  const base = {
    date: f.date,
    time: f.time || undefined,
    tz: f.tz || 'UTC',
    mode: f.mode,
    houses: f.houses,
    details: f.details,
    aspects: f.aspects,
    cusps: false,
  }
  if (f.useCoords) {
    return {
      ...base,
      lat: f.lat ? parseFloat(f.lat) : undefined,
      lon: f.lon ? parseFloat(f.lon) : undefined,
    }
  }
  return { ...base, location: f.location || undefined }
}

export function ComputePage() {
  const [form, setForm] = useState<FormState>(defaultForm)
  const [result, setResult] = useState<ChartOutput | null>(null)
  const [savedRequest, setSavedRequest] = useState<ChartCompute | null>(null)
  const [saveState, setSaveState] = useState<'idle' | 'naming' | 'saved'>('idle')
  const [saveName, setSaveName] = useState('')

  const { save } = useChartStore()
  const navigate = useNavigate()

  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }))

  const mutation = useMutation({
    mutationFn: () => api.computeChart(buildRequest(form)),
    onSuccess: (data) => {
      setResult(data)
      setSavedRequest(buildRequest(form))
      setSaveState('idle')
      setSaveName('')
    },
  })

  function handleSave() {
    if (!savedRequest) return
    if (saveState === 'idle') {
      setSaveName(form.date)
      setSaveState('naming')
      return
    }
    if (saveState === 'naming' && saveName.trim()) {
      const chart = save(saveName, savedRequest)
      setSaveState('saved')
      setTimeout(() => navigate(`/charts/${chart.id}`), 600)
    }
  }

  const saveActions = result && savedRequest ? (
    <div className="flex items-center gap-2">
      {saveState === 'naming' && (
        <Input
          autoFocus
          value={saveName}
          onChange={(e) => setSaveName(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setSaveState('idle') }}
          placeholder="Chart name"
          className="h-8 text-sm w-40"
        />
      )}
      <Button
        variant="outline"
        size="sm"
        onClick={handleSave}
        disabled={saveState === 'naming' && !saveName.trim()}
        className="gap-1.5"
      >
        {saveState === 'saved' ? (
          <><Check size={13} /> Saved</>
        ) : (
          <><BookmarkPlus size={13} /> {saveState === 'naming' ? 'Confirm' : 'Save chart'}</>
        )}
      </Button>
    </div>
  ) : null

  return (
    <div className="max-w-2xl mx-auto px-6 py-10 space-y-10">

      {/* Input form */}
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="date">Date</Label>
            <Input
              id="date"
              type="date"
              required
              value={form.date}
              onChange={(e) => set({ date: e.target.value })}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="time">
              Time{' '}
              <span className="text-muted-foreground font-normal">(optional)</span>
            </Label>
            <Input
              id="time"
              type="time"
              value={form.time}
              onChange={(e) => set({ time: e.target.value })}
            />
          </div>
        </div>

        {!form.useCoords ? (
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between">
              <Label htmlFor="location">Location</Label>
              <button
                type="button"
                className="text-xs text-primary hover:underline"
                onClick={() => set({ useCoords: true })}
              >
                Use coordinates instead
              </button>
            </div>
            <Input
              id="location"
              placeholder="e.g. New York, NY"
              value={form.location}
              onChange={(e) => set({ location: e.target.value })}
            />
          </div>
        ) : (
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between">
              <Label>Coordinates</Label>
              <button
                type="button"
                className="text-xs text-primary hover:underline"
                onClick={() => set({ useCoords: false })}
              >
                Use location name instead
              </button>
            </div>
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
          </div>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="tz">Timezone</Label>
          <Input
            id="tz"
            placeholder="e.g. America/New_York"
            value={form.tz}
            onChange={(e) => set({ tz: e.target.value })}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="mode">Zodiac mode</Label>
            <select
              id="mode"
              value={form.mode}
              onChange={(e) => set({ mode: e.target.value as ZodiacMode })}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="realsky">Real-sky</option>
              <option value="tropical">Tropical</option>
              <option value="vedic">Vedic</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="houses">House system</Label>
            <select
              id="houses"
              value={form.houses}
              onChange={(e) => set({ houses: e.target.value as HouseSystem })}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="porphyry">Porphyry</option>
              <option value="placidus">Placidus</option>
              <option value="equal">Equal</option>
              <option value="arc13">Arc-13</option>
            </select>
          </div>
        </div>

        <label className="flex items-center gap-2.5 text-sm cursor-pointer select-none">
          <input
            type="checkbox"
            checked={form.details}
            onChange={(e) => set({ details: e.target.checked, aspects: e.target.checked ? form.aspects : false })}
            className="h-4 w-4 rounded border-input accent-primary"
          />
          Include minor bodies, nodes, and lots
        </label>

        {form.details && (
          <label className="flex items-center gap-2.5 text-sm cursor-pointer select-none ml-6">
            <input
              type="checkbox"
              checked={form.aspects}
              onChange={(e) => set({ aspects: e.target.checked })}
              className="h-4 w-4 rounded border-input accent-primary"
            />
            Include aspects
          </label>
        )}

        <div className="flex items-center justify-between pt-1">
          {mutation.isError && (
            <p className="text-sm text-destructive">
              {mutation.error instanceof Error
                ? mutation.error.message
                : 'Something went wrong.'}
            </p>
          )}
          {!mutation.isError && <span />}
          <Button
            onClick={() => mutation.mutate()}
            disabled={!form.date || mutation.isPending}
          >
            {mutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            {mutation.isPending ? 'Computing…' : 'Compute chart'}
          </Button>
        </div>
      </div>

      {/* Results */}
      {result && <ChartResult result={result} actions={saveActions} />}
    </div>
  )
}
