/**
 * GraphQL client for the Hoshi API.
 *
 * All response types use camelCase field names — Strawberry auto-converts
 * Python snake_case to camelCase in the GraphQL schema.
 */

export type ZodiacMode = 'realsky' | 'tropical' | 'vedic'
export type HouseSystem = 'porphyry' | 'equal' | 'placidus' | 'arc13'

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface BodyEntry {
  kind: string
  name: string
  sign: string
  signSymbol: string
  degree: number
  lon: number
  house?: number | null
  rx: boolean
  approximate: boolean
  dignity: string
  symbol: string
}

export interface Aspect {
  bodyA: string
  signA: string
  bodyB: string
  signB: string
  name: string
  symbol: string
  angle: number
  orb: number
  kind: string
}

export interface TallyRow {
  primary: number
  total: number
}

export interface ElementTally {
  fire: TallyRow
  earth: TallyRow
  air: TallyRow
  water: TallyRow
}

export interface ModalityTally {
  cardinal: TallyRow
  fixed: TallyRow
  mutable: TallyRow
}

export interface TallyOutput {
  elements: ElementTally
  modalities: ModalityTally
}

export interface ChartHeader {
  name: string
  when: string
  lat?: number | null
  lon?: number | null
  mode: string
  houseSystem?: string | null
}

export interface PlacementFrac {
  sign: string
  fraction: number
}

export interface PlacementDist {
  pid: string
  fracs: PlacementFrac[]
}

export interface ChartOutput {
  chart: ChartHeader
  warnings: string[]
  bodies: BodyEntry[]
  cusps: number[]
  tallies?: TallyOutput | null
  aspects?: Aspect[] | null
  placementDist?: PlacementDist[] | null
}

export interface BirthWindow {
  start: string // ISO datetime string
  end: string
}

export interface BirthRangeWindow {
  start: string
  end: string
  durationDays: number
}

export interface BirthRangeResultOutput {
  constraints: string[]
  mode: string
  searchStart: string
  searchEnd: string
  stepHours: number
  windows: BirthRangeWindow[]
}

export interface ConstraintInput {
  planet: string
  sign: string
}

export interface BirthRangeRequest {
  constraints: ConstraintInput[]
  fromDate: string
  toDate?: string | null
  mode: ZodiacMode
  lat?: number | null
  lon?: number | null
}

export interface CuspEntry {
  house: number
  sign: string
  degree: number
  lon: number
}

export interface CuspsOutput {
  houseSystem: string
  cusps: CuspEntry[]
}

export interface TransitHeader {
  name: string
  natalDate: string
  transitWhen: string
  mode: string
  houseSystem?: string | null
}

export interface TransitsOutput {
  header: TransitHeader
  warnings: string[]
  transitBodies: BodyEntry[]
  natalBodies?: BodyEntry[] | null
  aspects?: Aspect[] | null
}

export interface CompareHeader {
  nameA: string
  nameB: string
  dateA: string
  dateB: string
  mode: string
}

export interface CompareOutput {
  header: CompareHeader
  warnings: string[]
  bodiesA: BodyEntry[]
  bodiesB: BodyEntry[]
  aspects?: Aspect[] | null
}

export interface CompositeHeader {
  nameA: string
  nameB: string
  dateA: string
  dateB: string
  mode: string
  houseSystem?: string | null
}

export interface CompositeOutput {
  header: CompositeHeader
  warnings: string[]
  bodies: BodyEntry[]
  cusps: number[]
  aspects?: Aspect[] | null
}

export interface SkyEventEntry {
  when: string
  eventType: string
  body: string
  bodySymbol: string
  detail: string
  sign?: string | null
  signSymbol?: string | null
  bodyB?: string | null
  aspectName?: string | null
  aspectSymbol?: string | null
}

export interface SkyEventsOutput {
  events: SkyEventEntry[]
  mode: string
  fromDate: string
  toDate: string
}

// ---------------------------------------------------------------------------
// Input types (form state / saved chart data — not API response shapes)
// ---------------------------------------------------------------------------

export interface ChartData {
  date: string
  time?: string | null
  lat?: number | null
  lon?: number | null
  location?: string | null
  tz: string
}

export interface ChartCompute extends ChartData {
  mode: ZodiacMode
  houses: HouseSystem
  details: boolean
  aspects: boolean
  cusps: boolean
  birthWindows?: BirthWindow[] | null
}

export interface TransitsRequest {
  natal: ChartData
  date?: string | null
  time?: string | null
  tz: string
  mode: ZodiacMode
  houses: HouseSystem
  details: boolean
  aspects: boolean
  showNatal: boolean
  tier: string
  sensitivity: string
}

export interface ForecastRequest {
  natal: ChartData
  fromDate?: string | null
  toDate?: string | null
  tz: string
  mode: ZodiacMode
  houses: HouseSystem
  tier: string
  details: boolean
  sensitivity: string
}

export interface CompareRequest {
  chartA: ChartData
  chartB: ChartData
  mode: ZodiacMode
  houses: HouseSystem
  details: boolean
  aspects: boolean
}

export interface CompositeRequest {
  chartA: ChartData
  chartB: ChartData
  mode: ZodiacMode
  houses: HouseSystem
  details: boolean
  aspects: boolean
}

export interface CompositeTransitsRequest {
  chartA: ChartData
  chartB: ChartData
  date?: string | null
  time?: string | null
  tz: string
  mode: ZodiacMode
  houses: HouseSystem
  details: boolean
  aspects: boolean
  showNatal: boolean
  tier: string
  sensitivity: string
}

export interface ForecastHeader {
  name: string
  natalDate: string
  fromDate: string
  toDate: string
  mode: string
  tier: string
  houseSystem?: string | null
}

export interface TransitAspect extends Aspect {
  ingress?: string | null
  exact: string[]
  egress?: string | null
  passCount: number
  currentPass?: number | null
  tier: string
  natalSensitivity: string
}

export interface ForecastOutput {
  header: ForecastHeader
  warnings: string[]
  aspects: TransitAspect[]
}

export interface CompositeForecastRequest {
  chartA: ChartData
  chartB: ChartData
  fromDate?: string | null
  toDate?: string | null
  tz: string
  mode: ZodiacMode
  houses: HouseSystem
  tier: string
  details: boolean
  sensitivity: string
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

// ---------------------------------------------------------------------------
// GraphQL fragments
// ---------------------------------------------------------------------------

const BODY_FIELDS = `kind name sign signSymbol degree lon house rx approximate dignity symbol`

const ASPECT_FIELDS = `bodyA signA bodyB signB name symbol angle orb kind`

const TALLY_FIELDS = `
  elements {
    fire { primary total } earth { primary total }
    air  { primary total } water { primary total }
  }
  modalities {
    cardinal { primary total } fixed { primary total } mutable { primary total }
  }
`

const CHART_RESULT_FIELDS = `
  chart { name when lat lon mode houseSystem }
  warnings
  bodies { ${BODY_FIELDS} }
  cusps
  tallies { ${TALLY_FIELDS} }
  aspects { ${ASPECT_FIELDS} }
  placementDist { pid fracs { sign fraction } }
`

// ---------------------------------------------------------------------------
// GraphQL executor
// ---------------------------------------------------------------------------

const GQL = '/api/graphql'

async function gql<T>(query: string, variables?: Record<string, unknown>): Promise<T> {
  const res = await fetch(GQL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, variables }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { errors?: { message: string }[] }
    throw new Error(body?.errors?.[0]?.message ?? `HTTP ${res.status}`)
  }
  const json = await res.json() as { data?: T; errors?: { message: string }[] }
  if (json.errors?.length) throw new Error(json.errors[0].message)
  return json.data as T
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

export const api = {
  computeChart: (req: ChartCompute): Promise<ChartOutput> =>
    gql<{ chart: ChartOutput }>(
      `query ComputeChart(
        $date: String!, $tz: String!,
        $time: String, $lat: Float, $lon: Float, $location: String,
        $mode: ZodiacMode!, $houses: HouseSystem!, $details: Boolean!, $aspects: Boolean!,
        $birthWindows: [BirthWindowInput!]
      ) {
        chart(date: $date, tz: $tz, time: $time, lat: $lat, lon: $lon,
              location: $location, mode: $mode, houses: $houses,
              details: $details, aspects: $aspects, birthWindows: $birthWindows) { ${CHART_RESULT_FIELDS} }
      }`,
      {
        date: req.date,
        tz: req.tz,
        time: req.time ?? null,
        lat: req.lat ?? null,
        lon: req.lon ?? null,
        location: req.location ?? null,
        mode: req.mode,
        houses: req.houses,
        details: req.details,
        aspects: req.aspects,
        birthWindows: req.birthWindows ?? null,
      },
    ).then((d) => d.chart),

  birthRange: (req: BirthRangeRequest): Promise<BirthRangeResultOutput> =>
    gql<{ birthRange: BirthRangeResultOutput }>(
      `query BirthRange(
        $constraints: [ConstraintInput!]!,
        $fromDate: String!, $toDate: String,
        $mode: ZodiacMode!, $lat: Float, $lon: Float
      ) {
        birthRange(constraints: $constraints, fromDate: $fromDate, toDate: $toDate,
                   mode: $mode, lat: $lat, lon: $lon) {
          constraints mode searchStart searchEnd stepHours
          windows { start end durationDays }
        }
      }`,
      {
        constraints: req.constraints,
        fromDate: req.fromDate,
        toDate: req.toDate ?? null,
        mode: req.mode,
        lat: req.lat ?? null,
        lon: req.lon ?? null,
      },
    ).then((d) => d.birthRange),

  importChart: (source: string, opts?: Partial<Omit<ChartCompute, 'date'>>): Promise<ChartOutput> =>
    gql<{ importChart: ChartOutput }>(
      `query ImportChart(
        $source: String!, $mode: ZodiacMode!, $houses: HouseSystem!,
        $details: Boolean!, $aspects: Boolean!
      ) {
        importChart(source: $source, mode: $mode, houses: $houses,
                    details: $details, aspects: $aspects) { ${CHART_RESULT_FIELDS} }
      }`,
      {
        source,
        mode: opts?.mode ?? 'realsky',
        houses: opts?.houses ?? 'porphyry',
        details: opts?.details ?? false,
        aspects: opts?.aspects ?? false,
      },
    ).then((d) => d.importChart),

  chartTransits: (req: TransitsRequest): Promise<TransitsOutput> =>
    gql<{ transits: TransitsOutput }>(
      `query ChartTransits(
        $natal: ChartDataInput!, $tz: String!,
        $date: String, $time: String,
        $mode: ZodiacMode!, $houses: HouseSystem!,
        $details: Boolean!, $aspects: Boolean!, $showNatal: Boolean!,
        $tier: String!, $sensitivity: String!
      ) {
        transits(natal: $natal, tz: $tz, date: $date, time: $time,
                 mode: $mode, houses: $houses, details: $details,
                 aspects: $aspects, showNatal: $showNatal,
                 tier: $tier, sensitivity: $sensitivity) {
          header { name natalDate transitWhen mode houseSystem }
          warnings
          transitBodies { ${BODY_FIELDS} }
          natalBodies { ${BODY_FIELDS} }
          aspects { ${ASPECT_FIELDS} ingress exact egress passCount currentPass tier natalSensitivity }
        }
      }`,
      {
        natal: req.natal,
        tz: req.tz,
        date: req.date ?? null,
        time: req.time ?? null,
        mode: req.mode,
        houses: req.houses,
        details: req.details,
        aspects: req.aspects,
        showNatal: req.showNatal,
        tier: req.tier,
        sensitivity: req.sensitivity,
      },
    ).then((d) => d.transits),

  chartForecast: (req: ForecastRequest): Promise<ForecastOutput> =>
    gql<{ forecast: ForecastOutput }>(
      `query ChartForecast(
        $natal: ChartDataInput!, $tz: String!,
        $fromDate: String, $toDate: String,
        $mode: ZodiacMode!, $houses: HouseSystem!,
        $tier: String!, $details: Boolean!, $sensitivity: String!
      ) {
        forecast(natal: $natal, tz: $tz, fromDate: $fromDate, toDate: $toDate,
                 mode: $mode, houses: $houses, tier: $tier, details: $details,
                 sensitivity: $sensitivity) {
          header { name natalDate fromDate toDate mode tier houseSystem }
          warnings
          aspects { ${ASPECT_FIELDS} ingress exact egress passCount currentPass tier natalSensitivity }
        }
      }`,
      {
        natal: req.natal,
        tz: req.tz,
        fromDate: req.fromDate ?? null,
        toDate: req.toDate ?? null,
        mode: req.mode,
        houses: req.houses,
        tier: req.tier,
        details: req.details,
        sensitivity: req.sensitivity,
      },
    ).then((d) => d.forecast),

  chartCompare: (req: CompareRequest): Promise<CompareOutput> =>
    gql<{ compare: CompareOutput }>(
      `query ChartCompare(
        $chartA: ChartDataInput!, $chartB: ChartDataInput!,
        $mode: ZodiacMode!, $houses: HouseSystem!,
        $details: Boolean!, $aspects: Boolean!
      ) {
        compare(chartA: $chartA, chartB: $chartB, mode: $mode, houses: $houses,
                details: $details, aspects: $aspects) {
          header { nameA nameB dateA dateB mode }
          warnings
          bodiesA { ${BODY_FIELDS} }
          bodiesB { ${BODY_FIELDS} }
          aspects { ${ASPECT_FIELDS} }
        }
      }`,
      {
        chartA: req.chartA,
        chartB: req.chartB,
        mode: req.mode,
        houses: req.houses,
        details: req.details,
        aspects: req.aspects,
      },
    ).then((d) => d.compare),

  chartComposite: (req: CompositeRequest): Promise<CompositeOutput> =>
    gql<{ composite: CompositeOutput }>(
      `query ChartComposite(
        $chartA: ChartDataInput!, $chartB: ChartDataInput!,
        $mode: ZodiacMode!, $houses: HouseSystem!,
        $details: Boolean!, $aspects: Boolean!
      ) {
        composite(chartA: $chartA, chartB: $chartB, mode: $mode, houses: $houses,
                  details: $details, aspects: $aspects) {
          header { nameA nameB dateA dateB mode houseSystem }
          warnings
          bodies { ${BODY_FIELDS} }
          cusps
          aspects { ${ASPECT_FIELDS} }
        }
      }`,
      {
        chartA: req.chartA,
        chartB: req.chartB,
        mode: req.mode,
        houses: req.houses,
        details: req.details,
        aspects: req.aspects,
      },
    ).then((d) => d.composite),

  chartCompositeTransits: (req: CompositeTransitsRequest): Promise<TransitsOutput> =>
    gql<{ compositeTransits: TransitsOutput }>(
      `query ChartCompositeTransits(
        $chartA: ChartDataInput!, $chartB: ChartDataInput!,
        $tz: String!, $date: String, $time: String,
        $mode: ZodiacMode!, $houses: HouseSystem!,
        $details: Boolean!, $aspects: Boolean!, $showNatal: Boolean!,
        $tier: String!, $sensitivity: String!
      ) {
        compositeTransits(chartA: $chartA, chartB: $chartB, tz: $tz, date: $date,
                          time: $time, mode: $mode, houses: $houses, details: $details,
                          aspects: $aspects, showNatal: $showNatal, tier: $tier,
                          sensitivity: $sensitivity) {
          header { name natalDate transitWhen mode houseSystem }
          warnings
          transitBodies { ${BODY_FIELDS} }
          natalBodies { ${BODY_FIELDS} }
          aspects { ${ASPECT_FIELDS} }
        }
      }`,
      {
        chartA: req.chartA,
        chartB: req.chartB,
        tz: req.tz,
        date: req.date ?? null,
        time: req.time ?? null,
        mode: req.mode,
        houses: req.houses,
        details: req.details,
        aspects: req.aspects,
        showNatal: req.showNatal,
        tier: req.tier,
        sensitivity: req.sensitivity,
      },
    ).then((d) => d.compositeTransits),

  chartCompositeForecast: (req: CompositeForecastRequest): Promise<ForecastOutput> =>
    gql<{ compositeForecast: ForecastOutput }>(
      `query ChartCompositeForecast(
        $chartA: ChartDataInput!, $chartB: ChartDataInput!,
        $tz: String!, $fromDate: String, $toDate: String,
        $mode: ZodiacMode!, $houses: HouseSystem!,
        $tier: String!, $details: Boolean!, $sensitivity: String!
      ) {
        compositeForecast(chartA: $chartA, chartB: $chartB, tz: $tz,
                          fromDate: $fromDate, toDate: $toDate, mode: $mode,
                          houses: $houses, tier: $tier, details: $details,
                          sensitivity: $sensitivity) {
          header { name natalDate fromDate toDate mode tier houseSystem }
          warnings
          aspects { ${ASPECT_FIELDS} ingress exact egress passCount currentPass tier natalSensitivity }
        }
      }`,
      {
        chartA: req.chartA,
        chartB: req.chartB,
        tz: req.tz,
        fromDate: req.fromDate ?? null,
        toDate: req.toDate ?? null,
        mode: req.mode,
        houses: req.houses,
        tier: req.tier,
        details: req.details,
        sensitivity: req.sensitivity,
      },
    ).then((d) => d.compositeForecast),

  skyNow: (opts?: { mode?: ZodiacMode; tz?: string }): Promise<ChartOutput> =>
    gql<{ skyNow: ChartOutput }>(
      `query SkyNow($mode: ZodiacMode!, $tz: String!) {
        skyNow(mode: $mode, tz: $tz) {
          chart { name when lat lon mode houseSystem }
          warnings
          bodies { ${BODY_FIELDS} }
        }
      }`,
      { mode: opts?.mode ?? 'realsky', tz: opts?.tz ?? 'UTC' },
    ).then((d) => d.skyNow),

  skyEvents: (params: SkyEventsParams): Promise<SkyEventsOutput> =>
    gql<{ skyEvents: SkyEventsOutput }>(
      `query SkyEvents(
        $tz: String!, $fromDate: String, $toDate: String, $mode: ZodiacMode!,
        $stations: Boolean!, $ingresses: Boolean!, $phases: Boolean!,
        $voc: Boolean!, $aspects: Boolean!
      ) {
        skyEvents(tz: $tz, fromDate: $fromDate, toDate: $toDate, mode: $mode,
                  stations: $stations, ingresses: $ingresses, phases: $phases,
                  voc: $voc, aspects: $aspects) {
          events { when eventType body bodySymbol detail sign signSymbol bodyB aspectName aspectSymbol }
          mode fromDate toDate
        }
      }`,
      {
        tz: params.tz ?? 'UTC',
        fromDate: params.from ?? null,
        toDate: params.to ?? null,
        mode: params.mode ?? 'realsky',
        stations: params.stations ?? true,
        ingresses: params.ingresses ?? true,
        phases: params.phases ?? true,
        voc: params.voc ?? true,
        aspects: params.aspects ?? true,
      },
    ).then((d) => d.skyEvents),
}
