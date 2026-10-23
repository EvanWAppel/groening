"""Stamp a fresh metro skeleton from this repo — the `make new-city` scaffold (TASKS E6).

Decided 2026-09-27: a scaffold + guide, not a shared pip package. The generator
writes a small, runnable project into an empty directory:

* ``city_config.py`` — the one per-city surface, as a stub (empty ``SOURCES``).
* ``build_warehouse.py`` — the city-agnostic engine helpers (ArcGIS pagination,
  TLS opt-out, IPv4-first, retrying GET, raw loading, build provenance) copied
  *verbatim* from Groening's ``build_warehouse.py`` at generation time, plus an
  empty ``FETCHERS`` registry the new city fills in.
* the dbt project, the build-provenance staging/mart pair, a one-page Streamlit
  app, Dockerfile, pyproject, a catalog-contract test, README and BLOCKED.md.

Templates live in ``scaffold/*.tmpl`` with ``__CODENAME__`` / ``__CITY__`` /
``__DB__`` placeholders. See ``docs/new-city.md`` for the full walkthrough.

Usage:
    make new-city DEST=../robbins CODENAME=robbins CITY="Seattle, WA" DB=seattle
    uv run python new_city.py ../robbins --codename robbins --city "Seattle, WA" --db seattle
"""

import argparse
import ast
import logging
import re
from pathlib import Path

log = logging.getLogger("new_city")

ROOT = Path(__file__).parent
TEMPLATES = ROOT / "scaffold"

# Generic helpers lifted verbatim from build_warehouse.py into the new city's build.
ENGINE_FUNCTIONS = (
    "_ipv4_first",
    "_get_json",
    "_ssl_ctx",
    "fetch_layer",
    "fetch_features",
    "_centroid",
    "_epoch_to_date",
    "_urlopen",
    "collect_build_metadata",
    "_raw_row_counts",
    "load_raw",
)

# Generic helpers lifted verbatim from city_config.py into the stub config.
CONFIG_FUNCTIONS = ("source_catalog_rows",)

# Files copied byte-for-byte from this repo (already city-neutral).
VERBATIM_FILES = (
    "models/staging/stg_build_metadata.sql",
    "models/marts/mart_build_metadata.sql",
    ".gitignore",
    ".python-version",
)

# dbt project/profile names and the DuckDB file stem must be plain identifiers.
_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]*")
_PLACEHOLDER = re.compile(r"__[A-Z][A-Z_]*__")


def function_source(source: str, name: str) -> str:
    """Exact source text of the top-level function ``name`` in ``source``."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            segment = ast.get_source_segment(source, node)
            if segment is None:
                raise ValueError(f"could not recover source for {name}()")
            return segment
    raise KeyError(f"no top-level function {name}() to copy")


def _extract(path: Path, names: tuple[str, ...]) -> str:
    source = path.read_text()
    return "\n\n\n".join(function_source(source, name) for name in names)


def _validate(codename: str, city: str, db: str) -> None:
    for field, value in (("codename", codename), ("db", db)):
        if not _IDENTIFIER.fullmatch(value):
            raise ValueError(
                f"{field} {value!r} must be lowercase letters, digits and underscores, "
                "starting with a letter (dbt project/profile and DuckDB naming)"
            )
    if not city.strip():
        raise ValueError("city must be a non-blank display name, e.g. 'Seattle, WA'")


def _render(template: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        template = template.replace(f"__{key}__", value)
    leftover = _PLACEHOLDER.search(template)
    if leftover:
        raise ValueError(f"unfilled template placeholder {leftover.group()}")
    return template


def scaffold(dest: Path, codename: str, city: str, db: str) -> list[Path]:
    """Write a fresh metro skeleton into ``dest`` (which must be absent or empty).

    Returns the written paths. Raises ``ValueError`` on an unusable name and
    ``FileExistsError`` rather than overwrite anything already in ``dest``.
    """
    _validate(codename, city, db)
    dest = Path(dest)
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"{dest} is not empty; refusing to overwrite it")

    values = {
        "CODENAME": codename,
        "CITY": city.strip(),
        "DB": db,
        "ENGINE": _extract(ROOT / "build_warehouse.py", ENGINE_FUNCTIONS),
        "CONFIG_HELPERS": _extract(ROOT / "city_config.py", CONFIG_FUNCTIONS),
    }
    # Render everything before writing anything, so a bad template never leaves
    # a half-stamped directory behind.
    files: dict[str, str] = {
        tmpl.relative_to(TEMPLATES).as_posix().removesuffix(".tmpl"): _render(
            tmpl.read_text(), values
        )
        for tmpl in sorted(TEMPLATES.rglob("*.tmpl"))
    }
    files.update({rel: (ROOT / rel).read_text() for rel in VERBATIM_FILES})

    written = []
    for rel, text in files.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        written.append(path)
    log.info("Stamped %d files for %s (%s) into %s", len(written), codename, city, dest)
    return written


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path, help="new project directory (absent or empty)")
    parser.add_argument("--codename", required=True, help="project/dbt name, e.g. robbins")
    parser.add_argument("--city", required=True, help='display name, e.g. "Seattle, WA"')
    parser.add_argument("--db", required=True, help="DuckDB file stem, e.g. seattle")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    scaffold(args.dest, codename=args.codename, city=args.city, db=args.db)
    log.info("Next: follow docs/new-city.md from step 2 inside %s", args.dest)


if __name__ == "__main__":
    main()
