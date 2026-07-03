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
export type InfoListOutput = components['schemas']['InfoListOutput']
export type InfoDetailOutput = components['schemas']['InfoDetailOutput']
export type ZodiacMode = components['schemas']['ZodiacMode']
export type HouseSystem = components['schemas']['HouseSystem']

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

function get<T>(path: string): Promise<T> {
  return request<T>(path)
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

  listInfo: (category: string) =>
    get<InfoListOutput>(`/info/${category}`),

  getInfo: (category: string, name: string) =>
    get<InfoDetailOutput>(`/info/${category}/${encodeURIComponent(name)}`),
}
