import { useState } from 'react'
import { Tooltip } from '@base-ui/react/tooltip'
import type { InfoEntry } from '@/lib/astroInfo'

interface InfoTooltipProps {
  info: InfoEntry | undefined
  children: React.ReactNode
}

export function InfoTooltip({ info, children }: InfoTooltipProps) {
  const [open, setOpen] = useState(false)

  if (!info) return <>{children}</>

  return (
    <Tooltip.Root open={open} onOpenChange={setOpen}>
      <Tooltip.Trigger
        render={<span className="cursor-default" />}
        delay={300}
        onTouchEnd={(e) => {
          e.preventDefault()
          setOpen((o) => !o)
        }}
      >
        {children}
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Positioner sideOffset={6}>
          <Tooltip.Popup className="z-50 w-max max-w-[320px] rounded-md border border-border bg-popover px-2.5 py-2 shadow-md">
            <p className="text-[11px] font-semibold text-popover-foreground mb-0.5">
              {info.name}
            </p>
            <p className="text-[11px] text-muted-foreground leading-snug text-balance">
              {info.keywords.join(' · ')}
            </p>
          </Tooltip.Popup>
        </Tooltip.Positioner>
      </Tooltip.Portal>
    </Tooltip.Root>
  )
}
