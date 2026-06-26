from __future__ import annotations

from textual.app import App
from textual.binding import Binding
from textual.reactive import reactive

from hoshi_ui.screens.chart_list import ChartListScreen


MODES = ["realsky", "tropical", "vedic"]
GROUP_BY_OPTIONS = ["category", "sign", "house", "planet"]
HOUSE_SYSTEMS = ["porphyry", "placidus", "equal", "arc13"]


class HoshiApp(App):
    TITLE = "hoshi"
    SUB_TITLE = "real-sky astrology"

    CSS = """
    #chart-header, #transit-header, #compare-header, #compare-hint {
        height: auto;
        padding: 0 1;
        color: $accent;
    }

    #chart-select {
        margin: 1 2;
    }

    #loading {
        height: 1fr;
    }

    DataTable {
        height: auto;
    }

    VerticalScroll {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("m", "cycle_mode", "Mode"),
        Binding("d", "toggle_details", "Details"),
        Binding("a", "toggle_aspects", "Aspects"),
        Binding("g", "cycle_group_by", "Group by"),
        Binding("h", "cycle_house_system", "Houses"),
    ]

    zodiac_mode = reactive("realsky")
    details = reactive(False)
    aspects = reactive(False)
    group_by = reactive("category")
    house_system = reactive("porphyry")

    def on_mount(self) -> None:
        self.push_screen(ChartListScreen())

    def action_cycle_mode(self) -> None:
        idx = (MODES.index(self.zodiac_mode) + 1) % len(MODES)
        self.zodiac_mode = MODES[idx]
        self.sub_title = f"mode: {self.zodiac_mode}"

    def action_toggle_details(self) -> None:
        self.details = not self.details

    def action_toggle_aspects(self) -> None:
        self.aspects = not self.aspects

    def action_cycle_group_by(self) -> None:
        idx = (GROUP_BY_OPTIONS.index(self.group_by) + 1) % len(GROUP_BY_OPTIONS)
        self.group_by = GROUP_BY_OPTIONS[idx]

    def action_cycle_house_system(self) -> None:
        idx = (HOUSE_SYSTEMS.index(self.house_system) + 1) % len(HOUSE_SYSTEMS)
        self.house_system = HOUSE_SYSTEMS[idx]


def cli() -> None:
    app = HoshiApp()
    app.run()
