"""Write the single real-data SmartCrop notebook.

The notebook reads the FAOSTAT, NASA POWER, CHIRPS, and SoilGrids downloads.
It does not read the archived synthetic generator or its CSV files.
"""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "smartcrop_real_master.ipynb"


def build() -> Path:
    cells = [
        new_markdown_cell(
            """# SmartCrop real-data pipeline

One notebook for the SmartCrop maize yield methodology. It replaces the separate real-data notebooks (`01_real_data_acquisition` through `05_real_model_metrics`) and it does **not** use the archived synthetic files in `data/synthetic/`.

The study area is the Macheke grid in Mashonaland East, Zimbabwe. The target is FAOSTAT national maize yield in tonnes per hectare. Weather and soil describe the study-area grid. They are not farm measurements.

Raw files were retrieved on **5 October 2026** by `scripts/acquire_all.py`. This notebook reads those saved responses, checks them, builds the seasonal table, and fits the models. It does not invent yields.

## Source URLs

| Source | URL |
| --- | --- |
| NASA POWER daily point API | https://power.larc.nasa.gov/api/temporal/daily/point |
| NASA POWER documentation | https://power.larc.nasa.gov/ |
| CHIRPS via SERVIR ClimateSERV | https://climateserv.servirglobal.net/api/submitDataRequest/ |
| CHIRPS product page | https://data.chc.ucsb.edu/products/CHIRPS-2.0/ |
| ISRIC SoilGrids 2.0 query | https://rest.isric.org/soilgrids/v2.0/properties/query |
| SoilGrids documentation | https://rest.isric.org/soilgrids/v2.0/docs |
| FAOSTAT Africa crops and livestock bulk file | https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip |
| FAOSTAT crops and livestock products | https://www.fao.org/faostat/en/#data/QCL |
| ZIMSTAT (reviewed, not ingested) | https://zimstat.co.zw/ |
| Ministry of Agriculture (reviewed, not ingested) | https://www.agriculture.gov.zw/ |

## References

Climate Hazards Center. (n.d.). *CHIRPS: Climate Hazards Group InfraRed Precipitation with Station data* [Data set]. University of California, Santa Barbara. https://data.chc.ucsb.edu/products/CHIRPS-2.0/

Food and Agriculture Organization of the United Nations. (n.d.). *FAOSTAT: Crops and livestock products* [Data set]. https://www.fao.org/faostat/en/#data/QCL

Funk, C., Peterson, P., Landsfeld, M., Pedreros, D., Verdin, J., Shukla, S., Husak, G., Rowland, J., Harrison, L., Hoell, A., & Michaelsen, J. (2015). The climate hazards infrared precipitation with stations: A new environmental record for monitoring extremes. *Scientific Data, 2*, Article 150066. https://doi.org/10.1038/sdata.2015.66

ISRIC – World Soil Information. (n.d.). *SoilGrids REST API* [Data set]. https://rest.isric.org/soilgrids/v2.0/docs

National Aeronautics and Space Administration. (n.d.). *Prediction of Worldwide Energy Resources (POWER)* [Data set]. https://power.larc.nasa.gov/

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, É. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, 12*, 2825–2830.

Poggio, L., de Sousa, L. M., Batjes, N. H., Heuvelink, G. B. M., Kempen, B., Ribeiro, E., & Rossiter, D. (2021). SoilGrids 2.0: Producing soil information for the globe with quantified spatial uncertainty. *SOIL, 7*(1), 217–240. https://doi.org/10.5194/soil-7-217-2021

SERVIR. (n.d.). *ClimateSERV*. https://climateserv.servirglobal.net/

Wirth, R., & Hipp, J. (2000). CRISP-DM: Towards a standard process model for data mining. In *Proceedings of the 4th International Conference on the Practical Application of Knowledge Discovery and Data Mining* (pp. 29–39). Practical Application Company.
"""
        ),
        new_markdown_cell(
            """## 1. Setup

The next cell locates the data-science folder, loads the saved downloads, and stops if a synthetic row is present. Figures are written to `reports/chapter3/figures/`."""
        ),
        new_code_cell(
            r'''import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path.cwd()
if not (ROOT / "src").is_dir():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

from models.real_training import _candidates, annual_masks, usable_features
from models.training import RANDOM_SEED

DATA = ROOT / "data"
FIG = ROOT / "reports" / "chapter3" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
SYNTHETIC = DATA / "synthetic" / "macheke_maize_synthetic.csv"
assert SYNTHETIC.is_file(), "The archived synthetic file should remain on disk, but it is not an input."

sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams.update({
    "figure.dpi": 140,
    "savefig.dpi": 160,
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.titleweight": "semibold",
})
NAVY = "#1B4F72"
GREEN = "#196F3D"
EARTH = "#B9770E"


def save_table(frame, path, title):
    display = frame.copy()
    fig_h = 0.55 + 0.42 * (len(display) + 1)
    fig, ax = plt.subplots(figsize=(11.2, max(1.8, fig_h)))
    ax.axis("off")
    ax.set_title(title, loc="left", fontsize=12, pad=10, color="#1B4F72")
    table = ax.table(
        cellText=display.values,
        colLabels=list(display.columns),
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.35)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#D5D8DC")
        if row == 0:
            cell.set_facecolor("#1B4F72")
            cell.set_text_props(color="white", weight="bold")
        elif row % 2 == 0:
            cell.set_facecolor("#F4F6F7")
        else:
            cell.set_facecolor("white")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


frame = pd.read_csv(DATA / "processed" / "capstone_dataset_real.csv")
assert int(frame["synthetic_record"].fillna(False).astype(bool).sum()) == 0
assert "SYNTHETIC" not in set(frame["data_source_type"].astype(str))
print("Modelling rows", len(frame), "years", int(frame.year.min()), "to", int(frame.year.max()))
print("Synthetic rows in the modelling table:", int(frame["synthetic_record"].sum()))
'''
        ),
        new_markdown_cell(
            """## 2. Sources and acquisition

Each ingested source keeps its URL, retrieval time, and row count in `data/metadata/source_catalogue.csv`. ZIMSTAT and the Ministry of Agriculture page were opened and saved. Neither exposed a machine-readable Macheke maize table, so both stay at zero records."""
        ),
        new_code_cell(
            r'''catalogue = pd.read_csv(DATA / "metadata" / "source_catalogue.csv")
provenance = pd.read_csv(DATA / "metadata" / "provenance.csv")
view = catalogue[["source_id", "provider", "ingestion_status", "records_ingested", "url"]].copy()
view["records_ingested"] = view["records_ingested"].astype(int)
print(view.drop(columns="url").to_string(index=False))
print("\nURLs")
for row in view.itertuples(index=False):
    print(f"{row.source_id}: {row.url}")

counts = catalogue.loc[catalogue["ingestion_status"] == "ingested", ["source_id", "records_ingested"]]
fig, ax = plt.subplots(figsize=(8.2, 4.2))
ax.barh(counts["source_id"], counts["records_ingested"], color=NAVY)
ax.set_xlabel("Records retained from the 5 October 2026 download")
ax.set_title("Downloaded records by source")
for index, value in enumerate(counts["records_ingested"]):
    ax.text(value + 80, index, f"{int(value):,}", va="center", fontsize=9)
fig.tight_layout()
fig.savefig(FIG / "fig_3_1_source_counts.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
save_table(
    view.assign(url=view["url"].str.slice(0, 62)),
    FIG / "fig_3_1_source_log.png",
    "Notebook output: source log (URLs truncated in the figure; full URLs are printed above)",
)
print("NASA request example:")
print((DATA / "raw" / "nasa_power" / "power_daily_2000.request.txt").read_text().strip())
'''
        ),
        new_markdown_cell(
            """## 3. Quality, cleaning, and the seasonal join

Daily NASA POWER and CHIRPS values are summed or averaged over the November–March maize season. The season label is the harvest year, so November 2019 belongs to the 2020 season. January–February rainfall is kept as the critical window. A rainfall day is a day above 1 mm. A heat-stress day has a maximum temperature of at least 33 °C. NASA POWER fill values of −999 are already stored as missing.

The modelling table keeps harvest years 2000–2023. Seasonal rainfall comes from CHIRPS. SoilGrids is the same 0–5 cm prediction on every year. FAOSTAT national maize yield (kg/ha divided by 1,000) is joined on the harvest year. Farm fertiliser, seed, and planting date columns stay empty because no public table supplied them."""
        ),
        new_code_cell(
            r'''nasa = pd.read_csv(DATA / "processed" / "nasa_power_seasonal.csv")
chirps = pd.read_csv(DATA / "processed" / "chirps_seasonal.csv")
faostat = pd.read_csv(DATA / "processed" / "faostat_zimbabwe_maize.csv")
soil = pd.read_csv(DATA / "processed" / "soilgrids_points.csv")
agreed = nasa.merge(chirps, on="year")
rain_corr = float(agreed["nasa_season_rainfall_mm"].corr(agreed["chirps_season_rainfall_mm"]))
window = faostat.loc[faostat["year"].between(2000, 2023)].copy()

checks = pd.DataFrame([
    ["Modelling seasons", len(frame)],
    ["Duplicate harvest years", int(frame["year"].duplicated().sum())],
    ["Missing yield", int(frame["yield_t_ha"].isna().sum())],
    ["Missing climate predictors", int(frame[["season_rainfall_mm", "avg_temperature_c", "heat_stress_days"]].isna().sum().sum())],
    ["Negative seasonal rainfall", int((frame["season_rainfall_mm"] < 0).sum())],
    ["Minimum temperature above maximum", int((frame["min_temperature_c"] > frame["max_temperature_c"]).sum())],
    ["NASA daily rows", int(len(pd.read_csv(DATA / "interim" / "nasa_power_daily.csv")))],
    ["CHIRPS daily rows", int(len(pd.read_csv(DATA / "interim" / "chirps_daily.csv")))],
    ["SoilGrids rows", int(len(soil))],
    ["FAOSTAT national years", int(len(faostat))],
    ["NASA–CHIRPS seasonal rainfall correlation", round(rain_corr, 3)],
    ["Quality flag", frame["quality_flag"].mode().iloc[0]],
])
checks.columns = ["Check", "Result"]
print(checks.to_string(index=False))
print("FAOSTAT flags, 2000-2023")
print(window["faostat_flag"].value_counts().to_string())
print(window.loc[window["faostat_flag"] != "A", ["year", "faostat_flag", "yield_t_ha"]].to_string(index=False))
save_table(checks, FIG / "fig_3_2_quality_report.png", "Notebook output: quality checks on the real-data table")

fig, ax = plt.subplots(figsize=(6.4, 5.4))
ax.scatter(agreed["chirps_season_rainfall_mm"], agreed["nasa_season_rainfall_mm"], color=NAVY, s=36)
limit = max(agreed["chirps_season_rainfall_mm"].max(), agreed["nasa_season_rainfall_mm"].max()) * 1.05
ax.plot([0, limit], [0, limit], color="#7F8C8D", linestyle="--", linewidth=1)
ax.set_xlabel("CHIRPS seasonal rainfall (mm)")
ax.set_ylabel("NASA POWER seasonal rainfall (mm)")
ax.set_title(f"Seasonal rainfall agreement (r = {rain_corr:.3f}, n = {len(agreed)})")
fig.tight_layout()
fig.savefig(FIG / "fig_3_2_rainfall_agreement.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

management = ["fertilizer_kg_ha", "basal_fertilizer_kg_ha", "top_dressing_kg_ha", "seed_variety", "planting_day_of_year", "irrigation_used"]
print("Share missing in farm-management columns:")
print(frame[management].isna().mean().round(3).to_string())
'''
        ),
        new_markdown_cell(
            """## 4. Features, collinearity, and the year split

Soil properties do not change across the 24 seasons, so they are reported and then left out of the model matrix. Temperature range is the difference between the seasonal mean maximum and the seasonal mean minimum, so those three columns are linearly dependent. The tree models can still split on them. A linear model cannot separate them.

The most recent four harvest years are the test set. The four years before that are the validation set used to choose the algorithm. Earlier years are the training set. The test years are not used to choose the model or the tree settings."""
        ),
        new_code_cell(
            r'''features = usable_features(frame)
print("Model features:", features)
soil_cols = ["soil_ph", "soil_nitrogen_g_kg", "soil_organic_carbon_g_kg", "soil_clay_pct", "soil_sand_pct", "soil_silt_pct", "soil_cec_cmol_kg", "soil_bulk_density_g_cm3"]
print("Distinct soil values:")
print(frame[soil_cols].nunique().to_string())

vif_rows = []
x = frame[features].astype(float)
for column in features:
    others = [name for name in features if name != column]
    fitted = LinearRegression().fit(x[others], x[column])
    score = float(fitted.score(x[others], x[column]))
    vif = float("inf") if score > 0.999999 else 1.0 / (1.0 - score)
    vif_rows.append({"feature": column, "r2_on_others": round(score, 3), "vif": None if np.isinf(vif) else round(vif, 2)})
vif_table = pd.DataFrame(vif_rows)
print(vif_table.to_string(index=False))

masks = annual_masks(frame)
print("Train", masks["train_years"][0], "-", masks["train_years"][-1], "n =", len(masks["train_years"]))
print("Validation", masks["validation_years"])
print("Test", masks["test_years"])

dictionary = pd.DataFrame([
    ["year", "Harvest year used as the join key", "year", "Calendar rule on the November-March season"],
    ["season", "Season label, for example 2019/2020", "label", "Derived from the harvest year"],
    ["yield_t_ha", "Zimbabwe maize yield, the target", "t/ha", "FAOSTAT, kg/ha divided by 1000"],
    ["production_tonnes", "National maize production", "tonnes", "FAOSTAT"],
    ["season_rainfall_mm", "November-March rainfall total", "mm", "CHIRPS, NASA POWER only if CHIRPS is missing"],
    ["critical_period_rainfall_mm", "January-February rainfall", "mm", "CHIRPS"],
    ["rainfall_days", "Days with rainfall above 1 mm", "days", "CHIRPS"],
    ["rainfall_cv", "Coefficient of variation of daily rainfall", "ratio", "CHIRPS"],
    ["avg_temperature_c", "Mean of daily mean temperature", "°C", "NASA POWER T2M"],
    ["max_temperature_c", "Mean of daily maximum temperature", "°C", "NASA POWER T2M_MAX"],
    ["min_temperature_c", "Mean of daily minimum temperature", "°C", "NASA POWER T2M_MIN"],
    ["temperature_range_c", "max_temperature_c minus min_temperature_c", "°C", "Engineered from NASA POWER"],
    ["heat_stress_days", "Days with maximum temperature of at least 33 °C", "days", "NASA POWER"],
    ["soil_ph", "Topsoil pH, 0-5 cm, constant across years", "pH", "SoilGrids 2.0"],
    ["soil_nitrogen_g_kg", "Topsoil nitrogen, constant across years", "g/kg", "SoilGrids 2.0"],
    ["soil_organic_carbon_g_kg", "Topsoil organic carbon, constant across years", "g/kg", "SoilGrids 2.0"],
])
dictionary.columns = ["variable", "meaning", "unit", "source"]
dictionary.to_csv(ROOT / "reports" / "chapter3" / "data_dictionary.csv", index=False)
dictionary
'''
        ),
        new_markdown_cell(
            """## 5. Descriptive analysis

Yield, rainfall, and temperature are summarised for the 24 modelling seasons. Pearson and Spearman correlations describe linear and rank association with national yield. A Shapiro–Wilk test checks the yield distribution. A Mann–Whitney test compares yield in the driest quarter of seasons with the other seasons. A Kendall test looks for a monotonic yield trend. These tests describe the table. They do not identify causes."""
        ),
        new_code_cell(
            r'''numeric = ["yield_t_ha", "season_rainfall_mm", "critical_period_rainfall_mm", "rainfall_days", "rainfall_cv", "avg_temperature_c", "max_temperature_c", "min_temperature_c", "temperature_range_c", "heat_stress_days"]
description = frame[numeric].agg(["count", "mean", "median", "std", "min", "max", "skew"]).T.round(3)
description.to_csv(ROOT / "reports" / "chapter3" / "descriptive_statistics.csv")
print(description.to_string())

associations = []
for column in features:
    pearson = float(frame[column].corr(frame["yield_t_ha"], method="pearson"))
    spearman = float(frame[column].corr(frame["yield_t_ha"], method="spearman"))
    associations.append({"feature": column, "pearson": round(pearson, 3), "spearman": round(spearman, 3)})
association_table = pd.DataFrame(associations).sort_values("pearson", key=lambda s: s.abs(), ascending=False)
print(association_table.to_string(index=False))

shapiro_w, shapiro_p = stats.shapiro(frame["yield_t_ha"])
quartile = float(frame["season_rainfall_mm"].quantile(0.25))
low_mask = frame["season_rainfall_mm"] <= quartile
mann_u, mann_p = stats.mannwhitneyu(frame.loc[low_mask, "yield_t_ha"], frame.loc[~low_mask, "yield_t_ha"], alternative="two-sided")
kendall_tau, kendall_p = stats.kendalltau(frame["year"], frame["yield_t_ha"])
print("Shapiro-Wilk yield W", round(float(shapiro_w), 4), "p", round(float(shapiro_p), 4))
print("Lowest rainfall quartile", round(quartile, 1), "mm; seasons", int(low_mask.sum()))
print("Mean yield in drier seasons", round(float(frame.loc[low_mask, "yield_t_ha"].mean()), 3))
print("Mean yield in other seasons", round(float(frame.loc[~low_mask, "yield_t_ha"].mean()), 3))
print("Mann-Whitney U", round(float(mann_u), 2), "p", round(float(mann_p), 4))
print("Kendall tau", round(float(kendall_tau), 3), "p", round(float(kendall_p), 4))

fig, axes = plt.subplots(2, 1, figsize=(9.2, 6.4), sharex=True)
axes[0].plot(frame["year"], frame["yield_t_ha"], color=GREEN, marker="o", linewidth=1.6)
axes[0].set_ylabel("National maize yield (t/ha)")
axes[0].set_title("FAOSTAT Zimbabwe maize yield by harvest year")
axes[1].bar(frame["year"], frame["season_rainfall_mm"], color=EARTH, width=0.7)
axes[1].set_ylabel("CHIRPS seasonal rainfall (mm)")
axes[1].set_xlabel("Harvest year")
axes[1].set_title("Macheke study-area rainfall, November to March")
fig.tight_layout()
fig.savefig(FIG / "fig_3_3_yield_and_rainfall.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

corr = frame[features + ["yield_t_ha"]].corr()
fig, ax = plt.subplots(figsize=(8.6, 7.0))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, ax=ax, annot_kws={"size": 8})
ax.set_title("Pearson correlations among climate features and national yield")
fig.tight_layout()
fig.savefig(FIG / "fig_3_4_correlation_matrix.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
'''
        ),
        new_markdown_cell(
            """## 6. Models, tuning, and the held-out seasons

Four regressors are compared: ordinary least squares, a depth-limited decision tree, a random forest, and gradient boosting. Each pipeline median-imputes inside the training fold. The linear model is also standardised. A training-mean baseline and a linear time trend are scored on the same years.

Algorithm choice uses validation years 2016–2019 only. An expanding window then scores one-year-ahead predictions for 2008–2019, pooled into one MAE, RMSE, and R². Those folds stop before 2020. A small random-forest grid (200 or 100 trees, depth 2–4, minimum leaf 2 or 3) is scored on the validation years. The saved settings stay in place when the grid does not improve validation RMSE by a meaningful amount. The test years 2020–2023 are scored once."""
        ),
        new_code_cell(
            r'''def regression_scores(y_true, y_pred):
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(mean_squared_error(y_true, y_pred) ** 0.5), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


y = frame["yield_t_ha"]
x = frame[features]
train, valid, test = masks["train"], masks["validation"], masks["test"]
candidates = _candidates(RANDOM_SEED)
rows = []
fitted = {}
for name, model in candidates.items():
    model.fit(x.loc[train], y.loc[train])
    scores = regression_scores(y.loc[valid], model.predict(x.loc[valid]))
    rows.append({"model_name": name, **{f"validation_{key}": value for key, value in scores.items()}})
    fitted[name] = model
comparison = pd.DataFrame(rows).sort_values(["validation_r2", "validation_rmse"], ascending=[False, True]).reset_index(drop=True)
chosen_name = str(comparison.loc[0, "model_name"])
chosen = fitted[chosen_name]

mean_baseline = {
    "validation": regression_scores(y.loc[valid], np.full(int(valid.sum()), float(y.loc[train].mean()))),
    "test": regression_scores(y.loc[test], np.full(int(test.sum()), float(y.loc[train].mean()))),
}
trend = LinearRegression().fit(frame.loc[train, ["year"]], y.loc[train])
trend_baseline = {
    "validation": regression_scores(y.loc[valid], trend.predict(frame.loc[valid, ["year"]])),
    "test": regression_scores(y.loc[test], trend.predict(frame.loc[test, ["year"]])),
}

development = frame.loc[frame["year"] <= 2019].sort_values("year").reset_index(drop=True)
pooled = []
for name, model in _candidates(RANDOM_SEED).items():
    predictions = []
    actual = []
    for end in range(8, len(development)):
        fold = clone(model)
        past = development.iloc[:end]
        future = development.iloc[end:end + 1]
        fold.fit(past[features], past["yield_t_ha"])
        predictions.append(float(fold.predict(future[features])[0]))
        actual.append(float(future["yield_t_ha"].iloc[0]))
    pooled.append({"model_name": name, "one_step_years": "2008-2019", "n_forecasts": len(actual), **regression_scores(actual, predictions)})
expanding = pd.DataFrame(pooled).sort_values("rmse").reset_index(drop=True)

grid_rows = []
for trees, depth, leaf in [(100, 2, 2), (100, 3, 2), (100, 4, 2), (100, 2, 3), (100, 3, 3), (100, 4, 3), (200, 2, 2), (200, 3, 2), (200, 4, 2), (200, 2, 3), (200, 3, 3), (200, 4, 3)]:
    forest = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestRegressor(n_estimators=trees, max_depth=depth, min_samples_leaf=leaf, random_state=RANDOM_SEED, n_jobs=1)),
    ])
    forest.fit(x.loc[train], y.loc[train])
    scores = regression_scores(y.loc[valid], forest.predict(x.loc[valid]))
    grid_rows.append({"n_estimators": trees, "max_depth": depth, "min_samples_leaf": leaf, **{f"validation_{key}": value for key, value in scores.items()}})
grid = pd.DataFrame(grid_rows).sort_values("validation_rmse").reset_index(drop=True)
preset = grid.loc[(grid["n_estimators"] == 200) & (grid["max_depth"] == 4) & (grid["min_samples_leaf"] == 2)].iloc[0]

test_pred = chosen.predict(x.loc[test])
test_scores = regression_scores(y.loc[test], test_pred)
importance = permutation_importance(chosen, x.loc[valid], y.loc[valid], n_repeats=10, random_state=RANDOM_SEED, scoring="r2")
importance_table = pd.DataFrame({"feature": features, "importance_mean": importance.importances_mean}).sort_values("importance_mean", ascending=False)
importance_table.insert(0, "rank", range(1, len(importance_table) + 1))

print("Validation comparison")
print(comparison.to_string(index=False))
print("Expanding-window pooled scores")
print(expanding.to_string(index=False))
print("Random forest grid, best five by validation RMSE")
print(grid.head(5).to_string(index=False))
print("Saved settings validation RMSE", float(preset["validation_rmse"]))
print("Chosen", chosen_name, "test", test_scores)
print("Training-mean baseline", mean_baseline)
print("Trend baseline", trend_baseline)
print(importance_table.round(4).to_string(index=False))

comparison.to_csv(ROOT / "reports" / "chapter3" / "model_comparison.csv", index=False)
grid.to_csv(ROOT / "reports" / "chapter3" / "random_forest_grid.csv", index=False)
save_table(comparison.round(4), FIG / "fig_3_5_model_comparison.png", "Notebook output: validation scores used to choose the algorithm")

fig, ax = plt.subplots(figsize=(8.0, 4.4))
order = comparison.sort_values("validation_rmse")
ax.barh(order["model_name"], order["validation_rmse"], color=NAVY)
ax.set_xlabel("Validation RMSE (t/ha), harvest years 2016-2019")
ax.set_title("Algorithm comparison on the validation seasons")
fig.tight_layout()
fig.savefig(FIG / "fig_3_5_validation_rmse.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

test_frame = frame.loc[test, ["year", "yield_t_ha"]].copy()
test_frame["predicted_t_ha"] = test_pred
fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.4))
axes[0].scatter(test_frame["yield_t_ha"], test_frame["predicted_t_ha"], color=NAVY, s=50, zorder=3)
for row in test_frame.itertuples(index=False):
    axes[0].annotate(str(int(row.year)), (row.yield_t_ha, row.predicted_t_ha), textcoords="offset points", xytext=(5, 4), fontsize=8)
low = min(test_frame["yield_t_ha"].min(), test_frame["predicted_t_ha"].min()) - 0.1
high = max(test_frame["yield_t_ha"].max(), test_frame["predicted_t_ha"].max()) + 0.1
axes[0].plot([low, high], [low, high], color="#7F8C8D", linestyle="--")
axes[0].set_xlabel("FAOSTAT yield (t/ha)")
axes[0].set_ylabel("Predicted yield (t/ha)")
axes[0].set_title("Test seasons")
axes[1].plot(frame["year"], frame["yield_t_ha"], color=GREEN, marker="o", label="FAOSTAT")
axes[1].scatter(test_frame["year"], test_frame["predicted_t_ha"], color=NAVY, s=40, label="Test prediction", zorder=3)
axes[1].set_ylabel("Yield (t/ha)")
axes[1].set_xlabel("Harvest year")
axes[1].set_title("Held-out predictions")
axes[1].legend(frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(FIG / "fig_3_6_test_predictions.png", bbox_inches="tight", facecolor="white")
plt.close(fig)

summary = {
    "n_seasons": int(len(frame)),
    "year_start": int(frame.year.min()),
    "year_end": int(frame.year.max()),
    "retrieval_date": "5 October 2026",
    "rain_corr": round(rain_corr, 3),
    "rain_corr_n": int(len(agreed)),
    "nasa_daily": int(len(pd.read_csv(DATA / "interim" / "nasa_power_daily.csv"))),
    "chirps_daily": int(len(pd.read_csv(DATA / "interim" / "chirps_daily.csv"))),
    "soil_rows": int(len(soil)),
    "faostat_years": int(len(faostat)),
    "faostat_year_min": int(faostat.year.min()),
    "faostat_year_max": int(faostat.year.max()),
    "faostat_flags": {str(k): int(v) for k, v in window["faostat_flag"].value_counts().items()},
    "faostat_x_years": [int(year) for year in window.loc[window["faostat_flag"] != "A", "year"]],
    "yield_mean": round(float(y.mean()), 3),
    "yield_median": round(float(y.median()), 3),
    "yield_std": round(float(y.std()), 3),
    "yield_min": round(float(y.min()), 3),
    "yield_max": round(float(y.max()), 3),
    "yield_min_year": int(frame.loc[y.idxmin(), "year"]),
    "yield_max_year": int(frame.loc[y.idxmax(), "year"]),
    "rain_mean": round(float(frame.season_rainfall_mm.mean()), 1),
    "rain_median": round(float(frame.season_rainfall_mm.median()), 1),
    "rain_std": round(float(frame.season_rainfall_mm.std()), 1),
    "rain_min": round(float(frame.season_rainfall_mm.min()), 1),
    "rain_max": round(float(frame.season_rainfall_mm.max()), 1),
    "rain_min_year": int(frame.loc[frame.season_rainfall_mm.idxmin(), "year"]),
    "rain_max_year": int(frame.loc[frame.season_rainfall_mm.idxmax(), "year"]),
    "temp_mean": round(float(frame.avg_temperature_c.mean()), 2),
    "temp_min": round(float(frame.avg_temperature_c.min()), 2),
    "temp_max": round(float(frame.avg_temperature_c.max()), 2),
    "heat_mean": round(float(frame.heat_stress_days.mean()), 1),
    "heat_max": int(frame.heat_stress_days.max()),
    "heat_max_year": int(frame.loc[frame.heat_stress_days.idxmax(), "year"]),
    "soil": {column: float(frame[column].iloc[0]) for column in soil_cols},
    "shapiro_w": round(float(shapiro_w), 3),
    "shapiro_p": round(float(shapiro_p), 3),
    "rain_q25": round(quartile, 1),
    "n_dry": int(low_mask.sum()),
    "yield_dry": round(float(frame.loc[low_mask, "yield_t_ha"].mean()), 3),
    "yield_other": round(float(frame.loc[~low_mask, "yield_t_ha"].mean()), 3),
    "mann_u": round(float(mann_u), 1),
    "mann_p": round(float(mann_p), 3),
    "kendall_tau": round(float(kendall_tau), 3),
    "kendall_p": round(float(kendall_p), 3),
    "train_years": [int(year) for year in masks["train_years"]],
    "validation_years": [int(year) for year in masks["validation_years"]],
    "test_years": [int(year) for year in masks["test_years"]],
    "chosen_model": chosen_name,
    "comparison": comparison.to_dict(orient="records"),
    "expanding": expanding.to_dict(orient="records"),
    "grid_best": grid.iloc[0].to_dict(),
    "grid_preset_rmse": float(preset["validation_rmse"]),
    "test_scores": test_scores,
    "mean_baseline": mean_baseline,
    "trend_baseline": trend_baseline,
    "test_predictions": test_frame.round(4).to_dict(orient="records"),
    "importance": importance_table.round(4).to_dict(orient="records"),
    "vif": vif_table.to_dict(orient="records"),
    "associations": association_table.to_dict(orient="records"),
    "description": description.reset_index().rename(columns={"index": "variable"}).to_dict(orient="records"),
    "management_missing": {column: float(frame[column].isna().mean()) for column in management},
    "versions": {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scikit-learn": __import__("sklearn").__version__,
        "matplotlib": __import__("matplotlib").__version__,
        "scipy": __import__("scipy").__version__,
    },
    "random_seed": int(RANDOM_SEED),
    "r2_target": 0.8,
    "r2_target_met": bool(test_scores["r2"] >= 0.8),
}
(ROOT / "reports" / "chapter3" / "chapter3_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("Summary written")
'''
        ),
    ]
    book = new_notebook(cells=cells)
    book.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    book.metadata["language_info"] = {"name": "python", "pygments_lexer": "ipython3"}
    nbformat.write(book, OUT)
    print(OUT)
    return OUT


if __name__ == "__main__":
    build()
