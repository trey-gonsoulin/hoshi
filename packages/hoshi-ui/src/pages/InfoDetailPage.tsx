import { useParams, Link } from 'react-router'
import { ArrowLeft } from 'lucide-react'
import { getInfoDetail } from '@/lib/astroInfo'

export function InfoDetailPage() {
  const { category, name } = useParams<{ category: string; name: string }>()

  const data =
    category && name ? getInfoDetail(category, decodeURIComponent(name)) : null

  if (!data) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-10">
        <p className="text-sm text-destructive">Not found.</p>
      </div>
    )
  }

  const attrs: { label: string; value: string | number }[] = [
    data.element ? { label: 'Element', value: data.element } : null,
    data.modality ? { label: 'Modality', value: data.modality } : null,
    data.ruler ? { label: 'Ruler', value: data.ruler } : null,
    data.cusp != null ? { label: 'Cusp', value: `${data.cusp}°` } : null,
    data.size != null ? { label: 'Size', value: `${data.size}°` } : null,
  ].filter(Boolean) as { label: string; value: string | number }[]

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <div className="flex items-center gap-2 mb-8">
        <Link
          to={`/info/${category}`}
          className="text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Back to category"
        >
          <ArrowLeft size={16} />
        </Link>
        <h1 className="text-lg font-semibold">{data.name}</h1>
      </div>

      {data.keywords.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-6">
          {data.keywords.map((kw) => (
            <span
              key={kw}
              className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground"
            >
              {kw}
            </span>
          ))}
        </div>
      )}

      {data.meaning && (
        <p className="text-sm leading-relaxed mb-6">{data.meaning}</p>
      )}

      {attrs.length > 0 && (
        <table className="text-sm border-collapse">
          <tbody>
            {attrs.map(({ label, value }) => (
              <tr key={label} className="border-b border-border/40 last:border-0">
                <td className="py-1.5 pr-8 text-muted-foreground w-24">{label}</td>
                <td className="py-1.5 font-medium tabular-nums">{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
