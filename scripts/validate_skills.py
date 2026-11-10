#!/usr/bin/env python3
"""Validate this repository's plain-scalar skill metadata and local links."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    errors = []
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    for path in skills:
        text = path.read_text()
        match = re.match(r"\A---\nname: ([a-z0-9]+(?:-[a-z0-9]+)*)\ndescription: ([^\n]+)\n---\n", text)
        if not match or match[1] != path.parent.name:
            errors.append(f"{path.relative_to(ROOT)}: invalid name/frontmatter")
        elif len(match[1]) > 64 or len(match[2]) > 1024 or any(c in match[2] for c in "<>"):
            errors.append(f"{path.relative_to(ROOT)}: invalid metadata")
        if "[TODO:" in text:
            errors.append(f"{path.relative_to(ROOT)}: unfinished scaffold")
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in link and not (path.parent / link.split("#")[0]).resolve().is_file():
                errors.append(f"{path.relative_to(ROOT)}: missing local reference {link}")
    if not skills:
        errors.append("no skills found")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Validated {len(skills)} skills and their local references.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
