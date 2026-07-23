"""Real-sky astrology calculations — Python port of Nuastro.

This top-level module is the stable SDK surface. Import the domain types and
functions from here rather than the internal submodules, e.g.::

    from hoshi import Chart, ChartInput, ZodiacMode, compute_aspects

    ci = ChartInput(name="ada", date="1815-12-10", time="13:00",
                    tz="Europe/London", lat=51.5, lon=-0.13)
    chart = Chart.from_input(ci)
    for body in chart.bodies():
        print(body.label, body.placed.placement(ZodiacMode.realsky).name)
    aspects = compute_aspects(chart)
"""

from hoshi.adb import ADBError, ADBResult, adb_to_chart_input
from hoshi.events import BODY_DISPLAY, BODY_SYMBOL, SIGN_SYMBOL, SkyEvent, sky_events
from hoshi.output import (
    BodySelection,
    ChartListOutput,
    ChartOutput,
    CompareOutput,
    CuspsOutput,
    ForecastHeader,
    ForecastOutput,
    HouseComparisonOutput,
    InfoDetailOutput,
    InfoListOutput,
    SkyEventsOutput,
    TransitAspect,
    TransitsOutput,
)
from hoshi.utils import fuzzy_match
from hoshi.aspects import (
    ASPECT_DEFS,
    Aspect,
    AspectDef,
    compute_aspects,
    compute_inter_aspects,
)
from hoshi.chart import (
    AngleChart,
    BodyRef,
    Chart,
    HouseSystem,
    Placed,
    PlanetChart,
    PointChart,
    uncertain_signs,
)
from hoshi.dignities import (
    chart_ruler,
    dignity_for,
    element_modality_tally,
    natal_sensitivity,
)
from hoshi.ephemeris import (
    PLANET_ORDER,
    HorizonsError,
    PlanetPosition,
    ecliptic_precession,
    lahiri_ayanamsa,
    positions,
)
from hoshi.houses import Angles
from hoshi.points import HERMETIC_LOT_NAMES, LunarElements, hermetic_lots
from hoshi.transits import (
    ForecastWindow,
    TransitTier,
    forecast_transits,
    transit_aspect_window,
    transit_tier,
)
from hoshi.birthrange import (
    BirthDateRange,
    Constraint,
    PlacementFraction,
    SCANNABLE_ANGLES,
    SCANNABLE_PLANETS,
    find_birth_date_ranges,
    placement_proportions,
)
from hoshi.output import BirthRangeOutput
from hoshi.store import BirthWindow, ChartInput
from hoshi.zodiac import (
    IAU,
    PLANET_GLYPHS,
    SIGN_ATTRS,
    SIGN_GLYPHS,
    TROP_SIGNS,
    IAUSign,
    Placement,
    SignInfo,
    ZodiacMode,
    format_deg,
)

__version__ = "1.0.0"

__all__ = [
    "__version__",
    # Charts
    "Chart",
    "ChartInput",
    "Placed",
    "BodyRef",
    "PlanetChart",
    "AngleChart",
    "PointChart",
    "HouseSystem",
    "uncertain_signs",
    # Zodiac placement
    "ZodiacMode",
    "Placement",
    "IAU",
    "IAUSign",
    "TROP_SIGNS",
    "SignInfo",
    "SIGN_ATTRS",
    "SIGN_GLYPHS",
    "PLANET_GLYPHS",
    "format_deg",
    # Ephemeris
    "positions",
    "PlanetPosition",
    "PLANET_ORDER",
    "lahiri_ayanamsa",
    "ecliptic_precession",
    "HorizonsError",
    # Houses, points, lots
    "Angles",
    "LunarElements",
    "hermetic_lots",
    "HERMETIC_LOT_NAMES",
    # Aspects
    "Aspect",
    "AspectDef",
    "ASPECT_DEFS",
    "compute_aspects",
    "compute_inter_aspects",
    # Dignities
    "dignity_for",
    "element_modality_tally",
    "chart_ruler",
    "natal_sensitivity",
    # ADB import
    "ADBError",
    "ADBResult",
    "adb_to_chart_input",
    # Sky events
    "SkyEvent",
    "sky_events",
    "BODY_DISPLAY",
    "BODY_SYMBOL",
    "SIGN_SYMBOL",
    # Transit windows and forecast
    "TransitTier",
    "transit_aspect_window",
    "transit_tier",
    "ForecastWindow",
    "forecast_transits",
    # Output models
    "BodySelection",
    "ChartOutput",
    "ChartListOutput",
    "CuspsOutput",
    "TransitAspect",
    "TransitsOutput",
    "ForecastHeader",
    "ForecastOutput",
    "CompareOutput",
    "HouseComparisonOutput",
    "InfoDetailOutput",
    "InfoListOutput",
    "SkyEventsOutput",
    "BirthRangeOutput",
    # Birth date range and placement proportions
    "Constraint",
    "BirthDateRange",
    "PlacementFraction",
    "SCANNABLE_ANGLES",
    "SCANNABLE_PLANETS",
    "find_birth_date_ranges",
    "placement_proportions",
    "BirthWindow",
    # Utilities
    "fuzzy_match",
]
