from statistics import mean, pstdev

from app.schemas.market import IndicatorSnapshot, OHLCV


def calculate_indicators(prices: list[OHLCV]) -> IndicatorSnapshot:
    if not prices:
        return IndicatorSnapshot()

    closes = [item.close for item in prices]
    highs = [item.high for item in prices]
    lows = [item.low for item in prices]
    volumes = [item.volume for item in prices]
    latest_close = closes[-1]
    low_52 = min(lows[-252:]) if len(lows) >= 2 else None
    high_52 = max(highs[-252:]) if len(highs) >= 2 else None

    ema_12_series = _ema_series(closes, 12)
    ema_26_series = _ema_series(closes, 26)
    macd_series = [a - b for a, b in zip(ema_12_series, ema_26_series, strict=False)]
    signal_series = _ema_series(macd_series, 9) if macd_series else []

    middle = _sma(closes, 20)
    deviation = pstdev(closes[-20:]) if len(closes) >= 20 else None

    return IndicatorSnapshot(
        sma_20=_sma(closes, 20),
        sma_50=_sma(closes, 50),
        sma_200=_sma(closes, 200),
        ema_12=ema_12_series[-1] if ema_12_series else None,
        ema_26=ema_26_series[-1] if ema_26_series else None,
        rsi_14=_rsi(closes, 14),
        macd=macd_series[-1] if macd_series else None,
        macd_signal=signal_series[-1] if signal_series else None,
        macd_histogram=(macd_series[-1] - signal_series[-1]) if macd_series and signal_series else None,
        atr_14=_atr(prices, 14),
        bollinger_upper=(middle + 2 * deviation) if middle is not None and deviation is not None else None,
        bollinger_middle=middle,
        bollinger_lower=(middle - 2 * deviation) if middle is not None and deviation is not None else None,
        relative_volume=_relative_volume(volumes),
        high_52_week_distance=((latest_close - high_52) / high_52 * 100) if high_52 else None,
        low_52_week_distance=((latest_close - low_52) / low_52 * 100) if low_52 else None,
    )


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return round(mean(values[-period:]), 4)


def _ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    multiplier = 2 / (period + 1)
    ema = values[0]
    result = [ema]
    for value in values[1:]:
        ema = (value - ema) * multiplier + ema
        result.append(ema)
    return [round(item, 4) for item in result]


def _rsi(values: list[float], period: int) -> float | None:
    if len(values) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(values[-period - 1 : -1], values[-period:], strict=False):
        change = current - previous
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))
    avg_gain = mean(gains)
    avg_loss = mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _atr(prices: list[OHLCV], period: int) -> float | None:
    if len(prices) <= period:
        return None
    ranges: list[float] = []
    for previous, current in zip(prices[-period - 1 : -1], prices[-period:], strict=False):
        ranges.append(max(current.high - current.low, abs(current.high - previous.close), abs(current.low - previous.close)))
    return round(mean(ranges), 4)


def _relative_volume(volumes: list[int]) -> float | None:
    if len(volumes) < 21:
        return None
    avg = mean(volumes[-21:-1])
    if avg == 0:
        return None
    return round(volumes[-1] / avg, 2)
