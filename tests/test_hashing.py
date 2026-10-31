import hashlib
import hmac

import pytest
from pydantic import BaseModel, ValidationError

from megdan_schema.hashing import (
    FlagHash,
    HashString,
    Sha256Hash,
    flag_hash,
    is_hash_string,
    parse_hash,
    sha256_str,
    verify_flag,
)

EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
ABC_SHA = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


class _M(BaseModel):
    any_hash: HashString
    content: Sha256Hash
    flag: FlagHash


def test_sha256_known_vectors():
    assert sha256_str(b"") == f"sha256:{EMPTY_SHA}"
    assert sha256_str(b"abc") == f"sha256:{ABC_SHA}"
    assert sha256_str(bytearray(b"abc")) == f"sha256:{ABC_SHA}"
    assert sha256_str(memoryview(b"abc")) == f"sha256:{ABC_SHA}"


def test_sha256_rejects_str():
    with pytest.raises(TypeError):
        sha256_str("abc")


def test_flag_hash_matches_independent_hmac():
    expected = hmac.new(b"pepper", "FLAG{hello}".encode("utf-8"), hashlib.sha256).hexdigest()
    assert flag_hash("FLAG{hello}", "pepper") == f"hmac-sha256:{expected}"
    assert flag_hash("FLAG{hello}", b"pepper") == f"hmac-sha256:{expected}"
    assert flag_hash("FLAG{hello}", bytearray(b"pepper")) == f"hmac-sha256:{expected}"


def test_flag_hash_rfc4231_case_2():
    # RFC 4231 test case 2: key "Jefe", data "what do ya want for nothing?"
    assert flag_hash("what do ya want for nothing?", "Jefe") == (
        "hmac-sha256:5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"
    )


def test_flag_hash_non_ascii_flag_is_utf8():
    expected = hmac.new(b"s", "FLAG{żółw}".encode("utf-8"), hashlib.sha256).hexdigest()
    assert flag_hash("FLAG{żółw}", "s") == f"hmac-sha256:{expected}"


@pytest.mark.parametrize("salt", ["", b""])
def test_flag_hash_rejects_empty_salt(salt):
    with pytest.raises(ValueError):
        flag_hash("FLAG{x}", salt)


def test_flag_hash_rejects_bad_types():
    with pytest.raises(TypeError):
        flag_hash("FLAG{x}", 123)
    with pytest.raises(TypeError):
        flag_hash(b"FLAG{x}", "s")


def test_verify_flag():
    h = flag_hash("FLAG{hello}", "pepper")
    assert verify_flag("FLAG{hello}", h, "pepper") is True
    assert verify_flag("FLAG{hellO}", h, "pepper") is False
    assert verify_flag("FLAG{hello} ", h, "pepper") is False
    assert verify_flag("FLAG{hello}", h, "salt") is False


def test_verify_flag_uses_constant_time_compare(monkeypatch):
    calls = []
    real = hmac.compare_digest

    def spy(a, b):
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr("megdan_schema.hashing.hmac.compare_digest", spy)
    assert verify_flag("F", flag_hash("F", "s"), "s")
    assert len(calls) == 1


@pytest.mark.parametrize(
    "bad",
    [
        EMPTY_SHA,  # bare hex
        f"sha256:{EMPTY_SHA}",  # wrong algorithm for a flag hash
        f"hmac-sha256:{EMPTY_SHA.upper()}",
        f"hmac-sha256:{EMPTY_SHA[:-1]}",
        "hmac-sha256:",
        None,
    ],
)
def test_verify_flag_rejects_malformed_hash(bad):
    with pytest.raises(ValueError):
        verify_flag("x", bad, "s")


def test_parse_hash():
    assert parse_hash(f"sha256:{ABC_SHA}") == ("sha256", ABC_SHA)
    assert parse_hash(f"hmac-sha256:{ABC_SHA}").algorithm == "hmac-sha256"


@pytest.mark.parametrize(
    "bad",
    [
        ABC_SHA,
        f"SHA256:{ABC_SHA}",
        f"sha256:{ABC_SHA.upper()}",
        f"sha256:{ABC_SHA}0",
        f"sha256:{ABC_SHA[:-2]}",
        f"md5:{ABC_SHA}",
        f"sha256: {ABC_SHA}",
        f"sha256:{ABC_SHA}\n",
        "",
        None,
        b"sha256:" + ABC_SHA.encode(),
    ],
)
def test_bad_hash_strings(bad):
    assert not is_hash_string(bad)
    with pytest.raises(ValueError):
        parse_hash(bad)


def test_hash_types_in_models():
    _M(any_hash=f"hmac-sha256:{ABC_SHA}", content=f"sha256:{ABC_SHA}", flag=f"hmac-sha256:{ABC_SHA}")
    with pytest.raises(ValidationError):
        _M(any_hash=ABC_SHA, content=f"sha256:{ABC_SHA}", flag=f"hmac-sha256:{ABC_SHA}")
    with pytest.raises(ValidationError):
        _M(any_hash=f"sha256:{ABC_SHA}", content=f"hmac-sha256:{ABC_SHA}", flag=f"hmac-sha256:{ABC_SHA}")
    with pytest.raises(ValidationError):
        _M(any_hash=f"sha256:{ABC_SHA}", content=f"sha256:{ABC_SHA}", flag=f"sha256:{ABC_SHA}")


def test_model_hash_types_reject_trailing_newline():
    with pytest.raises(ValidationError):
        _M(any_hash=f"sha256:{ABC_SHA}\n", content=f"sha256:{ABC_SHA}", flag=f"hmac-sha256:{ABC_SHA}")
    with pytest.raises(ValidationError):
        _M(any_hash=f"sha256:{ABC_SHA}", content=f"sha256:{ABC_SHA}", flag=f"hmac-sha256:{ABC_SHA}\n")
