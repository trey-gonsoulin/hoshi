import rawData from './astroData.json'

export interface InfoEntry {
  name: string
  keywords: string[]
  meaning: string
  aliases: string[]
}

export interface SignEntry extends InfoEntry {
  element: string
  modality: string
  ruler: string
  lo: number
  size: number
}

interface AstroData {
  planets: Record<string, InfoEntry>
  signs: Record<string, SignEntry>
  angles: Record<string, InfoEntry>
  aspects: Record<string, InfoEntry>
  houses: Record<string, InfoEntry>
  points: Record<string, InfoEntry>
  dignities: Record<string, InfoEntry>
  retrograde: InfoEntry
}

const data = rawData as AstroData

// Lookup helpers for tooltip use

export function lookupBody(name: string): InfoEntry | undefined {
  return data.planets[name] ?? data.angles[name] ?? data.points[name]
}

export function lookupSign(name: string): SignEntry | undefined {
  return data.signs[name]
}

export function lookupHouse(n: number): InfoEntry | undefined {
  return data.houses[String(n)]
}

export function lookupAspect(name: string): InfoEntry | undefined {
  return data.aspects[name]
}

export function lookupRetrograde(): InfoEntry {
  return data.retrograde
}

// Maps dignity symbol → key in data.dignities
const DIGNITY_SYMBOL_KEY: Record<string, string> = {
  '⊕': 'domicile',
  '△': 'exaltation',
  '▽': 'detriment',
  '✕': 'fall',
}

export function lookupDignity(symbol: string): InfoEntry | undefined {
  const key = DIGNITY_SYMBOL_KEY[symbol]
  return key ? data.dignities[key] : undefined
}

export function getAllSigns(): Record<string, SignEntry> {
  return data.signs
}

// Page-level helpers — return shapes matching what InfoCategoryPage / InfoDetailPage expect

export type InfoItem = {
  name: string
  keywords: string[]
  element?: string | null
  modality?: string | null
  ruler?: string | null
  cusp?: number | null
  size?: number | null
}

export type InfoListResult = { title: string; items: InfoItem[] }

export type InfoDetailResult = {
  name: string
  keywords: string[]
  meaning: string
  element?: string | null
  modality?: string | null
  ruler?: string | null
  cusp?: number | null
  size?: number | null
}

const CATEGORY_TITLE: Record<string, string> = {
  planets: 'Planets',
  signs: 'Signs',
  angles: 'Angles',
  aspects: 'Aspects',
  houses: 'Houses',
  points: 'Points',
}

function _toItem(entry: InfoEntry | SignEntry): InfoItem {
  const s = entry as SignEntry
  return {
    name: entry.name,
    keywords: entry.keywords,
    element: s.element ?? null,
    modality: s.modality ?? null,
    ruler: s.ruler ?? null,
    cusp: s.lo ?? null,
    size: s.size ?? null,
  }
}

type AnyRecord = Record<string, InfoEntry>

export function getInfoList(category: string): InfoListResult | null {
  const catalog = (data as unknown as Record<string, unknown>)[category]
  if (!catalog || typeof catalog !== 'object' || Array.isArray(catalog)) return null
  const title = CATEGORY_TITLE[category] ?? category
  const items = Object.values(catalog as AnyRecord).map(_toItem)
  return { title, items }
}

export function getInfoDetail(category: string, name: string): InfoDetailResult | null {
  const catalog = (data as unknown as Record<string, unknown>)[category]
  if (!catalog || typeof catalog !== 'object' || Array.isArray(catalog)) return null
  const map = catalog as AnyRecord
  const normalized = name.toLowerCase()
  const entry =
    map[name] ??
    Object.values(map).find(
      (v) =>
        v.name.toLowerCase() === normalized ||
        v.aliases.some((a) => a.toLowerCase() === normalized),
    )
  if (!entry) return null
  const s = entry as SignEntry
  return {
    name: entry.name,
    keywords: entry.keywords,
    meaning: entry.meaning,
    element: s.element ?? null,
    modality: s.modality ?? null,
    ruler: s.ruler ?? null,
    cusp: s.lo ?? null,
    size: s.size ?? null,
  }
}
