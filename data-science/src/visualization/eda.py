"""Exploratory figures for the clean maize dataset.

Each figure has a title, axis labels, units, and a caption file beside it.
Plots use pairwise deletion when a point is missing. They do not impute.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from data.schema import TARGET_COLUMN
from features.engineering import MODEL_FEATURES, add_engineered_features
from visualization.figures import apply_style, save_figure

SYNTHETIC_NOTE = "Synthetic development data, not Macheke measurements."


def _hist(series: pd.Series, title: str, xlabel: str, stem: Path, caption: str) -> None:
    apply_style()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    values = series.dropna()
    ax.hist(values, bins=25, color="#2F6B4F", edgecolor="white")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Farm-season observations")
    fig.tight_layout()
    save_figure(fig, stem, caption)


def _scatter(df: pd.DataFrame, x: str, y: str, xlabel: str, ylabel: str, title: str, stem: Path, caption: str) -> None:
    apply_style()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    plot = df[[x, y]].dropna()
    ax.scatter(plot[x], plot[y], alpha=0.45, s=18, c="#3E6B4F", edgecolors="none")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    save_figure(fig, stem, caption)


def build_eda_figures(df: pd.DataFrame, figures_dir: Path) -> pd.DataFrame:
    """Write the EDA figure set and return the correlation table used for the top five."""
    figures_dir.mkdir(parents=True, exist_ok=True)
    featured = add_engineered_features(df)
    numeric = [column for column in MODEL_FEATURES if column in featured.columns]
    correlations = (
        featured[numeric + [TARGET_COLUMN]]
        .corr(numeric_only=True)[TARGET_COLUMN]
        .drop(TARGET_COLUMN)
        .sort_values(key=lambda s: s.abs(), ascending=False)
    )

    _hist(
        df[TARGET_COLUMN],
        "Distribution of maize yield",
        "Yield (t/ha)",
        figures_dir / "yield_distribution",
        f"Histogram of synthetic yield_t_ha. {SYNTHETIC_NOTE}",
    )
    _hist(
        df["rainfall_mm"],
        "Distribution of seasonal rainfall",
        "Seasonal rainfall (mm)",
        figures_dir / "rainfall_distribution",
        f"Histogram of synthetic seasonal rainfall. {SYNTHETIC_NOTE}",
    )
    apply_style()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for column, label in (
        ("avg_temperature_c", "Average"),
        ("max_temperature_c", "Maximum"),
        ("min_temperature_c", "Minimum"),
    ):
        ax.hist(df[column].dropna(), bins=20, alpha=0.45, label=label)
    ax.set_title("Distribution of growing-season temperatures")
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("Farm-season observations")
    ax.legend(title="Series")
    fig.tight_layout()
    save_figure(fig, figures_dir / "temperature_distribution", f"Overlaid temperature histograms. {SYNTHETIC_NOTE}")

    apply_style()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    order = sorted(df["season"].dropna().unique())
    sns.boxplot(data=df, x="season", y=TARGET_COLUMN, order=order, color="#C4D7C8", ax=ax)
    ax.set_title("Maize yield by synthetic season")
    ax.set_xlabel("Season label (not a historical weather series)")
    ax.set_ylabel("Yield (t/ha)")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    save_figure(fig, figures_dir / "yield_by_season", f"Yield by synthetic season label. {SYNTHETIC_NOTE}")

    apply_style()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.boxplot(data=df, x="ward", y=TARGET_COLUMN, color="#E4D2B6", ax=ax)
    ax.set_title("Maize yield by placeholder ward")
    ax.set_xlabel("Ward code (synthetic placeholder, not an official ward)")
    ax.set_ylabel("Yield (t/ha)")
    fig.tight_layout()
    save_figure(fig, figures_dir / "yield_by_ward", f"Yield by synthetic ward code. {SYNTHETIC_NOTE}")

    _scatter(
        df,
        "rainfall_mm",
        TARGET_COLUMN,
        "Seasonal rainfall (mm)",
        "Yield (t/ha)",
        "Seasonal rainfall and maize yield",
        figures_dir / "rainfall_vs_yield",
        f"Scatter of synthetic rainfall against yield. Association is partly built into the generator. {SYNTHETIC_NOTE}",
    )
    _scatter(
        df,
        "avg_temperature_c",
        TARGET_COLUMN,
        "Average temperature (°C)",
        "Yield (t/ha)",
        "Average temperature and maize yield",
        figures_dir / "temperature_vs_yield",
        f"Scatter of synthetic average temperature against yield. {SYNTHETIC_NOTE}",
    )
    _scatter(
        df,
        "fertilizer_kg_ha",
        TARGET_COLUMN,
        "Fertilizer product (kg/ha)",
        "Yield (t/ha)",
        "Fertilizer rate and maize yield",
        figures_dir / "fertilizer_vs_yield",
        f"Scatter of synthetic fertilizer product against yield. {SYNTHETIC_NOTE}",
    )

    apply_style()
    fig, axes = plt.subplots(1, 3, figsize=(11, 4))
    for ax, column, label in zip(
        axes,
        ["soil_ph", "soil_nitrogen", "soil_organic_carbon"],
        ["Soil pH", "Soil nitrogen (%)", "Soil organic carbon (%)"],
    ):
        plot = df[[column, TARGET_COLUMN]].dropna()
        ax.scatter(plot[column], plot[TARGET_COLUMN], alpha=0.4, s=14, c="#6B4A32")
        ax.set_xlabel(label)
        ax.set_ylabel("Yield (t/ha)")
    fig.suptitle("Soil variables and maize yield")
    fig.tight_layout()
    save_figure(fig, figures_dir / "soil_vs_yield", f"Soil pH, nitrogen, and organic carbon against yield. {SYNTHETIC_NOTE}")

    apply_style()
    corr = featured[numeric + [TARGET_COLUMN]].corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(corr, ax=ax, cmap="BrBG", center=0, annot=True, fmt=".2f", annot_kws={"size": 7})
    ax.set_title("Correlation matrix of model features and yield")
    fig.tight_layout()
    save_figure(
        fig,
        figures_dir / "correlation_matrix",
        f"Pearson correlations. These are associations in the synthetic file, not causal effects. {SYNTHETIC_NOTE}",
    )

    apply_style()
    missing = (df.isna().mean() * 100).sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(missing.index, missing.values, color="#8C4A32")
    ax.set_title("Missing values after cleaning")
    ax.set_xlabel("Missing observations (%)")
    ax.set_ylabel("Column")
    fig.tight_layout()
    save_figure(fig, figures_dir / "missing_values", f"Missingness remaining after duplicate removal and invalid-value blanking. {SYNTHETIC_NOTE}")

    apply_style()
    box_columns = ["yield_t_ha", "rainfall_mm", "fertilizer_kg_ha", "soil_ph"]
    fig, axes = plt.subplots(1, len(box_columns), figsize=(11, 4))
    for ax, column in zip(axes, box_columns):
        ax.boxplot(df[column].dropna(), vert=True)
        ax.set_title(column)
        ax.set_ylabel(column)
    fig.suptitle("Boxplots of yield, rainfall, fertilizer, and soil pH")
    fig.tight_layout()
    save_figure(fig, figures_dir / "boxplots_key_variables", f"Boxplots after cleaning. {SYNTHETIC_NOTE}")

    apply_style()
    hist_columns = ["yield_t_ha", "rainfall_mm", "avg_temperature_c", "fertilizer_kg_ha"]
    fig, axes = plt.subplots(2, 2, figsize=(9, 7))
    for ax, column in zip(axes.ravel(), hist_columns):
        ax.hist(df[column].dropna(), bins=20, color="#4C7C8A", edgecolor="white")
        ax.set_title(column)
        ax.set_xlabel(column)
        ax.set_ylabel("Observations")
    fig.suptitle("Histograms of the main analysis variables")
    fig.tight_layout()
    save_figure(fig, figures_dir / "histograms_key_variables", f"Histograms of the main variables. {SYNTHETIC_NOTE}")

    top = correlations.head(5)
    apply_style()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = ["#2F6B4F" if value >= 0 else "#8C4A32" for value in top.values]
    ax.barh(top.index[::-1], top.values[::-1], color=colors[::-1])
    ax.set_title("Five strongest linear associations with yield")
    ax.set_xlabel("Pearson correlation with yield_t_ha")
    ax.set_ylabel("Feature")
    fig.tight_layout()
    save_figure(
        fig,
        figures_dir / "top_features",
        "Absolute Pearson correlation with yield. This is association, not causation, and the generator built some of the association in.",
    )
    return correlations.rename("correlation_with_yield").reset_index().rename(columns={"index": "feature"})
