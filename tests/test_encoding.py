import base64

import pytest

from megdan_schema.encoding import encode_b64, encode_hex


# Reference implementations, copied verbatim from Poligon (android.encode_flag, evidence._hex).
def _poligon_encode_flag(flag: str) -> str:
    return base64.b64encode(flag.encode()).decode()


def _poligon_hex(flag: str) -> str:
    return flag.encode().hex()


VECTORS = [
    "",
    "A",
    "AB",
    "ABC",
    "FLAG{hello_world}",
    "flag{0123456789abcdef}",
    "MGD{żółw-ünïcødé}",
    "CTF{🚩 emoji}",
    "tab\tnew\nline",
    "~" * 257,
]

KNOWN = [
    # (text, base64, hex)
    ("", "", ""),
    ("A", "QQ==", "41"),
    ("AB", "QUI=", "4142"),
    ("ABC", "QUJD", "414243"),
    ("FLAG{hi}", "RkxBR3toaX0=", "464c41477b68697d"),
    ("é", "w6k=", "c3a9"),
    ("🚩", "8J+aqQ==", "f09f9aa9"),
    ("?>?", "Pz4/", "3f3e3f"),  # exercises '+' / '/' alphabet choice
    ("\xfb\xff", "w7vDvw==", "c3bbc3bf"),
]


@pytest.mark.parametrize("text", VECTORS)
def test_b64_matches_poligon_byte_for_byte(text):
    assert encode_b64(text).encode() == _poligon_encode_flag(text).encode()


@pytest.mark.parametrize("text", VECTORS)
def test_hex_matches_poligon_byte_for_byte(text):
    assert encode_hex(text).encode() == _poligon_hex(text).encode()


@pytest.mark.parametrize("text,b64,hx", KNOWN)
def test_known_vectors(text, b64, hx):
    assert encode_b64(text) == b64
    assert encode_hex(text) == hx


def test_b64_alphabet_is_standard_not_urlsafe():
    assert "+" in encode_b64("🚩")
    assert "/" in encode_b64("?>?")
    assert "-" not in encode_b64("🚩") and "_" not in encode_b64("?>?")


def test_lone_surrogate_raises_like_poligon():
    with pytest.raises(UnicodeEncodeError):
        _poligon_encode_flag("\ud800")
    with pytest.raises(UnicodeEncodeError):
        encode_b64("\ud800")
    with pytest.raises(UnicodeEncodeError):
        encode_hex("\ud800")
