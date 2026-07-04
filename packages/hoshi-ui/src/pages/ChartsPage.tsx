import { useRef, useState } from 'react'
import { Link } from 'react-router'
import { Trash2, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useChartStore } from '@/hooks/useChartStore'
import type { ChartCompute } from '@/api/client'

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

export function ChartsPage() {
  const { charts, save, remove } = useChartStore()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [importResult, setImportResult] = useState<{ ok: number; fail: number } | null>(null)

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
      <ul className="space-y-1">
        {charts.map((chart) => (
          <li
            key={chart.id}
            className="flex items-center justify-between gap-4 py-2.5 border-b border-border/40 last:border-0"
          >
            <Link
              to={`/charts/${chart.id}`}
              className="flex-1 min-w-0 group"
            >
              <span className="font-medium group-hover:text-primary transition-colors">
                {chart.name}
              </span>
              <span className="ml-3 text-xs text-muted-foreground tabular-nums">
                {chart.input.date}
                {chart.input.time ? ` ${chart.input.time}` : ''}
              </span>
            </Link>
            <button
              onClick={() => remove(chart.id)}
              aria-label={`Delete ${chart.name}`}
              className="text-muted-foreground hover:text-destructive transition-colors p-1"
            >
              <Trash2 size={14} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
