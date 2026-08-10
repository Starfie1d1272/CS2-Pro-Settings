"""Normalization rules."""
from cs2_pro_settings.normalize import (
    color_category,
    normalize_field,
    parse_resolution,
    to_bool,
    to_float,
    to_hz,
    to_int,
)


def test_float_commas_percent_units():
    assert to_float("1,200") == 1200.0
    assert to_float("93%") == 93.0
    assert to_float("400dpi") == 400.0
    assert to_float("2.5") == 2.5
    assert to_float("n/a") is None
    assert to_float(None) is None


def test_int():
    assert to_int("800") == 800
    assert to_int(2.5) == 2


def test_hz():
    assert to_hz("1000Hz") == 1000
    assert to_hz("1,000 Hz") == 1000
    assert to_hz(360) == 360


def test_resolution():
    assert parse_resolution("1280x960") == (1280, 960)
    assert parse_resolution("1920x1080") == (1920, 1080)
    assert parse_resolution("junk") is None
    assert parse_resolution(None) is None


def test_bool():
    assert to_bool("Yes") is True
    assert to_bool("Enabled") is True
    assert to_bool("true") is True
    assert to_bool("1") is True
    assert to_bool("No") is False
    assert to_bool("Disabled") is False
    assert to_bool("0") is False
    assert to_bool("sometimes") is None


def test_missing_values():
    assert to_float("") is None
    assert to_float("Unknown") is None
    assert to_hz("") is None


def test_crosshair_color():
    assert color_category("Custom (255,255,255)") == "Custom"
    assert color_category("cyan") == "Cyan"
    assert color_category("Green") == "Green"
    assert color_category("RGB 0,255,145") == "Custom"
    assert color_category(None) is None


def test_normalize_field_mapping():
    attr, value = normalize_field("dpi", "800")
    assert (attr, value) == ("dpi", 800.0)
    attr, value = normalize_field("pollingRate", "4000Hz")
    assert (attr, value) == ("polling_rate", 4000)
    attr, value = normalize_field("edpiCalculated", "1000")
    assert (attr, value) == ("edpi", 1000.0)
    attr, value = normalize_field("radarCentered", "true")
    assert (attr, value) == ("radar_centered", True)
    attr, value = normalize_field("unknown_field", "x")
    assert attr is None


def test_normalize_field_unknown_junk():
    attr, value = normalize_field("dpi", "banana")
    assert attr == "dpi"
    assert value is None
