# Open-Source Quant Resources Used

These projects are used as architecture and methodology references, not bundled runtime dependencies.

## OpenBB Platform

Use as the model for provider abstraction, multi-source data pipelines, and AI-ready research workflows.

- Repo: https://github.com/OpenBB-finance/OpenBB
- Role in Stonks: data coverage scoring and provider-status framing.

## Backtrader

Use as the model for strategy prototyping, analyzers, and backtest-first thinking.

- Site: https://www.backtrader.com/
- Role in Stonks: backtest checklist and baseline strategy workflow.

## Zipline

Use as the model for factor research and event-driven strategy framing.

- Repo: https://github.com/quantopian/zipline
- Role in Stonks: factor/event readiness language.

## FinRL

Use as the model for reinforcement-learning readiness: state design, reward design, environments, and validation.

- Repo: https://github.com/AI4Finance-Foundation/FinRL
- Role in Stonks: ML readiness scoring and AI workflow guardrails.

## QuantConnect LEAN

Use as the model for production-grade trading engine design, risk controls, and live-trading separation.

- Repo: https://github.com/QuantConnect/Lean
- Role in Stonks: execution risk controls and production-readiness notes.

## Implementation Notes

The current app does not execute trades or run real backtests. The `Quant Intelligence` endpoint compiles existing backend-fetched quote, OHLCV, indicator, news, SEC, and optional TipRanks data into a research workflow report. OpenAI can polish the report when `OPENAI_API_KEY` is available; otherwise the rules engine returns a deterministic report.
