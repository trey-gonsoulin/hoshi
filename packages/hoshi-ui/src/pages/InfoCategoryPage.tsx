import { useParams, Link } from 'react-router'
import { ArrowLeft } from 'lucide-react'
import { getInfoList } from '@/lib/astroInfo'

export function InfoCategoryPage() {
  const { category } = useParams<{ category: string }>()

  const data = category ? getInfoList(category) : null

  if (!data) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-10">
        <p className="text-sm text-destructive">Unknown category.</p>
      </div>
    )
  }

  const hasExtra = data.items.some(
    (item) => item.element || item.modality || item.ruler,
  )

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <div className="flex items-center gap-2 mb-6">
        <Link
          to="/info"
          className="text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Back to reference"
        >
          <ArrowLeft size={16} />
        </Link>
        <h1 className="text-lg font-semibold">{data.title}</h1>
      </div>

      <table className="w-full text-sm border-collapse">
        <tbody>
          {data.items.map((item) => (
            <tr
              key={item.name}
              className="border-b border-border/40 last:border-0"
            >
              <td className="py-2.5 pr-5 min-w-[120px]">
                <Link
                  to={`/info/${category}/${encodeURIComponent(item.name)}`}
                  className="font-medium hover:text-primary transition-colors"
                >
                  {item.name}
                </Link>
              </td>
              {hasExtra && (
                <td className="py-2.5 pr-5 text-muted-foreground text-xs min-w-[80px]">
                  {item.element ?? item.ruler ?? ''}
                </td>
              )}
              <td className="py-2.5 text-muted-foreground text-xs">
                {item.keywords.slice(0, 3).join(', ')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
