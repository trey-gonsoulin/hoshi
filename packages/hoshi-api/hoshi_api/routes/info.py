"""Reference info endpoints."""

from enum import StrEnum

from fastapi import APIRouter, HTTPException

from hoshi.output import InfoDetailOutput, InfoListOutput
from hoshi.utils import fuzzy_match

router = APIRouter(prefix="/info", tags=["info"])


class InfoCategory(StrEnum):
    planets = "planets"
    signs = "signs"
    angles = "angles"
    aspects = "aspects"
    houses = "houses"
    points = "points"


_EXTRA_COLS: dict[str, list[str]] = {
    "signs": ["Element", "Modality", "Ruler", "Cusp", "Size"],
}


def _catalog_for(category: InfoCategory) -> dict:
    from hoshi.info import ANGLES, ASPECTS, HOUSES, PLANETS, POINTS, SIGNS

    return {
        InfoCategory.planets: PLANETS,
        InfoCategory.signs: SIGNS,
        InfoCategory.angles: ANGLES,
        InfoCategory.aspects: ASPECTS,
        InfoCategory.houses: HOUSES,
        InfoCategory.points: POINTS,
    }[category]


@router.get("/{category}", response_model=InfoListOutput)
def list_info(category: InfoCategory) -> InfoListOutput:
    catalog = _catalog_for(category)
    extra = _EXTRA_COLS.get(category, [])
    return InfoListOutput.build(
        category.value.capitalize(), list(catalog.values()), extra_cols=extra
    )


@router.get("/{category}/{name}", response_model=InfoDetailOutput)
def get_info(category: InfoCategory, name: str) -> InfoDetailOutput:
    catalog = _catalog_for(category)
    if category == InfoCategory.houses:
        try:
            item = catalog.get(int(name))
        except ValueError:
            item = None
    else:
        item = fuzzy_match(name, catalog)
    if item is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown {category.value[:-1]}: {name!r}"
        )
    return InfoDetailOutput.build(item)
