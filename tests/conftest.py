import pytest

from megdan_schema.hashing import sha256_str

IMAGE_HASH = sha256_str(b"image")
FILE_HASH = sha256_str(b"file")


def make_poe(**overrides):
    data = {
        "poe_id": "POE-ABCD-0001",
        "source_image_hash": IMAGE_HASH,
        "artefact_path": "/data/data/com.example/databases/msg.db",
        "artefact_file_hash": FILE_HASH,
        "locator": {"table": "messages", "rowid": 17},
        "record_state": "live",
        "raw_value": "1730332800000",
        "normalised_value": "2024-10-31T00:00:00Z",
        "normalisation_rule": "unix_ms_to_iso8601_utc",
        "parser": "sqlite:messages@1.2.0",
        "how_to_find": "Query the messages table for the row whose sender is the suspect.",
        "tool_coverage": "auto_open",
        "difficulty_factors": {"tool_coverage": 1, "hops": 1, "obscurity": 0, "traps": 0},
        "points": 100,
    }
    data.update(overrides)
    return data


@pytest.fixture
def poe_data():
    return make_poe()
