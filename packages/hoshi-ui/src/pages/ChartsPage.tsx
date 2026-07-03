import { Link } from 'react-router'
import { Trash2 } from 'lucide-react'
import { useChartStore } from '@/hooks/useChartStore'

export function ChartsPage() {
  const { charts, remove } = useChartStore()

  if (!charts.length) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-16 text-center">
        <p className="text-muted-foreground text-sm">No saved charts yet.</p>
        <p className="text-muted-foreground text-sm mt-1">
          <Link to="/compute" className="text-primary hover:underline">
            Compute a chart
          </Link>{' '}
          and save it here.
        </p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <h1 className="text-lg font-semibold mb-6">Saved charts</h1>
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
