"""Validate local Markdown links, image targets, and Mermaid fence balance."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def validate_docs() -> list[str]:
    errors: list[str] = []
    markdown = [ROOT / "README.md", ROOT / "CHANGELOG.md", *sorted((ROOT / "docs").rglob("*.md"))]
    for path in markdown:
        if not path.exists():
            errors.append(f"missing documentation file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        if text.count("```") % 2:
            errors.append(f"{path.relative_to(ROOT)}: unbalanced code fences")
        for raw in LINK.findall(text):
            target = raw.strip().split()[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            file_part = unquote(target.split("#", 1)[0])
            if file_part and not (path.parent / file_part).resolve().exists():
                errors.append(f"{path.relative_to(ROOT)}: broken link {target}")
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    if architecture.count("```mermaid") < 10:
        errors.append("docs/architecture.md: expected at least ten Mermaid diagrams")
    return errors


def main() -> int:
    errors = validate_docs()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Documentation links, images, fences, and diagram inventory are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

