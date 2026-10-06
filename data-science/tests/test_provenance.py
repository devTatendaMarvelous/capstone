"""Source labels stay attached to the source that produced them."""

from validation.provenance import provenance_frame


def test_faostat_is_national_and_power_is_a_grid():
    frame = provenance_frame({"nasa_daily": 10, "faostat": 3})
    levels = dict(zip(frame["data_source"], frame["geographic_level_note"]))
    assert levels["FAOSTAT"] == "national"
    assert levels["NASA POWER"] == "grid_cell"
    assert frame.loc[frame["data_source"] == "NASA POWER", "records"].iloc[0] == 10
