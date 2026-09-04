import sys
from pathlib import Path

MAX_FILE_LINES = 350
WARN_FILE_LINES = 300
MAX_CLI_LINES = 100

CLI_NAMES = {"cli.py", "__main__.py"}


def is_cli_file(path: Path) -> bool:
    """Determine if a file is considered a CLI entry point."""
    if path.name in CLI_NAMES:
        return True
    return "cli" in path.parts and path.suffix == ".py"


def count_lines(path: Path) -> int:
    """Count total lines in a file."""
    try:
        content = path.read_text(encoding="utf-8")
        return len(content.splitlines())
    except UnicodeDecodeError:
        return 0


def check_file(path: Path) -> tuple[list[str], list[str]]:
    """Check a single python file against line budgets."""
    errors: list[str] = []
    warnings: list[str] = []
    line_count = count_lines(path)

    if line_count > MAX_FILE_LINES:
        errors.append(f"ERROR: {path} has {line_count} lines (exceeds {MAX_FILE_LINES} limit)")
    elif line_count >= WARN_FILE_LINES:
        warn_msg = (
            f"WARNING: {path} has {line_count} lines "
            f"(approaching {WARN_FILE_LINES} decomposition threshold)"
        )
        warnings.append(warn_msg)

    if is_cli_file(path) and line_count > MAX_CLI_LINES:
        errors.append(
            f"ERROR: CLI file {path} has {line_count} lines (exceeds CLI limit of {MAX_CLI_LINES})"
        )

    return errors, warnings


def main() -> int:
    """Scan project directories and enforce line budgets."""
    root = Path(__file__).resolve().parent.parent
    scan_dirs = [root / "src", root / "tests", root / "scripts"]

    all_errors: list[str] = []
    all_warnings: list[str] = []

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        for py_file in scan_dir.rglob("*.py"):
            errors, warnings = check_file(py_file)
            all_errors.extend(errors)
            all_warnings.extend(warnings)

    for warning in all_warnings:
        print(warning, file=sys.stderr)

    for error in all_errors:
        print(error, file=sys.stderr)

    if all_errors:
        print(f"\nBudget verification failed with {len(all_errors)} error(s).", file=sys.stderr)
        return 1

    print(f"Budget verification passed. Checked files across {len(scan_dirs)} directories.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
