# hoshi-api

REST API for [Hoshi](../../README.md) — real-sky astrological charting. Built with FastAPI and backed by the same JPL ephemerides as the CLI.

The API is stateless: chart data is computed on each request rather than stored server-side. All endpoints accept full birth parameters in the request body and return the computed chart.

## Running locally

```bash
uv run --package hoshi-api hoshi-api
```

Interactive docs at `http://localhost:8000/docs`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/charts/compute` | Compute a chart from birth parameters |
| `POST` | `/charts/import` | Import from Astro-Databank by name |
| `POST` | `/charts/cusps` | House cusps for a given time and location |
| `POST` | `/charts/transits` | Transiting planets against a natal chart |
| `POST` | `/charts/compare` | Synastry between two charts |
| `GET` | `/info/{category}` | Reference info (signs, planets, aspects, …) |
| `GET` | `/info/{category}/{name}` | Single item detail |

## Example

```bash
curl -s http://localhost:8000/charts/compute \
  -H "Content-Type: application/json" \
  -d '{
    "date": "1815-12-10",
    "time": "13:00",
    "lat": 51.5,
    "lon": -0.1,
    "tz": "Europe/London"
  }' | jq .
```

### Transits

```bash
curl -s http://localhost:8000/charts/transits \
  -H "Content-Type: application/json" \
  -d '{
    "natal": {
      "date": "1815-12-10",
      "time": "13:00",
      "lat": 51.5,
      "lon": -0.1,
      "tz": "Europe/London"
    },
    "date": "2026-01-01",
    "time": "12:00"
  }' | jq .
```

## Zodiac modes

Pass `"mode"` in the request body:

| Value | Description |
|-------|-------------|
| `"realsky"` | IAU real-sky boundaries, 13 signs including Ophiuchus (default) |
| `"tropical"` | Standard 12-sign tropical wheel |
| `"vedic"` | Sidereal with Lahiri ayanamsa |

## Deployment

See the SAM template at [`../../template.yaml`](../../template.yaml) for deploying to AWS Lambda + API Gateway.

## Development

```bash
# Run tests
uv run --package hoshi-api pytest packages/hoshi-api/tests/

# Lint and format
uv run ruff check --fix . && uv run ruff format .
```
