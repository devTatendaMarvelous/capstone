# Real data acquisition

This pipeline replaces the synthetic generator for new modelling work. It downloads verifiable sources and leaves a gap where a source does not provide Macheke farm yields. It does not invent farms, yields, or ward codes.

The study-area polygon in `data/external/macheke_boundary.geojson` is a bounding box around the town of Macheke. It is marked `study_area_approximation`. It is not an official district boundary.

## 1. Configure the study area

Edit `config/smartcrop_config.yaml`. The maize season defaults to November–March, labelled by the harvest year. January–February is the critical window. Both choices are agricultural assumptions and can be changed without editing Python.

## 2. Run acquisition

From `data-science/`:

```bash
python scripts/acquire_all.py --source all
python scripts/build_dataset.py
python scripts/validate_dataset.py
```

One source at a time:

```bash
python scripts/acquire_all.py --source nasa
python scripts/acquire_all.py --source chirps
python scripts/acquire_all.py --source soilgrids
python scripts/acquire_all.py --source faostat
python scripts/acquire_all.py --source zimstat
```

## 3. NASA POWER

`src/acquisition/nasa_power.py` calls the official daily point API for `T2M`, `T2M_MAX`, `T2M_MIN`, and `PRECTOTCORR` at the configured coordinate. Raw JSON is cached under `data/raw/nasa_power/`. The value `-999` is stored as missing. Seasonal features are means or sums over the configured season. This is grid weather, not farm weather.

## 4. CHIRPS

Daily CHIRPS is subset through the SERVIR ClimateSERV API for the study-area box (`datatype` 0). Full CHIRPS v3 continental rasters are not downloaded. The catalogue says so. Seasonal rainfall prefers these CHIRPS totals. `rainfall_days` counts days above the configured millimetre threshold.

## 5. SoilGrids

`src/acquisition/soilgrids.py` calls the SoilGrids 2.0 REST query for the study coordinate and the configured depths. Mapped values are divided by `d_factor`. Clay, sand, and silt are converted from g/kg to percent when the number is still above 100. These are 250 m predictions, not farm soil tests. The selected depth is `0-5cm`.

## 6. FAOSTAT

The Africa production zip from `bulks-faostat.fao.org` is filtered to Zimbabwe, item code 56, `Maize (corn)`. Green maize is excluded. Yield in kg/ha is converted with `kg/ha / 1000`. The result is national. It is not copied onto a farm identifier.

## 7. ZIMSTAT and Agritex

The public pages are requested and saved. If they do not expose a machine-readable Macheke maize table, ingestion status stays `reviewed_not_ingested`. No district total is split into fake farms.

## 8. Join

Seasonal NASA weather and CHIRPS rainfall are joined on harvest year. SoilGrids is attached as the same study-area prediction on every year. FAOSTAT national yield is joined on year. `geographic_level` for the climate row is `grid_cell`. `yield_geographic_level` is `national` when the target comes from FAOSTAT.

## 9. Provenance

`data/metadata/provenance.csv`, `source_catalogue.csv`, and `dataset_manifest.json` record the source, URL, resolution, and row counts. `synthetic_record` is false.

## 10. Reproduce the modelling table

`data/processed/capstone_dataset_real.csv` is the integrated table. `data/processed/modelling_dataset.csv` keeps rows with a non-null real `yield_t_ha`. Missing predictors are not filled in that file. Median imputation, when a model is fit, happens inside the training pipeline on the training years only.

If there is no verified Macheke farm yield, the training script prints the farm-level warning. A model may still be fit to the national yield series so the notebooks can report MAE, RMSE, and R². Those scores are not farm-level accuracy, and R² is not classification accuracy.

The log file is `data/logs/acquisition.log`.
