"""SoilGrids unit conversion."""

from acquisition.soilgrids import _points


def test_ph_is_divided_by_d_factor_and_clay_above_100_becomes_percent():
    payload = {
        "geometry": {"coordinates": [31.85, -18.14]},
        "properties": {
            "layers": [
                {
                    "name": "phh2o",
                    "unit_measure": {"d_factor": 10, "mapped_units": "pH*10", "target_units": "pH"},
                    "depths": [{"label": "0-5cm", "values": {"mean": 58}}],
                },
                {
                    "name": "clay",
                    "unit_measure": {"d_factor": 1, "mapped_units": "g/kg", "target_units": "g/kg"},
                    "depths": [{"label": "0-5cm", "values": {"mean": 250}}],
                },
            ]
        },
    }
    rows = {row["property"]: row for row in _points(payload, "phh2o")}
    assert rows["phh2o"]["value"] == 5.8
    assert rows["clay"]["value"] == 25.0
    assert rows["phh2o"]["latitude"] == -18.14
