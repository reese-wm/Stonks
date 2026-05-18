# API Contracts

## `GET /api/ticker/{symbol}`

Returns:

- `quote`
- `profile`
- `historical`
- `indicators`
- `news`
- `filings`
- `score`
- `provider_status`

All fields are normalized through Pydantic schemas in `app/schemas/market.py`.

## `GET /api/data-health`

Returns configured/missing provider status and cache policy.

## `GET /api/under-dollar-leaders`

Returns:

- `leaders`: top under-$1 screener results from FMP
- `projections`: ranked research-support projection cards
- `ai_summary`: optional OpenAI-generated summary when configured
- `warnings`: missing key, stale data, or provider issues

Also persists the result to the tracking database.

## `GET /api/under-dollar-leaders/latest`

Returns the latest stored under-$1 dashboard snapshot, or `null` if no snapshot exists.

## `POST /api/under-dollar-leaders/refresh`

Runs the under-$1 refresh job immediately and stores the result.

## `GET /api/tracking/under-dollar-history`

Returns recent stored snapshot summaries.

## `GET /api/tracking/projections`

Returns stored projection history. Optional query: `symbol=AAPL`.

## `GET /api/tracking/quotes/{symbol}`

Returns stored quote snapshots for the requested ticker.
