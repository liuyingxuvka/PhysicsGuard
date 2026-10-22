from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_python_sources_have_at_most_two_consecutive_blank_lines() -> None:
    violations: list[str] = []
    for directory in ("src", "tests", "scripts", "examples", ".flowguard/models"):
        for path in sorted((ROOT / directory).rglob("*.py")):
            blank_lines = 0
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                blank_lines = blank_lines + 1 if not line.strip() else 0
                if blank_lines == 3:
                    violations.append(f"{path.relative_to(ROOT).as_posix()}:{number - 2}")
    assert not violations, "Three or more consecutive blank lines:\n" + "\n".join(violations)
