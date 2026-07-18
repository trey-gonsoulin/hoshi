import { useState, useMemo } from 'react'
import { Link } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { Loader2, ChevronDown, ChevronUp, Calendar } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { BodyTable } from '@/components/BodyTable'
import { useChartStore } from '@/hooks/useChartStore'
import { api, type SkyEventEntry, type ZodiacMode } from '@/api/client'

const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone

function todayLocal(): string {
  return new Date().toLocaleDateString('en-CA') // YYYY-MM-DD in local timezone
}

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + 'T12:00:00')
  d.setDate(d.getDate() + days)
  return d.toLocaleDateString('en-CA')
}

// ── Event type metadata ───────────────────────────────────────────────────────

const EVENT_META: Record<string, { icon: string; label: string; color: string }> = {
  retrograde_station: { icon: '℞', label: 'Station RX', color: 'text-amber-600 dark:text-amber-400' },
  direct_station:     { icon: 'D', label: 'Station D',  color: 'text-sky-600 dark:text-sky-400' },
  ingress:            { icon: '→', label: 'Ingress',    color: 'text-violet-600 dark:text-violet-400' },
  moon_new:           { icon: '●', label: 'New Moon',   color: 'text-foreground/60' },
  moon_first_quarter: { icon: '◑', label: '1st Quarter',color: 'text-foreground/70' },
  moon_full:          { icon: '○', label: 'Full Moon',  color: 'text-foreground/90' },
  moon_last_quarter:  { icon: '◐', label: 'Last Quarter',color: 'text-foreground/70' },
  voc_start:          { icon: '∅', label: 'VoC begins', color: 'text-yellow-600 dark:text-yellow-500' },
  voc_end:            { icon: '✓', label: 'VoC ends',   color: 'text-muted-foreground' },
  exact_aspect:       { icon: '✦', label: 'Exact aspect',color: 'text-teal-600 dark:text-teal-400' },
}

// ── Time formatting ───────────────────────────────────────────────────────────

function formatEventTime(isoUtc: string, tz: string): string {
  try {
    const d = new Date(isoUtc)
    return d.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      timeZone: tz,
    })
  } catch {
    return isoUtc.slice(11, 16)
  }
}

function formatEventDate(isoUtc: string, tz: string): string {
  try {
    const d = new Date(isoUtc)
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      timeZone: tz,
    })
  } catch {
    return isoUtc.slice(0, 10)
  }
}

// ── EventList component ───────────────────────────────────────────────────────

function EventList({ events, tz, multiDay }: { events: SkyEventEntry[]; tz: string; multiDay: boolean }) {
  // Must be called before any early return — Rules of Hooks
  const grouped = useMemo(() => {
    if (!multiDay || events.length === 0) return null
    const map = new Map<string, SkyEventEntry[]>()
    for (const e of events) {
      const key = formatEventDate(e.when, tz)
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(e)
    }
    return map
  }, [events, tz, multiDay])

  if (events.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-6 text-center">
        No significant events in this period.
      </p>
    )
  }

  if (grouped) {
    return (
      <div className="space-y-6">
        {[...grouped.entries()].map(([date, dayEvents]) => (
          <div key={date}>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-3 select-none">
              {date}
            </p>
            <EventRows events={dayEvents} tz={tz} />
          </div>
        ))}
      </div>
    )
  }

  return <EventRows events={events} tz={tz} />
}

function EventRows({ events, tz }: { events: SkyEventEntry[]; tz: string }) {
  return (
    <ul className="space-y-0">
      {events.map((e, i) => {
        const meta = EVENT_META[e.eventType] ?? { icon: '·', label: '', color: 'text-muted-foreground' }
        const isVocStart = e.eventType === 'voc_start'
        const isVocEnd = e.eventType === 'voc_end'

        return (
          <li
            key={i}
            className={`flex items-baseline gap-3 py-2 border-b border-border/30 last:border-0 ${
              isVocStart || isVocEnd ? 'opacity-60' : ''
            }`}
          >
            {/* Time */}
            <span className="text-xs text-muted-foreground tabular-nums w-[60px] shrink-0 text-right">
              {formatEventTime(e.when, tz)}
            </span>

            {/* Type icon */}
            <span className={`text-xs font-mono w-4 shrink-0 text-center ${meta.color}`} aria-label={meta.label}>
              {meta.icon}
            </span>

            {/* Body glyph + detail */}
            <span className="text-sm flex-1 min-w-0">
              {e.bodySymbol && (
                <span className="text-muted-foreground/70 mr-1.5 select-none">{e.bodySymbol}</span>
              )}
              <span className={isVocStart || isVocEnd ? 'italic' : ''}>{e.detail}</span>
              {e.sign && e.signSymbol && (
                <span className="ml-1.5 text-muted-foreground text-xs">{e.signSymbol}</span>
              )}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

// ── Quick-range buttons ───────────────────────────────────────────────────────

function RangeButton({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
        active
          ? 'bg-primary text-primary-foreground border-primary'
          : 'border-border text-muted-foreground hover:text-foreground hover:border-foreground/40'
      }`}
    >
      {label}
    </button>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function SkyPage() {
  const today = todayLocal()
  const [from, setFrom] = useState(today)
  const [to, setTo] = useState(today)
  const [mode, setMode] = useState<ZodiacMode>('realsky')
  const [showSky, setShowSky] = useState(false)
  const [customRange, setCustomRange] = useState(false)

  const { charts } = useChartStore()
  const tz = localTz

  const isToday = from === today && to === today
  const isWeek = from === today && to === addDays(today, 6)
  const isMonth = from === today && to === addDays(today, 29)
  const multiDay = from !== to

  function setRange(fromDate: string, toDate: string) {
    setFrom(fromDate)
    setTo(toDate)
    setCustomRange(false)
  }

  // Events query — auto-fetches when range/mode changes
  const eventsQuery = useQuery({
    queryKey: ['sky-events', from, to, mode, tz],
    queryFn: () => api.skyEvents({ from, to, mode, tz }),
  })

  // Current sky — lazy, triggered by showSky toggle
  const skyQuery = useQuery({
    queryKey: ['sky-now', mode, tz],
    queryFn: () => api.skyNow({ mode, tz }),
    enabled: showSky,
  })

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="flex items-baseline justify-between mb-8">
        <div>
          <h1 className="text-lg font-semibold">Sky</h1>
          <p className="text-xs text-muted-foreground mt-0.5">{tz}</p>
        </div>

        {/* Zodiac mode */}
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as ZodiacMode)}
          className="text-xs h-7 rounded border border-input bg-background px-2 text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="realsky">Real-sky</option>
          <option value="tropical">Tropical</option>
          <option value="vedic">Vedic</option>
        </select>
      </div>

      {/* Range selector */}
      <div className="flex flex-wrap items-center gap-2 mb-6">
        <RangeButton label="Today" active={isToday && !customRange} onClick={() => setRange(today, today)} />
        <RangeButton label="Next 7 days" active={isWeek && !customRange} onClick={() => setRange(today, addDays(today, 6))} />
        <RangeButton label="Next 30 days" active={isMonth && !customRange} onClick={() => setRange(today, addDays(today, 29))} />
        <RangeButton
          label="Custom…"
          active={customRange}
          onClick={() => setCustomRange((v) => !v)}
        />
      </div>

      {customRange && (
        <div className="flex items-end gap-4 mb-6 p-4 rounded-lg border border-border bg-muted/30">
          <div className="space-y-1">
            <Label htmlFor="from-date" className="text-xs">From</Label>
            <Input
              id="from-date"
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              className="h-8 text-sm w-36"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="to-date" className="text-xs">To</Label>
            <Input
              id="to-date"
              type="date"
              value={to}
              min={from}
              onChange={(e) => setTo(e.target.value)}
              className="h-8 text-sm w-36"
            />
          </div>
        </div>
      )}

      {/* Events section */}
      <section>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4 select-none">
          {isToday ? "Today's events" : multiDay ? 'Upcoming events' : 'Events'}
        </p>

        {eventsQuery.isPending && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-6">
            <Loader2 size={14} className="animate-spin" />
            <span>Scanning sky…</span>
          </div>
        )}

        {eventsQuery.isError && (
          <p className="text-sm text-destructive py-2">
            {eventsQuery.error instanceof Error
              ? eventsQuery.error.message
              : 'Could not load sky events.'}
          </p>
        )}

        {eventsQuery.data && (
          <EventList events={eventsQuery.data.events} tz={tz} multiDay={multiDay} />
        )}
      </section>

      {/* Divider */}
      <div className="h-px bg-border my-8" />

      {/* Current sky toggle */}
      <section>
        <button
          onClick={() => setShowSky((v) => !v)}
          className="flex items-center gap-2 w-full group mb-4"
        >
          <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground select-none group-hover:text-foreground transition-colors">
            Current sky
          </p>
          <span className="text-muted-foreground group-hover:text-foreground transition-colors">
            {showSky ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </span>
        </button>

        {showSky && (
          <>
            {skyQuery.isPending && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                <Loader2 size={14} className="animate-spin" />
                <span>Computing sky…</span>
              </div>
            )}
            {skyQuery.isError && (
              <p className="text-sm text-destructive">Could not load current sky.</p>
            )}
            {skyQuery.data && (
              <BodyTable bodies={skyQuery.data.bodies} showHouses={false} />
            )}
          </>
        )}
      </section>

      {/* Compare with saved charts */}
      {charts.length > 0 && (
        <>
          <div className="h-px bg-border my-8" />
          <section>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4 select-none">
              Compare with chart
            </p>
            <ul className="space-y-1">
              {charts.map((chart) => (
                <li key={chart.id}>
                  <Link
                    to={`/charts/${chart.id}/transits`}
                    className="flex items-center justify-between py-2 border-b border-border/30 last:border-0 group"
                  >
                    <span className="text-sm font-medium group-hover:text-primary transition-colors">
                      {chart.name}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {chart.input.date}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}

      {/* Calendar link for date range events */}
      <div className="h-px bg-border my-8" />
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Calendar size={12} />
        <span>
          Events computed from JPL ephemerides · Moon events use IAU real-sky boundaries
        </span>
      </div>
    </div>
  )
}
