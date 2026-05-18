# Scoring Model

The MVP classification is evidence-based, not a trading signal.

```text
composite_score =
  0.30 * technical_score +
  0.25 * fundamental_score +
  0.20 * news_score +
  0.15 * valuation_score +
  0.10 * momentum_score -
  risk_penalty
```

Fundamental and valuation scores currently default to neutral placeholders until statement and ratio ingestion is connected.

## Labels

- Strong watchlist candidate
- Bullish setup, confirm risk
- Neutral / mixed evidence
- Weak setup
- Avoid for now
- High-risk speculative setup
- Needs more data
