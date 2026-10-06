"""Season windows for a maize crop that can cross the calendar year."""

from __future__ import annotations

import pandas as pd


def months_in_window(start_month: int, end_month: int) -> list[int]:
    months = []
    month = start_month
    while True:
        months.append(month)
        if month == end_month:
            break
        month = 1 if month == 12 else month + 1
        if len(months) > 12:
            raise ValueError("Season window did not close.")
    return months


def harvest_year(dates: pd.Series, start_month: int, end_month: int) -> pd.Series:
    """Label each daily date with the harvest year of its maize season.

    For a November-March season, November and December belong to the next
    calendar year's harvest. Months outside the window are missing.
    """
    stamp = pd.to_datetime(dates)
    window = set(months_in_window(start_month, end_month))
    month = stamp.dt.month
    year = stamp.dt.year
    inside = month.isin(window)
    if start_month > end_month:
        harvest = year.where(month <= end_month, year + 1)
    else:
        harvest = year
    return harvest.where(inside)


def season_label(harvest: int) -> str:
    return f"{harvest - 1}/{harvest}"
