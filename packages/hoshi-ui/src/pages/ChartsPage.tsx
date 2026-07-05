import { useRef, useState } from 'react'
import { zipSync, strToU8 } from 'fflate'
import { Link } from 'react-router'
import { Trash2, Upload, Download, GripVertical } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useChartStore } from '@/hooks/useChartStore'
import type { ChartCompute } from '@/api/client'
import type { PlacementSummary, SavedChart } from '@/hooks/useChartStore'

interface CliChart {
  name?: string
  date: string
  time?: string
  tz?: string
  lat?: number
  lon?: number
}

function parseCliChart(raw: unknown): { name: string; input: ChartCompute } | null {
  if (!raw || typeof raw !== 'object') return null
  const r = raw as Record<string, unknown>
  if (typeof r.date !== 'string' || !r.date) return null
  const chart = r as unknown as CliChart
  return {
    name: typeof chart.name === 'string' && chart.name ? chart.name : chart.date,
    input: {
      date: chart.date,
      time: chart.time ?? undefined,
      tz: chart.tz ?? 'UTC',
      lat: chart.lat ?? undefined,
      lon: chart.lon ?? undefined,
      mode: 'realsky',
      houses: 'porphyry',
      details: true,
      aspects: true,
      cusps: true,
    },
  }
}

function PlacementBadges({ placements }: { placements?: PlacementSummary }) {
  if (!placements) return null
  const parts = [
    placements.sun && `☉${placements.sun}`,
    placements.moon && `☽${placements.moon}`,
    placements.asc && `↑${placements.asc}`,
  ].filter(Boolean)
  if (!parts.length) return null
  return (
    <span className="ml-2 text-xs text-muted-foreground/70 tabular-nums">
      {parts.join(' ')}
    </span>
  )
}

function chartToCliJson(chart: SavedChart): Record<string, unknown> {
  const { name, input } = chart
  const out: Record<string, unknown> = { name, date: input.date }
  if (input.time) out.time = input.time
  if (input.tz && input.tz !== 'UTC') out.tz = input.tz
  if (input.lat != null) out.lat = input.lat
  if (input.lon != null) out.lon = input.lon
  return out
}

function downloadBlob(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function ChartsPage() {
  const { charts, save, remove, reorder } = useChartStore()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [importResult, setImportResult] = useState<{ ok: number; fail: number } | null>(null)
  const [activeTags, setActiveTags] = useState<Set<string>>(new Set())

  const allTags = Array.from(
    new Set(charts.flatMap((c) => c.tags ?? []))
  ).sort()

  const visibleCharts = activeTags.size === 0
    ? charts
    : charts.filter((c) => (c.tags ?? []).some((t) => activeTags.has(t)))

  function toggleTag(tag: string) {
    setActiveTags((prev) => {
      const next = new Set(prev)
      if (next.has(tag)) next.delete(tag)
      else next.add(tag)
      return next
    })
  }

  function handleExport() {
    const files: Record<string, Uint8Array> = {}
    for (const chart of charts) {
      const slug = chart.name.toLowerCase().replace(/\s+/g, '_')
      files[`${slug}.json`] = strToU8(JSON.stringify(chartToCliJson(chart), null, 2))
    }
    const zipped = zipSync(files, { level: 6 })
    downloadBlob('hoshi-charts.zip', new Blob([zipped], { type: 'application/zip' }))
  }

  const dragIndex = useRef<number>(-1)
  const [dragOver, setDragOver] = useState<number>(-1)

  async function handleFiles(files: FileList) {
    let ok = 0
    let fail = 0
    for (const file of Array.from(files)) {
      try {
        const text = await file.text()
        const parsed = parseCliChart(JSON.parse(text))
        if (!parsed) { fail++; continue }
        save(parsed.name, parsed.input)
        ok++
      } catch {
        fail++
      }
    }
    setImportResult({ ok, fail })
    setTimeout(() => setImportResult(null), 4000)
  }

  function handleDrop(toIdx: number) {
    reorder(dragIndex.current, toIdx)
    dragIndex.current = -1
    setDragOver(-1)
  }

  const header = (
    <div className="flex items-center justify-between mb-6">
      <h1 className="text-lg font-semibold">Saved charts</h1>
      <div className="flex items-center gap-3">
        {importResult && (
          <span className="text-xs text-muted-foreground">
            {importResult.ok > 0 && `${importResult.ok} imported`}
            {importResult.ok > 0 && importResult.fail > 0 && ', '}
            {importResult.fail > 0 && `${importResult.fail} failed`}
          </span>
        )}
        <Button
          variant="outline"
          size="icon-sm"
          title="Export all charts as JSON files"
          onClick={handleExport}
        >
          <Download size={13} />
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload size={13} />
          Import
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) handleFiles(e.target.files)
            e.target.value = ''
          }}
        />
      </div>
    </div>
  )

  const tagFilter = allTags.length > 0 && (
    <div className="flex flex-wrap gap-1.5 mb-5">
      {allTags.map((tag) => (
        <button
          key={tag}
          onClick={() => toggleTag(tag)}
          className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
            activeTags.has(tag)
              ? 'bg-primary text-primary-foreground border-primary'
              : 'bg-muted border-border text-muted-foreground hover:text-foreground'
          }`}
        >
          {tag}
        </button>
      ))}
    </div>
  )

  if (!charts.length) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-10">
        {header}
        <div className="py-10 text-center">
          <p className="text-muted-foreground text-sm">No saved charts yet.</p>
          <p className="text-muted-foreground text-sm mt-1">
            <Link to="/compute" className="text-primary hover:underline">
              Compute a chart
            </Link>{' '}
            and save it here, or import JSON files from the CLI.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      {header}
      {tagFilter}
      {visibleCharts.length === 0 && (
        <div className="py-10 text-center">
          <p className="text-muted-foreground text-sm">No charts match the selected tags.</p>
        </div>
      )}
      <ul className="space-y-1">
        {visibleCharts.map((chart) => {
          const realIdx = charts.indexOf(chart)
          return (
            <li
              key={chart.id}
              className={`flex items-center justify-between gap-2 py-2.5 border-b border-border/40 last:border-0 transition-opacity ${dragOver === realIdx ? 'opacity-50' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(realIdx) }}
              onDragLeave={() => setDragOver(-1)}
              onDrop={() => handleDrop(realIdx)}
            >
              <div
                draggable
                onDragStart={() => { dragIndex.current = realIdx }}
                onDragEnd={() => { dragIndex.current = -1; setDragOver(-1) }}
                className="text-muted-foreground/40 hover:text-muted-foreground cursor-grab active:cursor-grabbing p-1 -ml-1 touch-none"
                aria-label="Drag to reorder"
              >
                <GripVertical size={14} />
              </div>
              <Link
                to={`/charts/${chart.id}`}
                className="flex-1 min-w-0 group"
              >
                <div className="flex items-center">
                  <span className="font-medium group-hover:text-primary transition-colors">
                    {chart.name}
                  </span>
                  <PlacementBadges placements={chart.placements} />
                  <span className="ml-3 text-xs text-muted-foreground tabular-nums">
                    {chart.input.date}
                    {chart.input.time ? ` ${chart.input.time}` : ''}
                  </span>
                </div>
                {chart.tags && chart.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {chart.tags.map((tag) => (
                      <span key={tag} className="text-xs px-1.5 py-0.5 rounded-full bg-muted border border-border/60 text-muted-foreground">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </Link>
              <button
                onClick={() => remove(chart.id)}
                aria-label={`Delete ${chart.name}`}
                className="text-muted-foreground hover:text-destructive transition-colors p-1"
              >
                <Trash2 size={14} />
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
