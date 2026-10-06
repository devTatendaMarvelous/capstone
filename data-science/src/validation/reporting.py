"""Catalogue, data dictionary, and the acquisition report."""

from __future__ import annotations

from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from utils.config import data_dir, load_config
from validation.schema import REAL_COLUMNS


def write_source_catalogue(statuses: dict[str, dict]) -> pd.DataFrame:
    config = load_config()
    retrieved = datetime.now(timezone.utc).date().isoformat()
    rows = [
        ("NASA_POWER", "NASA POWER", "NASA Langley Research Center", "POWER Daily API", "https://power.larc.nasa.gov/api/temporal/daily/point", "meteorological", "Macheke study-area point", f"{config['years']['start']-1}-{config['years']['end']}", "about 0.5 degree", "daily", "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR", "API", "NASA POWER terms", "ingested"),
        ("CHIRPS_V3", "CHIRPS", "Climate Hazards Center / SERVIR ClimateSERV", "CHIRPS via ClimateSERV datatype 0", "https://climateserv.servirglobal.net/api/submitDataRequest/", "rainfall", "Macheke study-area approximation box", f"{config['years']['start']-1}-{config['years']['end']}", "0.05 degree", "daily", "rainfall", "API subset", "CHIRPS / ClimateSERV terms", "ingested"),
        ("SOILGRIDS_2", "SoilGrids 2.0", "ISRIC", "SoilGrids 2.0", "https://rest.isric.org/soilgrids/v2.0/properties/query", "soil", "one study-area point", "static prediction", "250 m", "static", "ph, nitrogen, soc, texture, cec, bulk density", "REST", "CC-BY", "ingested"),
        ("FAOSTAT", "FAOSTAT", "FAO", "Production Crops and Livestock Africa", "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip", "national agricultural statistics", "Zimbabwe", "1961-latest in file", "national", "annual", "maize yield, production, harvested area", "bulk CSV", "FAO terms", "ingested"),
        ("ZIMSTAT", "ZIMSTAT", "Zimbabwe National Statistics Agency", "public website review", "https://zimstat.co.zw/", "official statistics", "Zimbabwe", "", "", "", "", "HTML review", "site terms", statuses.get("zimstat", {}).get("ingestion_status", "reviewed_not_ingested")),
        ("AGRITEX", "Agritex / Ministry of Agriculture", "Ministry of Lands, Agriculture, Fisheries, Water and Rural Development", "public page review", "https://www.agriculture.gov.zw/", "extension statistics", "Zimbabwe", "", "", "", "", "HTML review", "site terms", statuses.get("agritex", {}).get("ingestion_status", "reviewed_not_ingested")),
    ]
    frame = pd.DataFrame(
        rows,
        columns=["source_id", "source_name", "provider", "dataset_name", "url", "data_type", "geographic_coverage", "temporal_coverage", "spatial_resolution", "temporal_resolution", "variables_used", "access_method", "license", "ingestion_status"],
    )
    overrides = {
        "nasa": "NASA_POWER",
        "chirps": "CHIRPS_V3",
        "soilgrids": "SOILGRIDS_2",
        "faostat": "FAOSTAT",
        "zimstat": "ZIMSTAT",
        "agritex": "AGRITEX",
    }
    for key, source_id in overrides.items():
        status = statuses.get(key, {}).get("ingestion_status")
        if status:
            frame.loc[frame["source_id"] == source_id, "ingestion_status"] = status
    frame["retrieved_at"] = retrieved
    frame["records_ingested"] = [
        statuses.get(key, {}).get("records", "")
        for key in ("nasa", "chirps", "soilgrids", "faostat", "zimstat", "agritex")
    ]
    frame["notes"] = [
        statuses.get(key, {}).get("notes", "")
        for key in ("nasa", "chirps", "soilgrids", "faostat", "zimstat", "agritex")
    ]
    path = data_dir() / "metadata" / "source_catalogue.csv"
    frame.to_csv(path, index=False)
    return frame


def write_dictionary(frame: pd.DataFrame) -> None:
    descriptions = {column: "" for column in REAL_COLUMNS}
    descriptions.update(
        {
            "yield_t_ha": "Maize yield in tonnes per hectare. Present only when copied from an agricultural statistics source.",
            "season_rainfall_mm": "Sum of daily rainfall over the configured maize season. CHIRPS when available, otherwise NASA POWER PRECTOTCORR.",
            "geographic_level": "Level of the climate and soil fields. grid_cell is not a farm.",
            "yield_geographic_level": "Level of yield_t_ha. national means FAOSTAT Zimbabwe, not a Macheke farm.",
            "synthetic_record": "False for every row written by this pipeline.",
            "soil_ph": "SoilGrids pH prediction at the selected depth, not a farm soil test.",
        }
    )
    columns = pd.DataFrame(
        {
            "column_name": REAL_COLUMNS,
            "description": [descriptions.get(column, "See the acquisition README.") for column in REAL_COLUMNS],
            "missing_allowed": True,
            "observed_non_null": [int(frame[column].notna().sum()) if column in frame.columns else 0 for column in REAL_COLUMNS],
        }
    )
    overview = pd.DataFrame(
        [
            {"item": "rows", "value": len(frame)},
            {"item": "columns", "value": frame.shape[1]},
            {"item": "synthetic_records", "value": int((frame["synthetic_record"] == True).sum()) if "synthetic_record" in frame.columns else 0},  # noqa: E712
            {"item": "yield_rows", "value": int(frame["yield_t_ha"].notna().sum()) if "yield_t_ha" in frame.columns else 0},
        ]
    )
    path = data_dir() / "metadata" / "data_dictionary.xlsx"
    with pd.ExcelWriter(path) as writer:
        overview.to_excel(writer, sheet_name="Dataset Overview", index=False)
        columns.to_excel(writer, sheet_name="Columns", index=False)
        pd.read_csv(data_dir() / "metadata" / "source_catalogue.csv").to_excel(writer, sheet_name="Sources", index=False)
        pd.DataFrame(
            [
                {"item": "yield", "rule": "kg/ha / 1000 = t/ha when FAOSTAT unit is kg/ha"},
                {"item": "rainfall day", "rule": "daily rainfall greater than the configured millimetre threshold"},
                {"item": "heat stress day", "rule": "daily maximum temperature at or above the configured Celsius threshold"},
                {"item": "soil texture", "rule": "SoilGrids g/kg divided by 10 to percent when the mapped value is still above 100 after d_factor"},
            ]
        ).to_excel(writer, sheet_name="Units", index=False)
        pd.DataFrame(
            [{"flag": flag, "meaning": meaning} for flag, meaning in (
                ("VALID", "No range or scale rule failed"),
                ("MISSING", "Yield is missing"),
                ("OUT_OF_RANGE", "A checked value is outside the documented physical range"),
                ("SUSPICIOUS", "National yield is attached to a grid-cell climate row"),
                ("DUPLICATE", "Same location, season, crop, and geographic levels"),
            )]
        ).to_excel(writer, sheet_name="Quality Rules", index=False)
        if (data_dir() / "metadata" / "provenance.csv").is_file():
            pd.read_csv(data_dir() / "metadata" / "provenance.csv").to_excel(writer, sheet_name="Provenance", index=False)


def write_acquisition_report(frame: pd.DataFrame) -> None:
    root = data_dir()
    figure_dir = root / "reports" / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    charts = []
    if not frame.empty and frame["year"].notna().any():
        counts = frame.groupby("year").size()
        _bar(counts.index.astype(int), counts.values, "Observations by harvest year", "Year", "Rows", figure_dir / "observations_by_year.png")
        charts.append("observations_by_year.png")
        if frame["yield_t_ha"].notna().any():
            _hist(frame["yield_t_ha"].dropna(), "National maize yield attached to the table", "t/ha", figure_dir / "yield_distribution.png")
            charts.append("yield_distribution.png")
        if frame["season_rainfall_mm"].notna().any():
            _line(frame["year"], frame["season_rainfall_mm"], "Season rainfall", "mm", figure_dir / "rainfall_by_season.png")
            charts.append("rainfall_by_season.png")
        missing = frame.isna().mean().sort_values(ascending=False).head(15)
        _bar(missing.index.astype(str), missing.values, "Share missing", "Column", "Fraction", figure_dir / "missing_values.png", horizontal=True)
        charts.append("missing_values.png")
    config = load_config()
    farm_yields = int(((frame.get("yield_geographic_level") == "farm") & frame["yield_t_ha"].notna()).sum()) if "yield_geographic_level" in frame else 0
    html = [
        "<html><head><meta charset='utf-8'><title>SmartCrop acquisition report</title></head><body>",
        "<h1>SmartCrop real-data acquisition</h1>",
        f"<p>Study area: Macheke, Mashonaland East, Zimbabwe. Boundary status: {config['study_area']['boundary_status']}.</p>",
        f"<p>{config['study_area']['boundary_note']}</p>",
        f"<p>Season assumption: {config['season']['assumption']}</p>",
        f"<p>Critical period assumption: {config['critical_growth_period']['assumption']}</p>",
        f"<p>Generated: {datetime.now(timezone.utc).isoformat()}</p>",
        f"<p>Rows: {len(frame)}. Synthetic rows: {int((frame['synthetic_record']==False).sum() and (frame['synthetic_record']==True).sum())}.</p>",
        f"<p>Yield values: {int(frame['yield_t_ha'].notna().sum())}. Farm-level yield values: {farm_yields}.</p>",
        "<p>FAOSTAT national maize yield is joined onto the Macheke grid for context. It is not a survey of Macheke farms. ZIMSTAT and Agritex did not contribute a public machine-readable Macheke table in this run.</p>",
        "<h2>Charts</h2>",
    ]
    for name in charts:
        html.append(f"<h3>{name}</h3><img src='figures/{name}' style='max-width:720px'/>")
    html.append("</body></html>")
    # Fix the synthetic count sentence properly below.
    synthetic = int(frame["synthetic_record"].fillna(False).astype(bool).sum()) if "synthetic_record" in frame else 0
    html[6] = f"<p>Rows: {len(frame)}. Synthetic rows: {synthetic}.</p>"
    (root / "reports" / "acquisition_report.html").write_text("\n".join(html), encoding="utf-8")
    summary = pd.DataFrame(
        [
            {"metric": "rows", "value": len(frame)},
            {"metric": "synthetic_records", "value": synthetic},
            {"metric": "yield_records", "value": int(frame["yield_t_ha"].notna().sum())},
            {"metric": "farm_level_yield_records", "value": farm_yields},
        ]
    )
    summary.to_csv(root / "reports" / "source_summary.csv", index=False)
    quality = frame["quality_flag"].value_counts(dropna=False).rename_axis("quality_flag").reset_index(name="rows")
    quality.to_html(root / "reports" / "data_quality_report.html", index=False)


def _bar(labels, values, title, xlabel, ylabel, path, horizontal=False):
    fig, ax = plt.subplots(figsize=(8, 4))
    if horizontal:
        ax.barh(list(labels), list(values), color="#14613f")
    else:
        ax.bar(list(labels), list(values), color="#14613f")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _hist(values, title, xlabel, path):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(values, bins=10, color="#3d6b54")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def _line(x, y, title, ylabel, path):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(x, y, color="#14613f")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
