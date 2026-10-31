import pytest
from pydantic import ValidationError

from megdan_schema.hashing import flag_hash, sha256_str
from megdan_schema.plugin import (
    ENTRY_POINT_GROUPS,
    PLUGIN_API,
    REQUIRED_PLUGIN_ATTRIBUTES,
    SLOT_CALLABLES,
    ChallengeItem,
    PanelData,
    PluginDescription,
    ScoreResult,
    Slot,
    SolverChallengeItem,
    clamp_score,
    is_api_compatible,
    parse_api_version,
    to_solver_item,
)

FH = flag_hash("FLAG{x}", "salt")


def _item(**overrides):
    data = {
        "challenge_id": "MGD-ABCD-01",
        "title": "First contact",
        "prompt": "When did the suspect first message the victim?",
        "points": 200,
        "flag_hash": FH,
        "answers": ["2024-10-31T00:00:00Z"],
        "poe_refs": ["POE-ABCD-0001"],
    }
    data.update(overrides)
    return data


# --- constants ----------------------------------------------------------------------


def test_contract_constants():
    assert PLUGIN_API == "1.0"
    assert ENTRY_POINT_GROUPS == {
        Slot.SCENARIO_PROVIDER: "megdan.poligon.scenario_providers",
        Slot.SCORER: "megdan.poligon.scorers",
        Slot.PANEL: "megdan.sarissa.panels",
    }
    assert SLOT_CALLABLES == {Slot.SCENARIO_PROVIDER: "provide", Slot.SCORER: "score", Slot.PANEL: "panel"}
    assert REQUIRED_PLUGIN_ATTRIBUTES == ("PLUGIN_API", "NAME", "VERSION", "describe")


# --- describe() ---------------------------------------------------------------------


@pytest.mark.parametrize("slot", ["scenario_provider", "scorer", "panel"])
def test_describe_shape_ok(slot):
    d = PluginDescription.model_validate({"name": "demo_plugin-1", "version": "0.1.0", "api": "1.0", "slot": slot})
    assert d.slot is Slot(slot)


@pytest.mark.parametrize(
    "patch",
    [
        {"name": "Demo"},
        {"name": "demo plugin"},
        {"name": ""},
        {"version": ""},
        {"api": "one"},
        {"api": "1"},
        {"slot": "exporter"},
        {"description": "extra keys are not part of describe()"},
    ],
)
def test_describe_shape_bad(patch):
    data = {"name": "demo", "version": "0.1.0", "api": "1.0", "slot": "scorer", **patch}
    with pytest.raises(ValidationError):
        PluginDescription.model_validate(data)


def test_describe_requires_all_keys():
    with pytest.raises(ValidationError):
        PluginDescription.model_validate({"name": "demo", "version": "0.1.0", "api": "1.0"})


# --- API compatibility --------------------------------------------------------------


@pytest.mark.parametrize("api,ok", [("1.0", True), ("1.7", True), ("1.0.3", True), ("2.0", False), ("0.9", False)])
def test_is_api_compatible(api, ok):
    assert is_api_compatible(api) is ok


@pytest.mark.parametrize("api", ["", "1", "v1.0", "1.0-beta", "01.0", "1.x", None, 1.0])
def test_is_api_compatible_garbage(api):
    assert is_api_compatible(api) is False


def test_is_api_compatible_custom_host():
    assert is_api_compatible("2.1", host_api="2.0")
    assert not is_api_compatible("2.1", host_api="garbage")


def test_parse_api_version():
    assert parse_api_version("1.0") == (1, 0)
    assert parse_api_version("10.20.30") == (10, 20)
    with pytest.raises(ValueError):
        parse_api_version("1")


# --- ChallengeItem ------------------------------------------------------------------


def test_challenge_item_ok_and_solver_view():
    item = ChallengeItem(**_item())
    solver = to_solver_item(item)
    assert isinstance(solver, SolverChallengeItem)
    assert solver.model_dump() == {
        "challenge_id": "MGD-ABCD-01",
        "title": "First contact",
        "prompt": "When did the suspect first message the victim?",
        "points": 200,
        "flag_hash": FH,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("challenge_id", "MGD-ABCD-00"),
        ("title", ""),
        ("prompt", ""),
        ("points", -5),
        ("points", "200"),
        ("flag_hash", sha256_str(b"x")),  # content hash, not a salted flag hash
        ("flag_hash", FH.removeprefix("hmac-sha256:")),
        ("answers", []),
        ("answers", [42]),
        ("poe_refs", []),
        ("poe_refs", ["POE-ABCD-1"]),
    ],
)
def test_challenge_item_rejects(field, value):
    with pytest.raises(ValidationError):
        ChallengeItem(**_item(**{field: value}))


def test_solver_item_forbids_answer_fields():
    data = _item()
    with pytest.raises(ValidationError):
        SolverChallengeItem(**data)  # answers / poe_refs are extra here


# --- ScoreResult --------------------------------------------------------------------


@pytest.mark.parametrize("points,max_points", [(0, 0), (0, 10), (10, 10), (3, 10)])
def test_score_result_ok(points, max_points):
    ScoreResult(points=points, max_points=max_points, detail="")


@pytest.mark.parametrize(
    "data",
    [
        {"points": 11, "max_points": 10, "detail": ""},
        {"points": -1, "max_points": 10, "detail": ""},
        {"points": 1, "max_points": -1, "detail": ""},
        {"points": 1.5, "max_points": 10, "detail": ""},
        {"points": True, "max_points": 10, "detail": ""},
        {"points": 1, "max_points": 10},
        {"points": 1, "max_points": 10, "detail": 5},
        {"points": 1, "max_points": 10, "detail": "", "bonus": 1},
    ],
)
def test_score_result_rejects(data):
    with pytest.raises(ValidationError):
        ScoreResult.model_validate(data)


@pytest.mark.parametrize(
    "points,max_points,expected,clamped",
    [(5, 10, 5, False), (0, 10, 0, False), (10, 10, 10, False), (15, 10, 10, True), (-3, 10, 0, True), (4, 0, 0, True)],
)
def test_clamp_score(points, max_points, expected, clamped):
    result, was_clamped = clamp_score(points, max_points, "d")
    assert result == ScoreResult(points=expected, max_points=max_points, detail="d")
    assert was_clamped is clamped


def test_clamp_score_bad_input():
    with pytest.raises(ValueError):
        clamp_score(1, -1)
    with pytest.raises(TypeError):
        clamp_score(1.5, 10)
    with pytest.raises(TypeError):
        clamp_score(1, True)


# --- PanelData ----------------------------------------------------------------------


def test_panel_rows_ok():
    p = PanelData.model_validate(
        {"title": "Summary", "rows": [{"label": "a", "value": "x"}, {"label": "b", "value": 2},
                                      {"label": "c", "value": 2.5}, {"label": "d", "value": None}]}
    )
    assert len(p.rows) == 4


def test_panel_empty_rows_ok():
    PanelData(title="Empty", rows=[])


def test_panel_table_ok():
    p = PanelData.model_validate({"title": "T", "columns": ["a", "b"], "table": [[1, "x"], [None, 2.0]]})
    assert p.columns == ["a", "b"]


@pytest.mark.parametrize(
    "data",
    [
        {"title": "T"},  # neither
        {"title": "T", "rows": [], "columns": ["a"], "table": [[1]]},  # both
        {"title": "T", "columns": ["a"]},  # columns without table
        {"title": "T", "table": [[1]]},  # table without columns
        {"title": "T", "columns": ["a", "b"], "table": [[1]]},  # ragged
        {"title": "T", "columns": ["a"], "table": [[1], [1, 2]]},  # ragged later row
        {"title": "", "rows": []},
        {"title": "T", "rows": [{"label": "a", "value": [1]}]},
        {"title": "T", "rows": [{"label": "a", "value": True}]},
        {"title": "T", "rows": [{"label": "a", "value": {"k": 1}}]},
        {"title": "T", "rows": [{"label": "a"}]},
        {"title": "T", "columns": ["a"], "table": [[{"x": 1}]]},
        {"title": "T", "rows": [], "html": "<b>no</b>"},
    ],
)
def test_panel_rejects(data):
    with pytest.raises(ValidationError):
        PanelData.model_validate(data)


def test_api_version_rejects_trailing_newline():
    assert is_api_compatible("1.0\n") is False
    with pytest.raises(ValidationError):
        PluginDescription.model_validate({"name": "demo\n", "version": "1", "api": "1.0", "slot": "panel"})
    with pytest.raises(ValidationError):
        PluginDescription.model_validate({"name": "demo", "version": "1", "api": "1.0\n", "slot": "panel"})
