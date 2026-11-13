"""Command line: python -m kavach_pack (or ``kavach-pack`` once installed)."""

from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path

from .documents import build
from .form import FormError, load
from .gaps import blockers, check
from .tiering import TIER_NAMES, factors, tier

TEMPLATE = "system-template.toml"


def _template_text() -> str:
    return resources.files("kavach_pack").joinpath(TEMPLATE).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="kavach-pack", description="Governance pack for an AI system, from one form.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new", help="write a blank system form to fill in")
    n.add_argument("path", nargs="?", default="system.toml")
    b = sub.add_parser("build", help="write the governance pack for one or more systems")
    b.add_argument("forms", nargs="+")
    b.add_argument("--out", default="governance-pack")
    c = sub.add_parser("check", help="show tier and gaps; exit 1 if there are blockers (for CI)")
    c.add_argument("forms", nargs="+")
    sub.add_parser("demo", help="build packs for the bundled example systems")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "new":
            path = Path(args.path)
            if path.exists():
                print(f"{path} already exists; not overwriting it.", file=sys.stderr)
                return 2
            path.write_text(_template_text(), encoding="utf-8")
            print(f"Wrote {path}. Fill it in, then run: kavach-pack build {path}")
            return 0

        if args.cmd == "build":
            for form in args.forms:
                s = load(form)
                folder = build(s, args.out)
                print(f"{s.name}: {TIER_NAMES[tier(s)]} tier, {len(blockers(check(s)))} blocker(s). Pack: {folder}")
            return 0

        if args.cmd == "check":
            failed = False
            for form in args.forms:
                s = load(form)
                gaps = check(s)
                blk = blockers(gaps)
                failed |= bool(blk)
                print(f"\n{s.name}: {TIER_NAMES[tier(s)]} tier")
                for f in factors(s):
                    print(f"  {f.score}  {f.name}: {f.reason}")
                for g in gaps:
                    print(f"  [{g.severity.upper()}] {g.id}: {g.message}")
                print(f"  {len(blk)} blocker(s), {len(gaps) - len(blk)} warning(s)")
            return 1 if failed else 0

        if args.cmd == "demo":
            examples = resources.files("kavach_pack").joinpath("examples")
            for name in ("loan-document-reader.toml", "bank-support-assistant.toml", "meeting-summary.toml"):
                s = load(Path(str(examples.joinpath(name))))
                folder = build(s, "kavach-pack-demo")
                print(f"{s.name}: {TIER_NAMES[tier(s)]} tier, {len(blockers(check(s)))} blocker(s). Pack: {folder}")
            print("\nOpen kavach-pack-demo/<system>/00-summary.md to start.")
            return 0
    except FormError as e:
        print(f"Form problem: {e}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
