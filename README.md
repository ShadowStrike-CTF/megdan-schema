# megdan-schema

Shared contracts for the Megdan line of CTF tools: schemas, validators and pure helpers that every Megdan tool agrees on, so the tools can't drift apart.

**v0.1.0** · Python ≥ 3.11 · depends only on `pydantic>=2.4` · MIT

## What's in it

| Module | Contract |
|---|---|
| `ids` | Challenge IDs `MGD-{SET}-{NN}` (SET = `[A-Z0-9]{4,12}`, NN = `01`–`99`) and point-of-entry IDs `POE-{SET}-{nnnn}`. Parse, format, validate. |
| `manifest` | Set manifest: `set_id`, `seed`, `source_image_hash`, `poligon_version`, `treska_version`, `created_utc`. |
| `hashing` | Algorithm-prefixed hash strings only (`sha256:{hex}`, `hmac-sha256:{hex}`); bare hex is rejected. `sha256_str`, `flag_hash`, `verify_flag` (constant-time compare). |
| `encoding` | `encode_b64`, `encode_hex`: the single source for flag encodings used in generated challenges. |
| `poe` | Point-of-entry (PoE) record: one findable thing in an extraction, with its location, record state, raw and normalised values, parser, tool coverage and difficulty factors. |
| `rubric` | Difficulty rubric: four factors (0–3 each) → score 0–12 → tier D1–D5 → 100–500 points, plus `override(points, reason)` with a required reason. |
| `plugin` | Plugin contract: `PLUGIN_API`, slot names, entry-point groups, `ChallengeItem`, `ScoreResult`, `PanelData`, the `describe()` shape and an API-compatibility check. |
| `validators` | Pure invariant checks that hosts run on plugin output: no plaintext flag in artefacts, every answer traceable to a cited PoE record, no answer fields in solver-facing items. |
| `export` | `python -m megdan_schema.export` writes JSON Schema for every model to `schemas/`. |

There is no application logic here. Anything that reads disk images, builds challenges, or renders UI belongs in a host tool.

## Distribution: not on PyPI

This package is **not published to PyPI** and won't be until the name is approved. PyPI also rejects packages that depend on a git URL, so the host tools can't depend on this repo directly and still publish themselves.

So:

1. **This repo is the source of truth.** Releases are git tags (`v0.1.0`, …), cut by the maintainer.
2. **Hosts vendor a pinned copy.** Each host copies `src/megdan_schema/` from a tagged release into its own tree and records the SHA-256 of every vendored file.
3. **Hosts check the pin in their CI.** `tools/vendor_check.py` prints the SHA-256 of each vendorable module:

   ```bash
   python tools/vendor_check.py
   ```

   The host keeps that output next to its vendored copy and fails CI if a vendored file's hash no longer matches. To upgrade, re-vendor from a newer tag and update the pins in the same commit.

Each module imports only the standard library, pydantic and its sibling modules, so the package folder can be copied as a unit. Line endings are pinned to LF (`.gitattributes`) so hashes match on every OS.

## Development

```bash
pip install -e '.[test]'
```

```bash
pytest --cov=megdan_schema --cov-branch --cov-report=term-missing
```

```bash
python -m megdan_schema.export --check
```

CI runs the tests on Python 3.11–3.13 and checks that `schemas/` is up to date. It never publishes anything.

## Licence

MIT. See [LICENSE](LICENSE).

© 2026 ShadowStrike · *Aut Viam Inveniam Aut Faciam*
