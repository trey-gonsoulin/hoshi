import { Link } from 'react-router'

const CATEGORIES = [
  { slug: 'planets', label: 'Planets' },
  { slug: 'signs', label: 'Signs' },
  { slug: 'houses', label: 'Houses' },
  { slug: 'aspects', label: 'Aspects' },
  { slug: 'points', label: 'Points' },
  { slug: 'angles', label: 'Angles' },
]

export function InfoPage() {
  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <h1 className="text-lg font-semibold mb-6">Reference</h1>
      <ul className="space-y-1">
        {CATEGORIES.map(({ slug, label }) => (
          <li key={slug} className="border-b border-border/40 last:border-0">
            <Link
              to={`/info/${slug}`}
              className="flex items-center justify-between py-2.5 group"
            >
              <span className="font-medium group-hover:text-primary transition-colors">
                {label}
              </span>
              <span className="text-muted-foreground text-xs">→</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
