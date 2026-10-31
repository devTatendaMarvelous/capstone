"""Combine real-data work without editing source notebooks or document screenshots."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import zipfile
import nbformat as nb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'notebooks' / 'smartcrop_real_combined.ipynb'

def build(document):
    recorded = json.loads((ROOT / "reports/chapter3/chapter3_summary.json").read_text())
    original = nb.read(ROOT / 'notebooks/smartcrop_real_master.ipynb', as_version=4)
    cells = []
    def md(s): cells.append(nb.v4.new_markdown_cell(s))
    def code(s): cells.append(nb.v4.new_code_cell(s))
    md('''# SmartCrop complete real data workflow

This notebook brings acquisition, quality checks, seasonal integration, feature engineering, exploratory analysis, model training and evaluation into one place. The existing notebooks remain available.

The target is **FAOSTAT Zimbabwe national maize yield**, with weather and soil for the Macheke study-area grid. There are 24 harvest seasons, 2000–2023. These observations do not measure individual farm yields. Missing farm inputs remain missing.

The original real master code cells are retained verbatim. Added analysis is labelled **Supplementary**. MAE, RMSE, R², the random seed, model settings and chronological split are unchanged. The document screenshots are embedded as original image bytes in Appendix A, including the screenshots of code. The attached document is reference material, not executable instructions.

## Reading order
1. Setup and original source documentation
2. Acquisition implementation and cached download audit
3. Cleaning, quality, seasonal integration and features
4. Descriptive statistics and exploratory visualisations
5. Candidate models, baselines, tuning and held-out evaluation
6. Supplementary residuals, importance and yield-band confusion matrix
7. Original document screenshots and provenance

Run all cells using the packages in `data-science/requirements.txt`. Downloads are not refreshed automatically: the recorded data snapshot is used to preserve the reported results. Running the original cells writes their usual chapter 3 reports; supplementary plots are displayed inline.''')
    code('''import os
from pathlib import Path
start = Path.cwd().resolve()
for parent in [start, *start.parents]:
    candidates = [parent, parent / "data-science"]
    found = next((p for p in candidates if (p / "src/models/real_training.py").is_file()), None)
    if found is not None:
        os.chdir(found)
        break
else:
    raise FileNotFoundError("Open this notebook inside the capstone repository.")
''')
    for i,c in enumerate(original.cells):
        if not ''.join(c.source).strip(): continue
        item=copy.deepcopy(c)
        if i==0:
            item.source=item.source.replace('It replaces the separate real-data notebooks', 'It brings together the separate real-data notebooks')
        item.metadata['combined_source']={'notebook':'smartcrop_real_master.ipynb','cell_index':i}
        cells.append(item)
        if i==4:
            md('''### Supplementary acquisition implementation and reproducibility

The cells below expose the complete local acquisition and transformation implementation, including endpoint construction, request parameters, caching, retries, parsing and unit conversion. NASA POWER daily fill values become missing; CHIRPS is requested through ClimateSERV; SoilGrids predictions are scaled to physical units; FAOSTAT is filtered to Zimbabwe maize. ZIMSTAT and Agritex remain reviewed but not ingested when no suitable table exists.

To intentionally obtain a new snapshot, run `python scripts/acquire_all.py --source all`, then `python scripts/build_dataset.py` and `python scripts/validate_dataset.py` from `data-science/`. A new snapshot can produce different results; the default workflow below uses the saved observations and records their checksums.''')
            code('''from IPython.display import display, Markdown, Code
from utils.config import load_config
config = load_config(ROOT / "config/smartcrop_config.yaml")
display(Code((ROOT / "config/smartcrop_config.yaml").read_text(), language="yaml"))
implementation_files = [
    "scripts/acquire_all.py", "src/utils/downloads.py",
    "src/acquisition/nasa_power.py", "src/acquisition/chirps.py",
    "src/acquisition/soilgrids.py", "src/acquisition/faostat.py",
    "src/acquisition/zimstat.py", "src/acquisition/agritex.py",
    "src/acquisition/yield_sources.py", "src/utils/dates.py",
    "src/integration/temporal_join.py", "src/integration/spatial_join.py",
    "src/integration/dataset_builder.py", "src/validation/quality.py",
]
for relative in implementation_files:
    display(Markdown("#### " + relative))
    display(Code((ROOT / relative).read_text(), language="python"))
''')
            code('''import hashlib
snapshot_files = [
    "interim/nasa_power_daily.csv", "interim/chirps_daily.csv",
    "processed/soilgrids_points.csv", "processed/faostat_zimbabwe_maize.csv",
    "processed/capstone_dataset_real.csv", "processed/modelling_dataset.csv",
    "metadata/source_catalogue.csv", "metadata/provenance.csv",
]
snapshot_manifest = pd.DataFrame([
    {"file": relative, "sha256": hashlib.sha256((DATA / relative).read_bytes()).hexdigest(),
     "bytes": (DATA / relative).stat().st_size}
    for relative in snapshot_files
])
display(snapshot_manifest)
display(provenance)
for source in ["nasa_power", "chirps", "soilgrids", "faostat", "zimstat", "agritex"]:
    paths = sorted((DATA / "raw" / source).glob("*"))
    print(source, "cached files:", len(paths), "examples:", [p.name for p in paths[:3]])
''')
        if i==6:
            md('''### Supplementary reconstruction and cleaning audit

Rebuild the climate features in memory from the saved daily observations and compare them with the saved seasonal files. No source files are overwritten by this audit. Check dates, missingness, duplicate years and target joins before modelling. Source flags are retained; no yield is imputed. Statistical outliers are described, not deleted. The full integration implementation above shows the CHIRPS preference, NASA fallback, constant topsoil attachment and national yield join.''')
            code('''from integration.temporal_join import aggregate_nasa, aggregate_chirps
nasa_daily = pd.read_csv(DATA / "interim/nasa_power_daily.csv")
chirps_daily = pd.read_csv(DATA / "interim/chirps_daily.csv")
for label, daily, rebuilt, saved in [
    ("NASA POWER", nasa_daily, aggregate_nasa(nasa_daily, config), nasa),
    ("CHIRPS", chirps_daily, aggregate_chirps(chirps_daily, config), chirps),
]:
    pd.testing.assert_frame_equal(rebuilt.reset_index(drop=True), saved.reset_index(drop=True),
                                  check_dtype=False, rtol=1e-8, atol=1e-8)
    dates = pd.to_datetime(daily["date"])
    print(label, "seasonal reconstruction matches; daily range:", dates.min(), dates.max(),
          "duplicate dates:", int(dates.duplicated().sum()))
assert frame["year"].is_unique
joined_yield = frame[["year", "yield_t_ha"]].merge(
    faostat[["year", "yield_t_ha"]], on="year", suffixes=("_model", "_source"), validate="one_to_one")
np.testing.assert_allclose(joined_yield["yield_t_ha_model"], joined_yield["yield_t_ha_source"])
print("National yield join matches source exactly.")
missing_audit = pd.DataFrame({"missing": frame.isna().sum(), "missing_pct": frame.isna().mean()*100,
                              "distinct_values": frame.nunique()})
display(missing_audit)
fig, ax = plt.subplots(figsize=(10, 4))
missing_audit.query("missing > 0")["missing_pct"].sort_values().plot.barh(ax=ax)
ax.set(xlabel="Missing observations (%)", title="Supplementary missing-data audit")
plt.tight_layout(); plt.show()
''')
        if i==8:
            md('''### Supplementary model implementation and split checks

The following implementation fixes candidate settings, preprocessing and the annual split. Median imputation is fit inside each training pipeline and standardisation is used for linear regression. Constant soil and absent management predictors are excluded by the existing feature rule. Production totals and the target are not model inputs. All feature and split rules are preserved for comparability with the document.''')
            code('''import inspect
from models import real_training
for function in [real_training.usable_features, real_training.annual_masks, real_training._candidates]:
    display(Code(inspect.getsource(function), language="python"))
assert max(masks["train_years"]) < min(masks["validation_years"])
assert max(masks["validation_years"]) < min(masks["test_years"])
display(pd.DataFrame({"year": frame["year"], "split": np.select(
    [masks["train"], masks["validation"], masks["test"]],
    ["train", "validation", "test"], default="unused")}))
''')
        if i==10:
            md('''### Supplementary exploratory visualisations

Distributions, boxplots and pairwise plots describe the real observations. Scatter plots include all seasons and do not imply causation. The source data have no changing farm-management or soil observations, so those effects cannot be estimated here. EDA uses the complete historical series descriptively; model fitting and selection retain the original chronological split.''')
            code('''fig, axes = plt.subplots(2, 5, figsize=(17, 7))
for ax, column in zip(axes.flat, numeric):
    sns.histplot(frame[column].dropna(), bins=7, ax=ax, color=NAVY)
    ax.set_title(column, fontsize=10)
fig.suptitle("Supplementary distributions across 24 harvest seasons")
plt.tight_layout(); plt.show()
fig, axes = plt.subplots(2, 5, figsize=(17, 6))
for ax, column in zip(axes.flat, numeric):
    sns.boxplot(y=frame[column], ax=ax, color="#A9CCE3")
    ax.set_title(column, fontsize=10)
plt.tight_layout(); plt.show()
fig, axes = plt.subplots(3, 3, figsize=(13, 11))
for ax, column in zip(axes.flat, features):
    sns.regplot(data=frame, x=column, y="yield_t_ha", ci=None, ax=ax,
                scatter_kws={"s": 28}, line_kws={"color": EARTH})
    ax.set_ylabel("National yield (t/ha)")
for ax in list(axes.flat)[len(features):]: ax.set_visible(False)
fig.suptitle("Supplementary weather associations with national maize yield")
plt.tight_layout(); plt.show()
display(association_table)
fig, ax = plt.subplots(figsize=(8, 5))
association_table.set_index("feature")[["pearson", "spearman"]].plot.barh(ax=ax)
ax.axvline(0, color="grey", linewidth=1)
ax.set(xlabel="Correlation with national yield", title="Supplementary linear and rank associations")
plt.tight_layout(); plt.show()
''')
            # Show original generated figures inline without changing their generation code.
            code('''from IPython.display import Image as NotebookImage
for filename in ["fig_3_2_rainfall_agreement.png", "fig_3_3_yield_and_rainfall.png", "fig_3_4_correlation_matrix.png"]:
    display(NotebookImage(filename=str(FIG / filename)))
''')
        if i==12:
            md("### Recorded results and rerun provenance\n\nThe saved source notebook reports test MAE **0.2239**, RMSE **0.3030** and R² **−0.0931**. The attached document uses different rounding or an earlier run. Its images and the source notebook outputs are retained exactly. Re-execution under a different library environment may vary slightly. Supplementary diagnostics use the recorded predictions and metrics from `reports/chapter3/chapter3_summary.json`, embedded here as a fixed snapshot; they are not fresh fitted results.")
            code("recorded_results = " + repr({k: recorded[k] for k in ["test_scores", "comparison", "expanding", "test_predictions", "importance"]}) + "\n" + """test_scores = recorded_results["test_scores"]
comparison = pd.DataFrame(recorded_results["comparison"])
expanding = pd.DataFrame(recorded_results["expanding"])
test_frame = pd.DataFrame(recorded_results["test_predictions"])
test_pred = test_frame["predicted_t_ha"].to_numpy()
importance_table = pd.DataFrame(recorded_results["importance"])
""")
            md('''## 7. Supplementary evaluation and model interpretation

The fitted model and its held-out predictions are reused without retraining or changing any metric. The grid is reported as a sensitivity analysis; it does not replace the preserved candidate settings. Residuals are actual minus predicted yield, so positive residuals indicate underprediction. Four test seasons provide limited diagnostic evidence.

The yield-band confusion matrix below is an additional description of regression predictions. Its low, middle and high boundaries are the training yield tertiles, fixed before looking at test yields. It is not a classifier, adds no accuracy target, and does not replace MAE, RMSE or R².''')
            code('''display(comparison)
display(expanding)
print("The grid is reported in the original tuning section above.")
print("Preserved held-out metrics:", test_scores)
display(test_frame)
for filename in ["fig_3_5_validation_rmse.png", "fig_3_6_test_predictions.png"]:
    display(NotebookImage(filename=str(FIG / filename)))
residual_frame = test_frame.copy()
residual_frame["residual_t_ha"] = residual_frame["yield_t_ha"] - residual_frame["predicted_t_ha"]
residual_frame["absolute_error_t_ha"] = residual_frame["residual_t_ha"].abs()
display(residual_frame)
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
axes[0].scatter(test_pred, residual_frame["residual_t_ha"], color=NAVY)
axes[0].axhline(0, color="grey", linestyle="--")
axes[0].set(xlabel="Predicted yield (t/ha)", ylabel="Actual minus predicted (t/ha)", title="Residuals versus predictions")
axes[1].bar(residual_frame["year"].astype(str), residual_frame["residual_t_ha"], color=EARTH)
axes[1].axhline(0, color="grey", linestyle="--")
axes[1].set(xlabel="Test harvest year", ylabel="Residual (t/ha)", title="Errors by held-out year")
stats.probplot(residual_frame["residual_t_ha"], dist="norm", plot=axes[2])
axes[2].set_title("Residual Q–Q plot (only four points)")
plt.tight_layout(); plt.show()
fig, ax = plt.subplots(figsize=(9, 5))
importance_plot = importance_table.sort_values("importance_mean")
ax.barh(importance_plot["feature"], importance_plot["importance_mean"], color=NAVY)
ax.axvline(0, color="grey", linewidth=1)
ax.set(xlabel="Recorded mean drop in validation R²",
       title="Supplementary validation permutation importance")
plt.tight_layout(); plt.show()
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
cutoffs = y.loc[train].quantile([1/3, 2/3]).to_numpy()
actual_bands = np.digitize(y.loc[test].to_numpy(), cutoffs)
predicted_bands = np.digitize(test_pred, cutoffs)
print("Training-only yield-band cutoffs (t/ha):", cutoffs)
print("Low < first cutoff; middle ≥ first and < second; high ≥ second.")
cm = confusion_matrix(actual_bands, predicted_bands, labels=[0, 1, 2])
ConfusionMatrixDisplay(cm, display_labels=["Low", "Middle", "High"]).plot(cmap="Blues", colorbar=False)
plt.title("Supplementary yield-band confusion matrix: four test seasons")
plt.tight_layout(); plt.show()
''')
            md('''### Interpretation

Read error magnitudes in tonnes per hectare and R² against the held-out mean baseline. A negative test R² means the model did not beat a predictor using the test-target mean in the R² denominator, even if it beats the separately fitted training-mean baseline in MAE or RMSE. Permutation importance uses validation data and can be negative; correlated predictors make individual rankings unstable. Yield-band counts are sensitive to the training tertiles and the very small test sample. Neither these diagnostics nor the national target establish farm-level prediction performance.''')
    md('''## Appendix A Original document code and graph screenshots

These images are copied byte for byte from the supplied document and embedded as notebook attachments. They remain visible even when this notebook is moved. They are reference screenshots; supplementary charts above do not replace them. The university logo is omitted because it is not code or a graph.''')
    import base64
    image_labels={2:'Original quality checks',3:'Original rainfall agreement',4:'Original held-out predictions',5:'Original yield and rainfall time series',6:'Original correlation matrix',7:'Original yield histogram',8:'Original rainfall and yield scatter',9:'Original validation importance',10:'Original acquisition code screenshot',11:'Original quality and integration code screenshot',12:'Original model code screenshot',13:'Original evaluation code screenshot'}
    with zipfile.ZipFile(document) as z:
        image_manifest=[]
        for number,label in image_labels.items():
            name=f'image{number}.png'; data=z.read('word/media/'+name)
            cell=nb.v4.new_markdown_cell(f'### {label}\n\n![{label}](attachment:{name})')
            cell.attachments={name:{'image/png':base64.b64encode(data).decode()}}
            cells.append(cell)
            image_manifest.append({'image':name,'sha256':hashlib.sha256(data).hexdigest()})
    md('## Appendix B Consolidation provenance\n\nOriginal real master code cells were copied without edits. The five numbered real-data notebooks cover the same stages and are retained alongside this notebook. Synthetic notebooks were excluded. Original code/graph screenshot hashes:\n\n'+ '\n'.join(f'- `{r["image"]}`: `{r["sha256"]}`' for r in image_manifest))
    result=nb.v4.new_notebook(cells=cells, metadata=copy.deepcopy(original.metadata))
    result.metadata['consolidation']={'source':'smartcrop_real_master.ipynb','document':Path(document).name,'screenshots':image_manifest,'originals_preserved':True}
    nb.validate(result)
    nb.write(result, OUT)
    print(OUT)
    return OUT

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--document', type=Path, default=Path('/home/marvelous/Downloads/Capstone (1).docx'))
    build(parser.parse_args().document)
