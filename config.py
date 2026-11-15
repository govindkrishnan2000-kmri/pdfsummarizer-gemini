"""Environment loading shared by the app and the summarizer.

``.env`` is tracked and holds non-secret defaults. ``.env.local`` is
gitignored and overrides it, so real keys stay on the machine.
"""

from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent


def load_env() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local", override=True)
