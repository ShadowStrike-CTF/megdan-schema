import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

import megdan_schema
from megdan_schema import export

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"


def _load_vendor_check():
    spec = importlib.util.spec_from_file_location("vendor_check", ROOT / "tools" / "vendor_check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vendor_check = _load_vendor_check()


# --- export -------------------------------------------------------------------------


def test_committed_schemas_are_up_to_date():
    assert export.stale_schemas(SCHEMAS) == []
    assert sorted(p.name for p in SCHEMAS.glob("*.json")) == sorted(f"{n}.json" for n in export.MODELS)


def test_render_is_deterministic_json():
    a, b = export.render_schemas(), export.render_schemas()
    assert a == b
    for text in a.values():
        assert text.endswith("\n")
        json.loads(text)


def test_write_and_check(tmp_path, capsys):
    out = tmp_path / "s"
    assert export.main(["--out", str(out), "--check"]) == 1
    assert "out of date" in capsys.readouterr().out

    assert export.main(["--out", str(out)]) == 0
    assert "wrote" in capsys.readouterr().out
    assert export.main(["--out", str(out), "--check"]) == 0
    assert "up to date" in capsys.readouterr().out

    (out / "score_result.json").write_text("{}\n", encoding="utf-8")
    assert export.stale_schemas(out) == ["score_result.json"]
    assert export.main(["--out", str(out), "--check"]) == 1


def test_bare_hex_rejected_in_exported_schema():
    schema = json.loads((SCHEMAS / "poe_record.json").read_text())
    assert "sha256" in schema["properties"]["source_image_hash"]["pattern"]


# --- vendor_check -------------------------------------------------------------------


def test_vendor_hashes_match_hashlib():
    pkg = Path(megdan_schema.__file__).parent
    pairs = vendor_check.file_hashes(pkg)
    names = [rel for _, rel in pairs]
    assert "megdan_schema/encoding.py" in names and "megdan_schema/py.typed" in names
    assert names == sorted(names)
    for digest, rel in pairs:
        assert digest == hashlib.sha256((pkg.parent / rel).read_bytes()).hexdigest()


def test_vendor_skips_bytecode(tmp_path):
    pkg = tmp_path / "megdan_schema"
    (pkg / "__pycache__").mkdir(parents=True)
    (pkg / "a.py").write_bytes(b"x = 1\n")
    (pkg / "__pycache__" / "a.cpython-313.pyc").write_bytes(b"\0")
    (pkg / "stray.pyc").write_bytes(b"\0")
    assert vendor_check.file_hashes(pkg) == [(hashlib.sha256(b"x = 1\n").hexdigest(), "megdan_schema/a.py")]


def test_vendor_main_output(capsys):
    assert vendor_check.main([]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines and all(len(line.split("  ")[0]) == 64 for line in lines)
    assert any(line.endswith("  megdan_schema/validators.py") for line in lines)


def test_vendor_main_bad_dir(tmp_path):
    with pytest.raises(SystemExit):
        vendor_check.main(["--package", str(tmp_path / "missing")])


def test_version():
    assert megdan_schema.__version__ == "0.1.0"
    assert all(hasattr(megdan_schema, name) for name in megdan_schema.__all__)
