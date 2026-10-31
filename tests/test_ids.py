import pytest
from pydantic import BaseModel, ValidationError

from megdan_schema.ids import (
    ChallengeId,
    PoeId,
    SetId,
    format_challenge_id,
    format_poe_id,
    is_valid_challenge_id,
    is_valid_poe_id,
    is_valid_set_id,
    parse_challenge_id,
    parse_poe_id,
)


class _M(BaseModel):
    set_id: SetId
    challenge_id: ChallengeId
    poe_id: PoeId


@pytest.mark.parametrize("value", ["ABCD", "A1B2", "ABCDEFGHIJKL", "0000", "SET2026"])
def test_valid_set_ids(value):
    assert is_valid_set_id(value)


@pytest.mark.parametrize("value", ["ABC", "ABCDEFGHIJKLM", "abcd", "AB-CD", "ABCD ", "", None, 1234])
def test_invalid_set_ids(value):
    assert not is_valid_set_id(value)


@pytest.mark.parametrize(
    "value,expected",
    [("MGD-ABCD-01", ("ABCD", 1)), ("MGD-ABCD-10", ("ABCD", 10)), ("MGD-ABCDEFGHIJKL-99", ("ABCDEFGHIJKL", 99))],
)
def test_parse_challenge_id(value, expected):
    assert parse_challenge_id(value) == expected
    assert is_valid_challenge_id(value)


@pytest.mark.parametrize(
    "value",
    [
        "MGD-ABCD-00",
        "MGD-ABCD-100",
        "MGD-ABCD-1",
        "MGD-ABC-01",
        "MGD-abcd-01",
        "mgd-ABCD-01",
        "XYZ-ABCD-01",
        "MGD-ABCD-01\n",
        " MGD-ABCD-01",
        "",
        None,
        42,
    ],
)
def test_invalid_challenge_ids(value):
    assert not is_valid_challenge_id(value)
    with pytest.raises(ValueError):
        parse_challenge_id(value)


@pytest.mark.parametrize("n", [1, 9, 10, 50, 99])
def test_challenge_id_round_trip(n):
    cid = format_challenge_id("SET1", n)
    assert parse_challenge_id(cid) == ("SET1", n)


def test_format_challenge_id_pads():
    assert format_challenge_id("ABCD", 7) == "MGD-ABCD-07"


@pytest.mark.parametrize("n", [0, 100, -1])
def test_format_challenge_id_out_of_range(n):
    with pytest.raises(ValueError):
        format_challenge_id("ABCD", n)


@pytest.mark.parametrize("n", ["7", 7.0, True, None])
def test_format_challenge_id_wrong_type(n):
    with pytest.raises(TypeError):
        format_challenge_id("ABCD", n)


@pytest.mark.parametrize("s", ["abc", "AB", "ABCD-1", None])
def test_format_challenge_id_bad_set(s):
    with pytest.raises(ValueError):
        format_challenge_id(s, 1)


@pytest.mark.parametrize(
    "value,expected",
    [("POE-ABCD-0001", ("ABCD", 1)), ("POE-ABCD-0042", ("ABCD", 42)), ("POE-ABCD-0100", ("ABCD", 100)),
     ("POE-ABCD-1000", ("ABCD", 1000)), ("POE-ABCD-9999", ("ABCD", 9999))],
)
def test_parse_poe_id(value, expected):
    assert parse_poe_id(value) == expected
    assert is_valid_poe_id(value)


@pytest.mark.parametrize(
    "value", ["POE-ABCD-0000", "POE-ABCD-42", "POE-ABCD-10000", "POE-abcd-0001", "MGD-ABCD-0001", "", None]
)
def test_invalid_poe_ids(value):
    assert not is_valid_poe_id(value)
    with pytest.raises(ValueError):
        parse_poe_id(value)


@pytest.mark.parametrize("n", [1, 9, 10, 99, 100, 999, 1000, 9999])
def test_poe_id_round_trip(n):
    assert parse_poe_id(format_poe_id("ABCD", n)) == ("ABCD", n)


def test_format_poe_id_pads_and_bounds():
    assert format_poe_id("ABCD", 42) == "POE-ABCD-0042"
    with pytest.raises(ValueError):
        format_poe_id("ABCD", 0)
    with pytest.raises(ValueError):
        format_poe_id("ABCD", 10000)
    with pytest.raises(ValueError):
        format_poe_id("ab", 1)


def test_annotated_types_in_models():
    _M(set_id="ABCD", challenge_id="MGD-ABCD-01", poe_id="POE-ABCD-0001")
    for bad in (
        {"set_id": "abc", "challenge_id": "MGD-ABCD-01", "poe_id": "POE-ABCD-0001"},
        {"set_id": "ABCD", "challenge_id": "MGD-ABCD-00", "poe_id": "POE-ABCD-0001"},
        {"set_id": "ABCD", "challenge_id": "MGD-ABCD-01", "poe_id": "POE-ABCD-0000"},
    ):
        with pytest.raises(ValidationError):
            _M(**bad)


def test_model_types_reject_trailing_newline():
    for bad in (
        {"set_id": "ABCD\n", "challenge_id": "MGD-ABCD-01", "poe_id": "POE-ABCD-0001"},
        {"set_id": "ABCD", "challenge_id": "MGD-ABCD-01\n", "poe_id": "POE-ABCD-0001"},
        {"set_id": "ABCD", "challenge_id": "MGD-ABCD-01", "poe_id": "POE-ABCD-0001\n"},
    ):
        with pytest.raises(ValidationError):
            _M(**bad)
