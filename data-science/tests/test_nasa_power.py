"""NASA POWER parsing. No live request."""

from acquisition.nasa_power import FILL, _records_from_payload


def test_missing_fill_becomes_null_and_units_stay_numeric():
    payload = {
        "properties": {
            "parameter": {
                "T2M": {"20200101": 24.5, "20200102": FILL},
                "PRECTOTCORR": {"20200101": 3.0, "20200102": 0.0},
            }
        }
    }
    rows = _records_from_payload(payload, 2020)
    assert rows[0]["date"] == "2020-01-01"
    assert rows[0]["T2M"] == 24.5
    assert rows[0]["PRECTOTCORR"] == 3.0
    assert rows[1]["T2M"] is None
    assert rows[1]["PRECTOTCORR"] == 0.0
