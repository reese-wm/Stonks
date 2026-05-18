from app.schemas.market import ProjectionScenario, TickerResearch


def build_projection_scenario(
    research: TickerResearch,
    *,
    amount: float,
    mode: str,
    periods: int,
) -> ProjectionScenario:
    clean_amount = max(0.0, amount)
    clean_periods = max(1, min(periods, 3650))
    clean_mode = mode.lower().strip()
    warnings = [
        "Scenario only. This is not a prediction and not financial advice.",
        "Assumes the observed rate continues unchanged, which rarely happens in real markets.",
    ]

    if clean_mode not in {"daily", "hourly"}:
        clean_mode = "daily"
        warnings.append("Unknown mode supplied; defaulted to daily.")

    daily_rate = _observed_daily_rate(research)
    if daily_rate is None:
        daily_rate = 0.0
        warnings.append("No observed rate was available, so the scenario used 0%.")

    if clean_mode == "hourly":
        rate = daily_rate / 6.5
        source_label = "estimated hourly rate from latest daily move divided by 6.5 market hours"
    else:
        rate = daily_rate
        source_label = "latest observed daily change"

    projected_value = clean_amount * ((1 + rate / 100) ** clean_periods)
    gain_loss = projected_value - clean_amount
    gain_loss_percent = (gain_loss / clean_amount * 100) if clean_amount else 0.0

    if abs(rate) > 25:
        warnings.append("The observed rate is extremely large, so compounding can produce unrealistic outputs.")

    return ProjectionScenario(
        symbol=research.symbol,
        amount=round(clean_amount, 2),
        mode=clean_mode,
        periods=clean_periods,
        rate_percent_per_period=round(rate, 4),
        projected_value=round(projected_value, 2),
        projected_gain_loss=round(gain_loss, 2),
        projected_gain_loss_percent=round(gain_loss_percent, 2),
        source_label=source_label,
        explanation=(
            f"If {research.symbol} continued at {rate:.2f}% per {clean_mode} period for "
            f"{clean_periods} periods, ${clean_amount:,.2f} would become ${projected_value:,.2f}."
        ),
        warnings=warnings,
    )


def _observed_daily_rate(research: TickerResearch) -> float | None:
    if research.quote and research.quote.change_percent is not None:
        return research.quote.change_percent
    if len(research.historical) >= 2:
        previous = research.historical[-2].close
        latest = research.historical[-1].close
        if previous:
            return (latest - previous) / previous * 100
    return None
