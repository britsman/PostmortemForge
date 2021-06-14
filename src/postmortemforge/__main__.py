"""Module entry point so `python -m postmortemforge` works."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
