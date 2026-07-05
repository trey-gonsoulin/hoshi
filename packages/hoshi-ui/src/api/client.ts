import type { components } from './types'

export type ChartCompute = components['schemas']['ChartCompute']
export type ChartOutput = components['schemas']['ChartOutput']
export type BodyEntry = components['schemas']['BodyEntry']
export type Aspect = components['schemas']['Aspect']
export type TallyOutput = components['schemas']['TallyOutput']
export type ChartHeader = components['schemas']['ChartHeader']
export type CuspsOutput = components['schemas']['CuspsOutput']
export type CuspsRequest = components['schemas']['CuspsRequest']
export type TransitsOutput = components['schemas']['TransitsOutput']
export type TransitsRequest = components['schemas']['TransitsRequest']
export type CompareOutput = components['schemas']['CompareOutput']
export type CompareRequest = components['schemas']['CompareRequest']
export type ChartData = components['schemas']['ChartData']
export type ZodiacMode = components['schemas']['ZodiacMode']
export type HouseSystem = components['schemas']['HouseSystem']

// Sky types — defined inline (not yet in auto-generated types.ts)
export interface SkyEventEntry {
  when: string          // ISO 8601 UTC
  event_type: string    // "retrograde_station" | "direct_station" | "ingress" | "moon_new" | etc.
  body: string
  body_symbol: string
  detail: string
  sign?: string | null
  sign_symbol?: string | null
  body_b?: string | null
  aspect_name?: string | null
  aspect_symbol?: string | null
}

export interface SkyEventsOutput {
  events: SkyEventEntry[]
  mode: string
  from_date: string
  to_date: string
}

export interface SkyEventsParams {
  from?: string
  to?: string
  mode?: ZodiacMode
  tz?: string
  stations?: boolean
  ingresses?: boolean
  phases?: boolean
  voc?: boolean
  aspects?: boolean
}

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) })
}

function get<T>(path: string, params?: Record<string, string | boolean | undefined>): Promise<T> {
  const qs = params
    ? '?' + new URLSearchParams(
        Object.entries(params)
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => [k, String(v)])
      ).toString()
    : ''
  return request<T>(`${path}${qs}`, { method: 'GET' })
}

export const api = {
  computeChart: (body: ChartCompute) =>
    post<ChartOutput>('/charts/compute', body),

  importChart: (source: string, opts?: Partial<Omit<ChartCompute, 'date'>>) =>
    post<ChartOutput>('/charts/import', { source, ...opts }),

  chartCusps: (body: CuspsRequest) =>
    post<CuspsOutput>('/charts/cusps', body),

  chartTransits: (body: TransitsRequest) =>
    post<TransitsOutput>('/charts/transits', body),

  chartCompare: (body: CompareRequest) =>
    post<CompareOutput>('/charts/compare', body),

  skyNow: (opts?: { mode?: ZodiacMode; tz?: string }) =>
    get<ChartOutput>('/sky/now', { mode: opts?.mode, tz: opts?.tz }),

  skyEvents: (params: SkyEventsParams) =>
    get<SkyEventsOutput>('/sky/events', {
      from: params.from,
      to: params.to,
      mode: params.mode,
      tz: params.tz,
      stations: params.stations,
      ingresses: params.ingresses,
      phases: params.phases,
      voc: params.voc,
      aspects: params.aspects,
    }),
}
