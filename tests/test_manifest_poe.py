from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from conftest import IMAGE_HASH, make_poe
from megdan_schema.manifest import SetManifest
from megdan_schema.poe import DifficultyFactors, PoERecord, RecordState, ToolCoverage


def _manifest(**overrides):
    data = {
        "set_id": "ABCD2026",
        "seed": 1337,
        "source_image_hash": IMAGE_HASH,
        "poligon_version": "0.9.0",
        "treska_version": "0.3.1",
        "created_utc": "2026-10-31T12:00:00Z",
    }
    data.update(overrides)
    return data


# --- SetManifest --------------------------------------------------------------------


def test_manifest_valid_and_round_trips():
    m = SetManifest(**_manifest())
    assert m.created_utc == datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
    assert SetManifest.model_validate_json(m.model_dump_json()) == m


def test_manifest_accepts_explicit_utc_offset():
    SetManifest(**_manifest(created_utc="2026-10-31T12:00:00+00:00"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("set_id", "abc"),
        ("seed", "1337"),
        ("seed", 1.5),
        ("seed", True),
        ("source_image_hash", IMAGE_HASH.removeprefix("sha256:")),
        ("poligon_version", ""),
        ("treska_version", ""),
        ("created_utc", "2026-10-31T12:00:00"),  # naive
        ("created_utc", "2026-10-31T12:00:00+01:00"),  # not UTC
        ("created_utc", datetime(2026, 10, 31, tzinfo=timezone(timedelta(hours=-5)))),
    ],
)
def test_manifest_rejects(field, value):
    with pytest.raises(ValidationError):
        SetManifest(**_manifest(**{field: value}))


def test_manifest_forbids_extra_fields():
    with pytest.raises(ValidationError):
        SetManifest(**_manifest(extra="x"))


# --- PoERecord ----------------------------------------------------------------------


def test_poe_valid_and_round_trips(poe_data):
    rec = PoERecord(**poe_data)
    assert rec.record_state is RecordState.LIVE
    assert rec.tool_coverage is ToolCoverage.AUTO_OPEN
    assert rec.trap_tags == [] and rec.related_poe == []
    assert PoERecord.model_validate_json(rec.model_dump_json()) == rec


def test_enum_values_are_exactly_the_spec():
    assert {s.value for s in RecordState} == {"live", "deleted", "wal_uncheckpointed", "freelist", "carved"}
    assert {c.value for c in ToolCoverage} == {"auto_commercial", "auto_open", "manual_query", "custom_script"}


@pytest.mark.parametrize("state", [s.value for s in RecordState])
def test_every_record_state_accepted(state):
    PoERecord(**make_poe(record_state=state))


@pytest.mark.parametrize(
    "field,value",
    [
        ("poe_id", "POE-ABCD-1"),
        ("poe_id", "MGD-ABCD-01"),
        ("source_image_hash", "deadbeef"),
        ("artefact_file_hash", IMAGE_HASH.upper()),
        ("artefact_path", ""),
        ("record_state", "archived"),
        ("tool_coverage", "magic"),
        ("parser", "sqlite-messages-1.2.0"),
        ("parser", "sqlite:messages"),
        ("parser", "sqlite:messages@"),
        ("parser", "sql ite:messages@1"),
        ("normalisation_rule", ""),
        ("how_to_find", ""),
        ("points", -1),
        ("points", "100"),
        ("raw_value", 17),
        ("related_poe", ["nope"]),
        ("locator", "table=messages"),
    ],
)
def test_poe_rejects(field, value):
    with pytest.raises(ValidationError):
        PoERecord(**make_poe(**{field: value}))


def test_poe_forbids_extra_fields():
    with pytest.raises(ValidationError):
        PoERecord(**make_poe(answer="x"))


def test_poe_optional_lists():
    rec = PoERecord(**make_poe(trap_tags=["timezone"], related_poe=["POE-ABCD-0002"]))
    assert rec.related_poe == ["POE-ABCD-0002"]


# --- DifficultyFactors --------------------------------------------------------------


@pytest.mark.parametrize("value", [0, 1, 2, 3])
def test_factor_bounds_ok(value):
    DifficultyFactors(tool_coverage=value, hops=value, obscurity=value, traps=value)


@pytest.mark.parametrize("value", [-1, 4, 1.0, "1", True])
@pytest.mark.parametrize("field", ["tool_coverage", "hops", "obscurity", "traps"])
def test_factor_bounds_bad(field, value):
    data = {"tool_coverage": 0, "hops": 0, "obscurity": 0, "traps": 0, field: value}
    with pytest.raises(ValidationError):
        DifficultyFactors(**data)


def test_factors_require_all_four():
    with pytest.raises(ValidationError):
        DifficultyFactors(tool_coverage=0, hops=0, obscurity=0)
