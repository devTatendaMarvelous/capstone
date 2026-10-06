# Synthetic maize observations

**These files are an archived synthetic exercise. They are not Macheke farm measurements, and the real-data pipeline does not read them.**

The generator now lives in `archive/synthetic/`. `src/data/synthetic.py` raises an import error so training cannot load it.

`macheke_maize_synthetic.csv` and `.xlsx` are produced by `generate_synthetic_dataset.py`. Every observation row has `data_source_type = SYNTHETIC`.

`generation_manifest.json` records the seed, rates, and which rows were altered so the file can be regenerated and audited. It is a generator log, not an agricultural dataset.

Season labels such as `2016/2017` are synthetic panel labels. They are not a claim that rainfall or yield matched those historical years.

Ward codes `SYN-W01` through `SYN-W06` are placeholders. They are not the official ward list for Macheke or Marondera District.

Do not merge this folder with real extracts unless the real rows are labelled `REAL` or `EXTERNAL` and kept distinguishable by `data_source_type`.
