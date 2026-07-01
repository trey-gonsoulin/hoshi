FROM public.ecr.aws/lambda/python:3.12 AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

# Copy the full workspace so uv can resolve workspace dependencies
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY hoshi/ ./hoshi/
COPY packages/hoshi-api/ ./packages/hoshi-api/

# Sync the hoshi-api package into a local venv.
# UV_INDEX_URL ensures only public PyPI is used (overrides any private index
# configured in packages/hoshi-api/pyproject.toml for local dev).
RUN UV_INDEX_URL=https://pypi.org/simple \
    uv sync --package hoshi-api --no-dev --no-editable

# ---- Chiron ephemeris pre-fetch stage ----
# Fetches daily Chiron positions from JPL Horizons for the given date range and
# saves them as a date-keyed JSON seed. This stage can be built once, pushed as
# its own image, and reused as a cache source — it only rebuilds when CHIRON_START
# or CHIRON_END changes.
FROM builder AS chiron-cache

ARG CHIRON_START=1900-01-01
ARG CHIRON_END=2050-12-31

RUN PYTHONPATH=/build/.venv/lib/python3.12/site-packages \
    python -c "from pathlib import Path; from hoshi.ephemeris import prefetch_chiron_range; prefetch_chiron_range('${CHIRON_START}', '${CHIRON_END}', Path('/chiron-seed/chiron_seed.json'))"

# ---- Final Lambda image ----
FROM public.ecr.aws/lambda/python:3.12

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY hoshi/ ./hoshi/
COPY packages/hoshi-api/ ./packages/hoshi-api/

RUN UV_INDEX_URL=https://pypi.org/simple \
    uv sync --package hoshi-api --no-dev --no-editable

# Copy installed packages into the Lambda task root
RUN cp -r /build/.venv/lib/python3.12/site-packages/. "${LAMBDA_TASK_ROOT}/"

# Bundle the Skyfield ephemeris so cold starts don't hit the network
RUN PYTHONPATH="${LAMBDA_TASK_ROOT}" python \
      -c "from skyfield.api import Loader; Loader('${LAMBDA_TASK_ROOT}')('de421.bsp')"

# Bundle the pre-fetched Chiron seed cache
COPY --from=chiron-cache /chiron-seed/chiron_seed.json "${LAMBDA_TASK_ROOT}/chiron_seed.json"

CMD ["hoshi_api.lambda_handler.handler"]
