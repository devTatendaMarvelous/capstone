"""Attach the single SoilGrids point to season rows. This is not a farm join."""

from __future__ import annotations

import pandas as pd


def soil_record(points: pd.DataFrame, depth: str) -> dict:
    if points.empty:
        return {}
    selected = points.loc[points["depth"] == depth]
    record = {}
    for _, row in selected.iterrows():
        record[row["column"]] = row["value"]
    if selected.empty:
        return record
    record["soil_latitude"] = float(selected["latitude"].iloc[0])
    record["soil_longitude"] = float(selected["longitude"].iloc[0])
    record["soil_depth"] = depth
    return record


def attach_soil(seasons: pd.DataFrame, points: pd.DataFrame, depth: str) -> pd.DataFrame:
    record = soil_record(points, depth)
    frame = seasons.copy()
    for key, value in record.items():
        frame[key] = value
    return frame
