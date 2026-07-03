import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router'
import { Loader2, ArrowLeft } from 'lucide-react'
import { ChartResult } from '@/components/ChartResult'
import { useChartStore } from '@/hooks/useChartStore'
import { api, type ChartOutput } from '@/api/client'


export function ChartDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { get } = useChartStore()
  const chart = id ? get(id) : undefined

  const [result, setResult] = useState<ChartOutput | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!chart) return
    setResult(null)
    setError(null)
    api
      .computeChart({ ...chart.input, details: true, aspects: true, cusps: true })
      .then(setResult)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : 'Failed to compute chart'),
      )
  }, [chart])

  if (!chart) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-16 text-center">
        <p className="text-muted-foreground text-sm">Chart not found.</p>
        <Link to="/" className="text-xs text-primary hover:underline mt-2 inline-block">
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
            to="/"
            className="text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Back to charts"
          >
            <ArrowLeft size={16} />
          </Link>
          <h1 className="text-lg font-semibold">{chart.name}</h1>
        </div>
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
      </div>

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      {!result && !error && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 size={14} className="animate-spin" />
          Computing…
        </div>
      )}

      {result && <ChartResult result={result} />}
    </div>
  )
}
