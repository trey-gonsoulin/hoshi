FROM public.ecr.aws/lambda/python:3.12

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

# Copy the full workspace so uv can resolve workspace dependencies
COPY pyproject.toml uv.lock ./
COPY hoshi/ ./hoshi/
COPY packages/hoshi-api/ ./packages/hoshi-api/

# Sync the hoshi-api package into a local venv.
# UV_INDEX_URL ensures only public PyPI is used (overrides any private index
# configured in packages/hoshi-api/pyproject.toml for local dev).
RUN UV_INDEX_URL=https://pypi.org/simple \
    uv sync --package hoshi-api --no-dev --no-editable

# Copy installed packages into the Lambda task root
RUN cp -r /build/.venv/lib/python3.12/site-packages/. "${LAMBDA_TASK_ROOT}/"

# Bundle the Skyfield ephemeris so cold starts don't hit the network
RUN PYTHONPATH="${LAMBDA_TASK_ROOT}" python \
      -c "from skyfield.api import Loader; Loader('${LAMBDA_TASK_ROOT}')('de421.bsp')"

CMD ["hoshi_api.lambda_handler.handler"]
