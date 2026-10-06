"""Shared figure styling for notebook exports."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "font.size": 10,
            "axes.grid": True,
            "grid.alpha": 0.25,
        }
    )


def save_figure(fig: plt.Figure, stem: Path, caption: str) -> None:
    """Save PNG, SVG, and PDF plus a one-line caption file."""
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".png"), dpi=150, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    stem.with_suffix(".caption.txt").write_text(caption.strip() + "\n", encoding="utf-8")
    plt.close(fig)
