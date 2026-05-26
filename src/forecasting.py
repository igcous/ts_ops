import math
import numpy as np
import pandas as pd


def exponential_smoothing(series: pd.Series, alpha: float = 0.3) -> pd.Series:
    result = [series.iloc[0]]
    for val in series.iloc[1:]:
        result.append(alpha * val + (1 - alpha) * result[-1])
    return pd.Series(result, index=series.index)


def forecast_case_volume(volume_series: pd.Series, periods: int = 28) -> pd.DataFrame:
    if len(volume_series) < 2:
        raise ValueError("Need at least 2 data points to forecast.")

    smoothed = exponential_smoothing(volume_series)

    # Linear trend from last 14 days
    tail = smoothed.iloc[-min(14, len(smoothed)):]
    x = np.arange(len(tail))
    slope, intercept = np.polyfit(x, tail.values, 1)

    last_date = volume_series.index[-1]
    forecast_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1), periods=periods, freq="D"
    )

    last_val = smoothed.iloc[-1]
    forecast_values = [last_val + slope * (i + 1) for i in range(periods)]
    forecast_values = [max(0, v) for v in forecast_values]

    # Confidence band: ±1.5 std of residuals
    residuals = volume_series.values - smoothed.values
    std = float(np.std(residuals))
    margin = 1.5 * std

    historical = pd.DataFrame({
        "date": volume_series.index,
        "forecast_volume": smoothed.values,
        "lower_bound": smoothed.values - margin,
        "upper_bound": smoothed.values + margin,
        "is_forecast": False,
    })

    future = pd.DataFrame({
        "date": forecast_dates,
        "forecast_volume": forecast_values,
        "lower_bound": [max(0, v - margin) for v in forecast_values],
        "upper_bound": [v + margin for v in forecast_values],
        "is_forecast": True,
    })

    return pd.concat([historical, future], ignore_index=True)


def forecast_agent_demand(
    forecast_df: pd.DataFrame,
    current_agents: int,
    cases_per_agent_per_day: float = 18.0,
) -> pd.DataFrame:
    future = forecast_df[forecast_df["is_forecast"]].copy()
    future["required_agents"] = (future["forecast_volume"] / cases_per_agent_per_day).apply(math.ceil)
    future["current_agents"] = current_agents
    future["staffing_gap"] = future["required_agents"] - current_agents
    future["is_understaffed"] = future["staffing_gap"] > 0
    return future[["date", "forecast_volume", "required_agents", "current_agents", "staffing_gap", "is_understaffed"]]
