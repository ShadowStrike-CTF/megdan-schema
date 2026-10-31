import pytest

from conftest import make_poe
from megdan_schema.hashing import flag_hash
from megdan_schema.plugin import ChallengeItem, to_solver_item
from megdan_schema.poe import PoERecord
from megdan_schema.validators import (
    MIN_INNER_LENGTH,
    PlaintextHit,
    check_answer_provenance,
    check_no_answer_fields,
    check_no_plaintext_flag,
)

FLAG = "FLAG{s3cret_value}"


def _hits(blobs, flag=FLAG):
    return {(h.blob, h.needle, h.encoding, h.offset) for h in check_no_plaintext_flag(blobs, flag)}


# --- INV-P1: check_no_plaintext_flag ------------------------------------------------


def test_clean_blobs_have_no_hits():
    assert check_no_plaintext_flag({"a.db": b"nothing here", "b.txt": b"", "c": b"FLAG{"}, FLAG) == []


def test_no_blobs():
    assert check_no_plaintext_flag({}, FLAG) == []


def test_full_flag_utf8():
    assert _hits({"a": b"xx" + FLAG.encode() + b"yy"}) == {("a", "flag", "utf-8", 2)}


def test_full_flag_utf16le():
    blob = b"\x00\x01" + FLAG.encode("utf-16-le")
    assert _hits({"a": blob}) == {("a", "flag", "utf-16-le", 2)}


def test_case_insensitive_both_encodings():
    assert _hits({"a": FLAG.upper().encode(), "b": FLAG.lower().encode("utf-16-le")}) == {
        ("a", "flag", "utf-8", 0),
        ("b", "flag", "utf-16-le", 0),
    }


def test_mixed_case_needle():
    assert _hits({"a": b"flag{S3CRET_value}"}, flag="Flag{s3Cret_VALUE}") == {("a", "flag", "utf-8", 0)}


def test_inner_value_alone_utf8_and_utf16():
    blob_a = b"token=S3CRET_VALUE;"
    blob_b = "v:s3cret_value".encode("utf-16-le")
    assert _hits({"a": blob_a, "b": blob_b}) == {("a", "inner", "utf-8", 6), ("b", "inner", "utf-16-le", 4)}


def test_inner_inside_full_hit_not_double_reported():
    hits = check_no_plaintext_flag({"a": FLAG.encode()}, FLAG)
    assert [h.needle for h in hits] == ["flag"]


def test_multiple_occurrences_and_blobs():
    blob = FLAG.encode() + b"|" + b"s3cret_value"
    assert _hits({"a": blob, "b": FLAG.encode()}) == {
        ("a", "flag", "utf-8", 0),
        ("a", "inner", "utf-8", len(FLAG) + 1),
        ("b", "flag", "utf-8", 0),
    }


def test_flag_without_braces_has_no_inner():
    assert _hits({"a": b"xx plainflag xx"}, flag="plainflag") == {("a", "flag", "utf-8", 3)}
    assert _hits({"a": b"lag"}, flag="plainflag") == set()


def test_empty_braces_have_no_inner():
    assert _hits({"a": b"FLAG"}, flag="FLAG{}") == set()


def test_short_inner_is_skipped():
    short = "F{" + "a" * (MIN_INNER_LENGTH - 1) + "}"
    assert _hits({"a": b"aaa aaa"}, flag=short) == set()
    exact = "F{" + "b" * MIN_INNER_LENGTH + "}"
    assert _hits({"a": b"x" + b"b" * MIN_INNER_LENGTH}, flag=exact) == {("a", "inner", "utf-8", 1)}


def test_non_ascii_flag_found_exactly():
    flag = "MGD{żółw_ÜBER}"
    assert _hits({"a": flag.encode(), "b": flag.encode("utf-16-le")}, flag=flag) == {
        ("a", "flag", "utf-8", 0),
        ("b", "flag", "utf-16-le", 0),
    }


def test_bytearray_and_memoryview_blobs():
    assert _hits({"a": bytearray(FLAG.encode()), "b": memoryview(FLAG.encode())}) == {
        ("a", "flag", "utf-8", 0),
        ("b", "flag", "utf-8", 0),
    }


@pytest.mark.parametrize("bad", ["", None, b"FLAG{x}"])
def test_bad_flag_argument(bad):
    with pytest.raises(ValueError):
        check_no_plaintext_flag({"a": b""}, bad)


def test_hit_model():
    assert check_no_plaintext_flag({"a": FLAG.encode()}, FLAG)[0] == PlaintextHit(
        blob="a", needle="flag", encoding="utf-8", offset=0
    )


# --- INV-P2: check_answer_provenance ------------------------------------------------

FH = flag_hash(FLAG, "salt")


def _item(**overrides):
    data = {
        "challenge_id": "MGD-ABCD-01",
        "title": "T",
        "prompt": "P",
        "points": 100,
        "flag_hash": FH,
        "answers": ["2024-10-31T00:00:00Z"],
        "poe_refs": ["POE-ABCD-0001"],
    }
    data.update(overrides)
    return data


INVENTORY = [
    PoERecord(**make_poe()),
    PoERecord(**make_poe(poe_id="POE-ABCD-0002", raw_value="alice", normalised_value="Alice")),
]


def _codes(problems):
    return [(p.code, p.location) for p in problems]


def test_provenance_ok_with_model_item_and_model_inventory():
    assert check_answer_provenance(ChallengeItem(**_item()), INVENTORY) == []


def test_provenance_matches_raw_value_too():
    assert check_answer_provenance(_item(answers=["1730332800000"]), INVENTORY) == []


def test_provenance_dict_inventory_and_mapping_by_id():
    dicts = [r.model_dump() for r in INVENTORY]
    assert check_answer_provenance(_item(), dicts) == []
    assert check_answer_provenance(_item(), {d["poe_id"]: d for d in dicts}) == []


def test_provenance_multiple_refs_and_answers():
    item = _item(answers=["Alice", "1730332800000"], poe_refs=["POE-ABCD-0001", "POE-ABCD-0002"])
    assert check_answer_provenance(item, INVENTORY) == []


def test_provenance_answer_must_come_from_a_cited_record():
    # "Alice" is in the inventory, but the item only cites POE-ABCD-0001.
    assert _codes(check_answer_provenance(_item(answers=["Alice"]), INVENTORY)) == [
        ("answer_not_in_cited_poe", "/answers/0")
    ]


def test_provenance_mismatch_is_exact():
    assert _codes(check_answer_provenance(_item(answers=["2024-10-31t00:00:00z"]), INVENTORY)) == [
        ("answer_not_in_cited_poe", "/answers/0")
    ]


def test_provenance_unknown_ref():
    item = _item(poe_refs=["POE-ABCD-0001", "POE-ABCD-0099"])
    assert _codes(check_answer_provenance(item, INVENTORY)) == [("unknown_poe", "/poe_refs/1")]


def test_provenance_unknown_ref_only_means_answer_unsupported():
    assert _codes(check_answer_provenance(_item(poe_refs=["POE-ABCD-0099"]), INVENTORY)) == [
        ("unknown_poe", "/poe_refs/0"),
        ("answer_not_in_cited_poe", "/answers/0"),
    ]


def test_provenance_missing_fields():
    assert _codes(check_answer_provenance({}, INVENTORY)) == [("no_answers", "/answers"), ("no_citations", "/poe_refs")]
    assert _codes(check_answer_provenance({"answers": "x", "poe_refs": "POE-ABCD-0001"}, INVENTORY)) == [
        ("no_answers", "/answers"),
        ("no_citations", "/poe_refs"),
    ]


def test_provenance_no_citations_flags_every_answer():
    assert _codes(check_answer_provenance(_item(poe_refs=[]), INVENTORY)) == [
        ("no_citations", "/poe_refs"),
        ("answer_not_in_cited_poe", "/answers/0"),
    ]


def test_provenance_non_string_values():
    item = _item(answers=[None, 17], poe_refs=[1, "POE-ABCD-0001"])
    assert _codes(check_answer_provenance(item, INVENTORY)) == [
        ("unknown_poe", "/poe_refs/0"),
        ("answer_not_in_cited_poe", "/answers/0"),
        ("answer_not_in_cited_poe", "/answers/1"),
    ]


def test_provenance_skips_malformed_inventory_records():
    inventory = [{"raw_value": "x"}, {"poe_id": 5}, make_poe(), object()]
    assert check_answer_provenance(_item(), inventory) == []


def test_provenance_record_missing_values_does_not_match_none():
    inventory = [{"poe_id": "POE-ABCD-0001"}]
    assert _codes(check_answer_provenance(_item(answers=[None]), inventory)) == [("answer_not_in_cited_poe", "/answers/0")]


# --- INV-P3: check_no_answer_fields -------------------------------------------------


def test_solver_item_from_model_is_clean():
    solver = to_solver_item(ChallengeItem(**_item()))
    assert check_no_answer_fields(solver) == []
    assert check_no_answer_fields(solver.model_dump()) == []


def test_setter_item_is_flagged():
    problems = check_no_answer_fields(ChallengeItem(**_item()))
    assert _codes(problems) == [("forbidden_field", "/answers")]


@pytest.mark.parametrize(
    "key",
    [
        "answer", "answers", "Answer", "expected_answer", "solution", "solution_steps",
        "flag", "flags", "FLAG", "flag_plain", "raw_flag", "artefact_path", "path", "filePath",
        "raw_value", "normalised_value", "how_to_find",
    ],
)  # fmt: skip
def test_forbidden_keys(key):
    assert _codes(check_no_answer_fields({"flag_hash": FH, key: "x"})) == [("forbidden_field", f"/{key}")]


@pytest.mark.parametrize("key", ["flag_hash", "FLAG_HASH", "title", "prompt", "points", "poe_refs", "hint"])
def test_allowed_keys(key):
    assert check_no_answer_fields({key: "x"}) == []


def test_nested_dicts_and_lists():
    item = {
        "flag_hash": FH,
        "hints": [{"text": "look at WAL"}, {"answer": "x"}],
        "meta": {"files": [{"source_path": "/a"}], "ok": (1, 2)},
        "a/b": {"flag": 1},
    }
    assert _codes(check_no_answer_fields(item)) == [
        ("forbidden_field", "/hints/1/answer"),
        ("forbidden_field", "/meta/files/0/source_path"),
        ("forbidden_field", "/a~1b/flag"),
    ]


def test_forbidden_key_value_is_still_walked():
    assert _codes(check_no_answer_fields({"solution": {"artefact_path": "/x"}})) == [
        ("forbidden_field", "/solution"),
        ("forbidden_field", "/solution/artefact_path"),
    ]


def test_list_of_items_and_non_str_keys():
    assert _codes(check_no_answer_fields([{"title": "a"}, {"answer": 1}])) == [("forbidden_field", "/1/answer")]
    assert check_no_answer_fields({1: "x", None: "y"}) == []


def test_tilde_escaping():
    assert _codes(check_no_answer_fields({"~x": {"path": 1}})) == [("forbidden_field", "/~0x/path")]


@pytest.mark.parametrize("scalar", [None, 1, "answer", b"flag"])
def test_scalars_are_clean(scalar):
    assert check_no_answer_fields(scalar) == []
