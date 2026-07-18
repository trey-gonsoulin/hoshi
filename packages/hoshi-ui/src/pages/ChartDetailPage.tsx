import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, ArrowLeft, Pencil, Check, X, Tag } from 'lucide-react'
import { ChartResult } from '@/components/ChartResult'
import { useChartStore } from '@/hooks/useChartStore'
import { api, type ZodiacMode, type HouseSystem } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { TimezonePicker } from '@/components/TimezonePicker'
import type { PlacementSummary } from '@/hooks/useChartStore'

const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone

interface EditState {
  name: string
  date: string
  time: string
  useCoords: boolean
  location: string
  lat: string
  lon: string
  tz: string
  mode: ZodiacMode
  houses: HouseSystem
  tags: string[]
  tagInput: string
}

function extractPlacements(bodies: { name: string; signSymbol: string }[]): PlacementSummary {
  const find = (n: string) => bodies.find((b) => b.name === n)?.signSymbol
  return { sun: find('Sun'), moon: find('Moon'), asc: find('Ascendant') }
}

export function ChartDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { get, update } = useChartStore()
  const queryClient = useQueryClient()
  const chart = id ? get(id) : undefined

  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState<EditState | null>(null)
  const tagInputRef = useRef<HTMLInputElement>(null)

  const { data: result, isLoading, error } = useQuery({
    queryKey: ['chart-compute', id],
    queryFn: () =>
      api.computeChart({ ...chart!.input, details: true, aspects: true, cusps: true }),
    enabled: !!chart,
    staleTime: Infinity,
    gcTime: Infinity,
  })

  // Backfill Sun/Moon/Asc placements when first computed
  useEffect(() => {
    if (result && chart && !chart.placements) {
      update(chart.id, { placements: extractPlacements(result.bodies) })
    }
  }, [result, chart, update])

  function startEdit() {
    if (!chart) return
    const input = chart.input
    setEditForm({
      name: chart.name,
      date: input.date,
      time: input.time ?? '',
      useCoords: input.lat != null,
      location: input.location ?? '',
      lat: input.lat != null ? String(input.lat) : '',
      lon: input.lon != null ? String(input.lon) : '',
      tz: input.tz ?? localTz,
      mode: input.mode ?? 'realsky',
      houses: input.houses ?? 'porphyry',
      tags: chart.tags ?? [],
      tagInput: '',
    })
    setEditing(true)
  }

  function cancelEdit() {
    setEditing(false)
    setEditForm(null)
  }

  function commitEdit() {
    if (!chart || !editForm) return
    const input = {
      ...chart.input,
      date: editForm.date,
      time: editForm.time || undefined,
      tz: editForm.tz || 'UTC',
      mode: editForm.mode,
      houses: editForm.houses,
      ...(editForm.useCoords
        ? {
            lat: editForm.lat ? parseFloat(editForm.lat) : undefined,
            lon: editForm.lon ? parseFloat(editForm.lon) : undefined,
            location: undefined,
          }
        : {
            location: editForm.location || undefined,
            lat: undefined,
            lon: undefined,
          }),
    }
    // Clear cached placements — they'll be backfilled after recompute
    update(chart.id, { name: editForm.name.trim() || chart.name, input, placements: undefined, tags: editForm.tags })
    queryClient.removeQueries({ queryKey: ['chart-compute', id] })
    setEditing(false)
    setEditForm(null)
  }

  const setEdit = (patch: Partial<EditState>) =>
    setEditForm((f) => f ? { ...f, ...patch } : f)

  if (!chart) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-16 text-center">
        <p className="text-muted-foreground text-sm">Chart not found.</p>
        <Link to="/charts" className="text-xs text-primary hover:underline mt-2 inline-block">
          Back to charts
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-2">
          <Link
            to="/charts"
            className="text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Back to charts"
          >
            <ArrowLeft size={16} />
          </Link>
          <h1 className="text-lg font-semibold">{chart.name}</h1>
          {!editing && chart.tags && chart.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {chart.tags.map((tag) => (
                <span key={tag} className="text-xs px-1.5 py-0.5 rounded-full bg-muted border border-border text-muted-foreground">
                  {tag}
                </span>
              ))}
            </div>
          )}
          {!editing && (
            <button
              onClick={startEdit}
              aria-label="Edit chart"
              className="text-muted-foreground hover:text-foreground transition-colors p-1"
            >
              <Pencil size={13} />
            </button>
          )}
        </div>
        {!editing && (
          <div className="flex gap-3 text-sm">
            <Link
              to={`/charts/${chart.id}/transits`}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Transits
            </Link>
            <Link
              to={`/charts/${chart.id}/compare`}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Compare
            </Link>
          </div>
        )}
        {editing && (
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={cancelEdit} className="gap-1">
              <X size={12} /> Cancel
            </Button>
            <Button size="sm" onClick={commitEdit} className="gap-1">
              <Check size={12} /> Save
            </Button>
          </div>
        )}
      </div>

      {editing && editForm && (
        <div className="space-y-5 mb-10 p-4 border border-border rounded-lg bg-muted/20">
          <div className="space-y-1.5">
            <Label htmlFor="edit-name">Name</Label>
            <Input
              id="edit-name"
              value={editForm.name}
              onChange={(e) => setEdit({ name: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="edit-date">Date</Label>
              <Input
                id="edit-date"
                type="date"
                value={editForm.date}
                onChange={(e) => setEdit({ date: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-time">
                Time{' '}
                <span className="text-muted-foreground font-normal">(optional)</span>
              </Label>
              <Input
                id="edit-time"
                type="text"
                placeholder="HH:MM"
                value={editForm.time}
                onChange={(e) => setEdit({ time: e.target.value })}
              />
            </div>
          </div>

          {!editForm.useCoords ? (
            <div className="space-y-1.5">
              <div className="flex items-baseline justify-between">
                <Label htmlFor="edit-location">Location</Label>
                <button
                  type="button"
                  className="text-xs text-primary hover:underline"
                  onClick={() => setEdit({ useCoords: true })}
                >
                  Use coordinates instead
                </button>
              </div>
              <Input
                id="edit-location"
                placeholder="e.g. New York, NY"
                value={editForm.location}
                onChange={(e) => setEdit({ location: e.target.value })}
              />
            </div>
          ) : (
            <div className="space-y-1.5">
              <div className="flex items-baseline justify-between">
                <Label>Coordinates</Label>
                <button
                  type="button"
                  className="text-xs text-primary hover:underline"
                  onClick={() => setEdit({ useCoords: false })}
                >
                  Use location name instead
                </button>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Input
                  placeholder="Latitude"
                  type="number"
                  step="any"
                  value={editForm.lat}
                  onChange={(e) => setEdit({ lat: e.target.value })}
                />
                <Input
                  placeholder="Longitude"
                  type="number"
                  step="any"
                  value={editForm.lon}
                  onChange={(e) => setEdit({ lon: e.target.value })}
                />
              </div>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="edit-tz">Timezone</Label>
            <TimezonePicker
              id="edit-tz"
              value={editForm.tz}
              onChange={(tz) => setEdit({ tz })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="edit-mode">Zodiac mode</Label>
              <select
                id="edit-mode"
                value={editForm.mode}
                onChange={(e) => setEdit({ mode: e.target.value as ZodiacMode })}
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="realsky">Real-sky</option>
                <option value="tropical">Tropical</option>
                <option value="vedic">Vedic</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-houses">House system</Label>
              <select
                id="edit-houses"
                value={editForm.houses}
                onChange={(e) => setEdit({ houses: e.target.value as HouseSystem })}
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="porphyry">Porphyry</option>
                <option value="placidus">Placidus</option>
                <option value="equal">Equal</option>
                <option value="arc13">Arc-13</option>
              </select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Tags</Label>
            <div className="flex flex-wrap gap-1.5 mb-1.5">
              {editForm.tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-muted border border-border"
                >
                  {tag}
                  <button
                    type="button"
                    onClick={() => setEdit({ tags: editForm.tags.filter((t) => t !== tag) })}
                    aria-label={`Remove tag ${tag}`}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <X size={10} />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <Input
                ref={tagInputRef}
                id="edit-tag-input"
                placeholder="Add a tag…"
                value={editForm.tagInput}
                onChange={(e) => setEdit({ tagInput: e.target.value })}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    const tag = editForm.tagInput.trim().toLowerCase()
                    if (tag && !editForm.tags.includes(tag)) {
                      setEdit({ tags: [...editForm.tags, tag], tagInput: '' })
                    } else {
                      setEdit({ tagInput: '' })
                    }
                  }
                }}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  const tag = editForm.tagInput.trim().toLowerCase()
                  if (tag && !editForm.tags.includes(tag)) {
                    setEdit({ tags: [...editForm.tags, tag], tagInput: '' })
                  } else {
                    setEdit({ tagInput: '' })
                  }
                  tagInputRef.current?.focus()
                }}
              >
                <Tag size={12} />
                Add
              </Button>
            </div>
          </div>
        </div>
      )}

      {error && !editing && (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Failed to compute chart'}
        </p>
      )}

      {isLoading && !editing && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 size={14} className="animate-spin" />
          Computing…
        </div>
      )}

      {result && !editing && <ChartResult result={result} />}
    </div>
  )
}
