"""Read dbt's ``target/`` build artifacts for the Sources & Methodology page.

The Dockerfile runs ``dbt build`` inside the image, so ``target/manifest.json``
and ``target/run_results.json`` are present at runtime. These pure parsers turn
them into a data-quality summary (E4) and pipeline lineage (E3) the app renders.
"""

import json
from pathlib import Path

TARGET = Path(__file__).parent / "target"

# Generic dbt test types we surface, matched against the test node's name prefix.
TEST_TYPES = ("not_null", "unique", "accepted_values", "relationships", "accepted_range")


def classify_test(unique_id: str) -> str:
    """Map a dbt test ``unique_id`` to its generic test type (or ``"other"``).

    A test id looks like ``test.groening.not_null_mart_x_col.<hash>``; the type
    is the leading token of the third dotted segment.
    """
    parts = unique_id.split(".")
    name = parts[2] if len(parts) >= 3 else unique_id
    for test_type in TEST_TYPES:
        if name.startswith(test_type):
            return test_type
    return "other"


def summarize_dbt_tests(run_results: dict) -> dict:
    """Count dbt test nodes by status and type from a ``run_results.json`` payload.

    Only ``test.*`` nodes are counted (model builds are ignored). Returns totals
    plus a per-type ``{passed, total}`` breakdown for the "N tests passing" panel.
    """
    tests = [
        r for r in run_results.get("results", [])
        if r.get("unique_id", "").startswith("test.")
    ]
    passed = sum(1 for r in tests if r.get("status") == "pass")
    failed = sum(1 for r in tests if r.get("status") in ("fail", "error"))
    by_type: dict[str, dict[str, int]] = {}
    for r in tests:
        bucket = by_type.setdefault(classify_test(r["unique_id"]), {"passed": 0, "total": 0})
        bucket["total"] += 1
        if r.get("status") == "pass":
            bucket["passed"] += 1
    return {"total": len(tests), "passed": passed, "failed": failed, "by_type": by_type}


def load_run_results() -> dict | None:
    """Read ``target/run_results.json``; ``None`` if no build has produced it yet."""
    path = TARGET / "run_results.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


# --------------------------------------------------------------------------- #
# Pipeline lineage (E3) — source -> staging -> mart -> page, from manifest.json #
# --------------------------------------------------------------------------- #
def _node_label(unique_id: str) -> str:
    """Readable label for a manifest node id.

    ``source.groening.raw.parks`` -> ``raw.parks``; ``model.groening.stg_parks``
    -> ``stg_parks``; ``exposure.groening.parks_page`` -> ``parks_page``.
    """
    parts = unique_id.split(".")
    if parts[0] == "source":
        return ".".join(parts[2:])
    return parts[2] if len(parts) >= 3 else unique_id


def node_layer(label: str) -> str:
    """Which pipeline layer a lineage node belongs to (drives its color)."""
    if label.startswith("raw."):
        return "source"
    if label.startswith("stg_"):
        return "staging"
    if label.startswith("mart_"):
        return "mart"
    return "page"


def lineage_edges(manifest: dict) -> list[tuple[str, str]]:
    """(parent, child) edges across sources, models, and exposures.

    Built from each model's and exposure's ``depends_on.nodes``. Test nodes are
    excluded — they assert quality, they aren't part of the data's flow.
    """
    edges: list[tuple[str, str]] = []
    for uid, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") != "model":
            continue
        for dep in node.get("depends_on", {}).get("nodes", []):
            edges.append((_node_label(dep), _node_label(uid)))
    for uid, exposure in manifest.get("exposures", {}).items():
        for dep in exposure.get("depends_on", {}).get("nodes", []):
            edges.append((_node_label(dep), _node_label(uid)))
    return edges


def build_lineage_dot(edges: list[tuple[str, str]]) -> str:
    """A Graphviz DOT digraph of the lineage, colored by pipeline layer."""
    colors = {
        "source": "#8a6d3b", "staging": "#4a6fa5",
        "mart": "#2e8b57", "page": "#a0522d",
    }
    layers = {}
    for parent, child in edges:
        layers[parent] = node_layer(parent)
        layers[child] = node_layer(child)
    lines = [
        "digraph lineage {",
        "  rankdir=LR;",
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10];',
    ]
    for label, layer in layers.items():
        lines.append(f'  "{label}" [fillcolor="{colors[layer]}", fontcolor="white"];')
    for parent, child in edges:
        lines.append(f'  "{parent}" -> "{child}";')
    lines.append("}")
    return "\n".join(lines)


def load_manifest() -> dict | None:
    """Read ``target/manifest.json``; ``None`` if no build has produced it yet."""
    path = TARGET / "manifest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())
