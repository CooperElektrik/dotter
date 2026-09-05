"""CLI entry point for Dotter visual novel engine."""

import argparse
import sys
from pathlib import Path

from dotter.demo import run_demo


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="dotter",
        description="Dotter visual novel engine runtime and screenplay player.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_cmd = subparsers.add_parser("run", help="Run a visual novel scene.")
    run_cmd.add_argument(
        "scene_path",
        type=Path,
        nargs="?",
        default=None,
        help="Path to .p screenplay file (defaults to demo scene).",
    )
    run_cmd.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode without window or audio device.",
    )

    demo_cmd = subparsers.add_parser("demo", help="Run the built-in demo scene.")
    demo_cmd.add_argument(
        "--headless",
        action="store_true",
        help="Run demo in headless verification mode.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI execution entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "demo"):
        headless = getattr(args, "headless", False)
        return run_demo(headless=headless)

    if args.command == "run":
        scene_path = getattr(args, "scene_path", None)
        headless = getattr(args, "headless", False)
        return run_demo(scene_path=scene_path, headless=headless)

    return 0


if __name__ == "__main__":
    sys.exit(main())
