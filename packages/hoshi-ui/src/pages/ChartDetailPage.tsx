import { useParams, Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { Loader2, ArrowLeft } from 'lucide-react'
import { ChartResult } from '@/components/ChartResult'
import { useChartStore } from '@/hooks/useChartStore'
import { api } from '@/api/client'

export function ChartDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { get } = useChartStore()
  const chart = id ? get(id) : undefined

  const { data: result, isLoading, error } = useQuery({
    queryKey: ['chart-compute', id],
    queryFn: () =>
      api.computeChart({ ...chart!.input, details: true, aspects: true, cusps: true }),
    enabled: !!chart,
    // Natal placements don't change unless backend computation changes,
    // which requires a page reload anyway — cache for the session lifetime
    staleTime: Infinity,
    gcTime: Infinity,
  })

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
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : 'Failed to compute chart'}
        </p>
      )}

      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 size={14} className="animate-spin" />
          Computing…
        </div>
      )}

      {result && <ChartResult result={result} />}
    </div>
  )
}
