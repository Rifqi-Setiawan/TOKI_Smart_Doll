"""Architecture test proving external AI providers
cannot mutate authoritative persistence (AI-003, AI-012).
"""

import ast
from pathlib import Path


def get_imported_modules(file_path: Path) -> set[str]:
    """Parse a python source file into an AST and collect all imported module names."""
    with open(file_path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def test_providers_cannot_import_persistence_or_mutation_engines() -> None:
    """Acceptance Criterion 5: AI adapters cannot access repositories, DB, or system tools.

    Enforces AI-003 and AI-012 boundaries.

    Inspect AST of all files under:
    - app/speech/
    - app/understanding/
    - app/response/
    - app/vision/
    - app/providers/
    """
    app_root = Path(__file__).parent.parent.parent / "app"
    forbidden_prefixes = [
        "app.persistence",
        "sqlalchemy",
        "alembic",
        "subprocess",
    ]

    target_packages = ["speech", "understanding", "response", "vision", "providers"]

    scanned_files_count = 0
    for pkg in target_packages:
        pkg_dir = app_root / pkg
        if not pkg_dir.exists():
            continue

        for py_file in pkg_dir.glob("**/*.py"):
            scanned_files_count += 1
            imports = get_imported_modules(py_file)

            for imp in imports:
                for forbidden in forbidden_prefixes:
                    assert not imp.startswith(forbidden), (
                        f"Architecture violation in {py_file.name}: "
                        f"AI adapter is forbidden from importing '{imp}' (AI-003, AI-012)"
                    )

    assert scanned_files_count > 0, "Architecture guard must scan at least one provider file"
