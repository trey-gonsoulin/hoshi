# hoshi-ui

Textual TUI for [Hoshi](../../README.md) — a terminal user interface for browsing and comparing real-sky astrological charts.

## Running

```bash
uv run --package hoshi-ui hoshi-ui
```

## Screens

| Screen | Description |
|--------|-------------|
| Chart list | Browse all saved charts in `./charts/` |
| Chart detail | Full chart display with bodies, aspects, and dignities |
| Transits | Current (or specified date) transits against a natal chart |
| Compare | Synastry between two saved charts |
| Info | Reference browser for signs, planets, aspects, and houses |

## Navigation

Charts saved with `hoshi chart add` appear in the chart list. Select one to open the detail view; from there you can open transits or pick a second chart for synastry.

## Development

```bash
uv run --package hoshi-ui pytest packages/hoshi-ui/tests/

uv run ruff check --fix . && uv run ruff format .
```
