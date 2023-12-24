from pathlib import Path

from .research import Shelf

Shelf.path = str(Path(__file__).parent.parent / ".pytest_cache" / "test.db")
