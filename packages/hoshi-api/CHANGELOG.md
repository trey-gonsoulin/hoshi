# CHANGELOG

<!-- version list -->

## v1.9.0 (2026-08-07)

### Features

- **transits**: Per-pass ingress/exact/egress for retrograde multi-hit transits
  ([#35](https://github.com/trey-gonsoulin/hoshi/pull/35),
  [`61de631`](https://github.com/trey-gonsoulin/hoshi/commit/61de631a5ea1e6bda321ed9eced9b0b3bf1fd98f))


## v1.8.0 (2026-08-07)

### Bug Fixes

- **api**: Add tier and sensitivity args to transits GraphQL resolver
  ([`60fe8da`](https://github.com/trey-gonsoulin/hoshi/commit/60fe8da052cd5b3f2ac11133ae29be9b33a6342d))

### Features

- Add dignity reference info across CLI, API, and UI
  ([`10ca54f`](https://github.com/trey-gonsoulin/hoshi/commit/10ca54f6b4039b84570a089b7eae2d87b5e5e109))

- **api**: Add birth range search and sign distribution endpoints
  ([`66f33c5`](https://github.com/trey-gonsoulin/hoshi/commit/66f33c592da09a67354f4aeec82536668540e0d6))

- **api**: Add POST /charts/cycles endpoint for planetary return dates
  ([`280c91a`](https://github.com/trey-gonsoulin/hoshi/commit/280c91a61c14a1b3a59c23eaf555bac1c90946a4))

- **api**: Composite-transits and composite-forecast endpoints
  ([`49ed388`](https://github.com/trey-gonsoulin/hoshi/commit/49ed38826a34ec54c658926fee585ca7d419f72d))

- **chart**: Composite (midpoint) chart from two natal charts
  ([`c6cbb71`](https://github.com/trey-gonsoulin/hoshi/commit/c6cbb715f0ae1fe6ab00628265d076308a181bc9))

- **hoshi-api**: Add GraphQL endpoint via Strawberry at /graphql
  ([`28a38e2`](https://github.com/trey-gonsoulin/hoshi/commit/28a38e2de40e6d5a48332be071cfbe0156c0d6d1))

- **transits**: Add ingress/exact/egress window dates to transit aspects
  ([`6f597cc`](https://github.com/trey-gonsoulin/hoshi/commit/6f597ccf4f25d8f8a038f353cc7976cf56baf0c4))

- **transits**: Add planet speed tier classification and filtering
  ([#37](https://github.com/trey-gonsoulin/hoshi/pull/37),
  [`13d73db`](https://github.com/trey-gonsoulin/hoshi/commit/13d73dbd0e843324428121fde7fd5dd01d6ddb92))

- **transits**: Add retrograde pass count and current-pass tracking
  ([`777a289`](https://github.com/trey-gonsoulin/hoshi/commit/777a2899d4125702b26ba166b2bafa97220ad746))

- **transits**: Date-range transit-to-natal forecast
  ([#38](https://github.com/trey-gonsoulin/hoshi/pull/38),
  [`8d7b7e7`](https://github.com/trey-gonsoulin/hoshi/commit/8d7b7e7dd3cb767124b0d94944c145debfb2f2d2))

- **transits**: Natal point sensitivity weighting
  ([#39](https://github.com/trey-gonsoulin/hoshi/pull/39),
  [`8764cfe`](https://github.com/trey-gonsoulin/hoshi/commit/8764cfe926373e80c26270f5715882f62ae5c4d4))

- **ui**: Add cycles page showing next planetary return dates
  ([`8967ba9`](https://github.com/trey-gonsoulin/hoshi/commit/8967ba94299536e7b7c5665cc94949e1caa2234c))

- **ui**: Composite chart page from two saved charts
  ([`5e607c2`](https://github.com/trey-gonsoulin/hoshi/commit/5e607c2613b744696517bbe3c737bf4130197263))

- **ui**: Transits tier/sensitivity filters, ingress/egress/pass display, and forecast page
  ([`e8a74eb`](https://github.com/trey-gonsoulin/hoshi/commit/e8a74eb35e8d637b200994f97deeed0ecf45275a))


## v1.7.0 (2026-07-05)

### Features

- **sky**: Add sky event timeline and landing page
  ([`4697e4d`](https://github.com/trey-gonsoulin/hoshi/commit/4697e4defb68251a0129ce66cbc11414c357bd15))


## v1.6.1 (2026-07-05)

### Bug Fixes

- **api**: Fix Dockerfile multiline python -c breaking Docker parser
  ([`342fe4c`](https://github.com/trey-gonsoulin/hoshi/commit/342fe4cbc4d175e1d07218b874eb476fbc863573))


## v1.6.0 (2026-07-05)

### Features

- **ephemeris**: Add Ceres and Eris as Horizons-backed bodies
  ([`3574041`](https://github.com/trey-gonsoulin/hoshi/commit/3574041fd9955671bf9da19f06c9fdf735f5cb53))

- **ephemeris**: Pre-seed Ceres and Eris for deployed Lambda environments
  ([`1b0574c`](https://github.com/trey-gonsoulin/hoshi/commit/1b0574c49a47e3faa812f196b1bc20116bc913bb))

### Testing

- **api**: Assert symbol and sign_symbol fields on body entries
  ([`2e72212`](https://github.com/trey-gonsoulin/hoshi/commit/2e72212b267519c756545a852a552e8b84fabe8a))


## v1.5.2 (2026-07-01)

### Bug Fixes

- **api**: Copy LICENSE into Docker build context
  ([`f94d9c2`](https://github.com/trey-gonsoulin/hoshi/commit/f94d9c22b2e93a34052779c3d91b2c99bf3d1f26))


## v1.5.1 (2026-07-01)

### Bug Fixes

- **api**: Read version from package metadata instead of hardcoded string
  ([`b2c5dc6`](https://github.com/trey-gonsoulin/hoshi/commit/b2c5dc6341ca863f9a968e333656e2f7dbd2860f))


## v1.5.0 (2026-06-30)

### Features

- Publish package to PyPI as hoshi-astro
  ([`f1b11be`](https://github.com/trey-gonsoulin/hoshi/commit/f1b11be1b6b61b19df98a65b02b702fd2deaec97))


## v1.4.0 (2026-06-30)

### Features

- **api**: Add MCP Streamable HTTP transport at /mcp
  ([`bbfd72c`](https://github.com/trey-gonsoulin/hoshi/commit/bbfd72c666eb03dea2683614f410132be03ba5ec))

- **ephemeris**: Bundle daily Chiron seed cache in Lambda image
  ([`432ba35`](https://github.com/trey-gonsoulin/hoshi/commit/432ba35b9b9fd9c5aab03addea5a65c943a21764))


## v1.3.0 (2026-06-30)

### Features

- **api**: Add FastMCP integration at /mcp/ for LLM integration
  ([`d16207f`](https://github.com/trey-gonsoulin/hoshi/commit/d16207fdafaa0dfa5c77f46758862854f8f3a4a5))


## v1.2.0 (2026-06-28)

### Features

- **api**: Build and deploy to AWS Lambda (SAM)
  ([`4f94f04`](https://github.com/trey-gonsoulin/hoshi/commit/4f94f0433bc6c1ffbc84e295c47ebf6f949af771))

- **info**: Add ecliptic cusp and size to signs info command
  ([`5ae3a2a`](https://github.com/trey-gonsoulin/hoshi/commit/5ae3a2aa02f6d0add227995f820057248d5eff09))


## v1.1.0 (2026-06-27)

### Features

- **api**: Add configuration required for SAM deployment on AWS Lambda
  ([`df15e6e`](https://github.com/trey-gonsoulin/hoshi/commit/df15e6ea498b906c5ea51dcd028cb7eccdc3baa9))


## v1.0.0 (2026-06-24)

- Initial Release
