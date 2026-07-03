import type { ChartCompute, ChartData } from '@/api/client'

export function chartDataFrom(input: ChartCompute): ChartData {
  return {
    date: input.date,
    time: input.time ?? undefined,
    lat: input.lat ?? undefined,
    lon: input.lon ?? undefined,
    location: input.location ?? undefined,
    tz: input.tz,
  }
}
