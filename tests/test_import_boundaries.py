"""Architectural invariants, enforced by walking the AST rather than importing.

Two non-negotiable rules from AGENTS.md:
1. `core/` must never import from `domains/`.
2. `core/interpret/` is the only module permitted to import the model client.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "oriphim"
_CORE = _SRC / "core"
_INTERPRET = _CORE / "interpret"


def _python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _qualified_imports(path: Path) -> set[str]:
    """Every dotted name touched by an import statement in this file.

    Covers both `import a.b.c` and `from a.b import c` (recorded as both
    "a.b" and "a.b.c"), so a check for a prefix catches either form.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                names.add(node.module)
                for alias in node.names:
                    names.add(f"{node.module}.{alias.name}")
    return names


def test_core_never_imports_domains() -> None:
    violations = []
    for path in _python_files(_CORE):
        for name in _qualified_imports(path):
            if name == "oriphim.domains" or name.startswith("oriphim.domains."):
                violations.append((path, name))
    assert not violations, f"core/ modules must never import oriphim.domains: {violations}"


def test_only_interpret_imports_the_model_client() -> None:
    violations = []
    for path in _python_files(_SRC):
        if _INTERPRET in path.parents:
            continue  # core/interpret/ is allowed to import its own client
        for name in _qualified_imports(path):
            if name == "oriphim.core.interpret.client" or name.startswith(
                "oriphim.core.interpret.client."
            ):
                violations.append((path, name))
    assert not violations, (
        f"Only oriphim.core.interpret may import the model client: {violations}"
    )
