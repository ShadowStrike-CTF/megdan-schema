# CLAUDE.md: megdan-schema

## Scope
Shared contracts for the Megdan tools: **schemas, validators and pure helpers only.**
- pydantic v2 models, their JSON Schema export (`schemas/*.json`, committed), and pure functions.
- No I/O beyond `export` (writes `schemas/`) and `tools/vendor_check.py` (reads source files).
- No application logic: no image parsing, challenge generation, scoring engines, UI or network code.

Layout: `src/megdan_schema/` (one module per contract), `tests/`, `schemas/`, `tools/`.

## Distribution decision
- **Not on PyPI.** The package name needs approval, and PyPI rejects packages with git-URL dependencies, so hosts can't depend on this repo directly.
- This repo is the source of truth. The maintainer tags releases; hosts **vendor** a pinned copy and check it with the SHA-256 output of `tools/vendor_check.py`.
- Modules import only stdlib, pydantic and sibling modules, so the package can be vendored as one folder.
- Any change to a module changes its vendor hash. Say so in the PR.

## Conventions
- Python ≥ 3.11, `pydantic>=2.4` (2.0–2.3 lack `StringConstraints`), hatchling build.
- Models use `extra="forbid"`. Hash strings are always algorithm-prefixed (`sha256:` / `hmac-sha256:`), lowercase hex.
- Validators return a list of problems (empty = OK). They report malformed plugin output instead of raising; only bad host-supplied arguments raise.
- Keep full line and branch coverage. Regenerate `schemas/` (`python -m megdan_schema.export`) whenever a model changes.
- Wording: follow the neutral-terms rule supplied in task briefs.

## What NOT to do
- Don't publish to PyPI or add any publish/upload step to CI.
- Don't add dependencies beyond pydantic, and never add git-URL dependencies.
- Don't create or push tags. The maintainer tags releases.
- Don't add app logic, I/O helpers or host-specific code here.
- Don't accept bare-hex hashes, plaintext flags or answer fields in solver-facing models.
- Don't put private project terminology, internal notes or task-brief tables in any file in this public repo.
