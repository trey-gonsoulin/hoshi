interface WarningBannerProps {
  warnings: string[]
}

export function WarningBanner({ warnings }: WarningBannerProps) {
  if (!warnings.length) return null
  return (
    <div className="border-l-2 border-amber-500 bg-amber-50 dark:bg-amber-950/30 pl-4 py-2.5 space-y-1">
      {warnings.map((w, i) => (
        <p key={i} className="text-sm text-amber-800 dark:text-amber-300 leading-snug">
          {w}
        </p>
      ))}
    </div>
  )
}
