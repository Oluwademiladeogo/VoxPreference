"""Download the pronouncing lexicons the pipeline needs (python -m pg.kb.fetch).

Pinned to the commits the knowledge base was built and tested with. CMUdict: BSD-style licence;
Britfone: MIT. Both are fetched into backend/data/resources/lexicons (git-ignored).
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

RESOURCES = Path(__file__).resolve().parents[2] / "data" / "resources"
FILES = {
    "lexicons/cmudict/cmudict.dict":
        "https://raw.githubusercontent.com/cmusphinx/cmudict/74790861f652b15e4ac49015a90074ad62a27690/cmudict.dict",
    "lexicons/cmudict/LICENSE":
        "https://raw.githubusercontent.com/cmusphinx/cmudict/74790861f652b15e4ac49015a90074ad62a27690/LICENSE",
    "lexicons/britfone/britfone.main.3.0.1.csv":
        "https://raw.githubusercontent.com/JoseLlarena/Britfone/1062be14adc96c358f2087ac5449d72130c7a6f4/britfone.main.3.0.1.csv",
    "lexicons/britfone/LICENSE.txt":
        "https://raw.githubusercontent.com/JoseLlarena/Britfone/1062be14adc96c358f2087ac5449d72130c7a6f4/LICENSE.txt",
}


def ensure(resources: Path = RESOURCES, quiet: bool = True) -> None:
    for rel, url in FILES.items():
        dest = Path(resources) / rel
        if dest.exists() and dest.stat().st_size > 0:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not quiet:
            print(f"downloading {url}", file=sys.stderr)
        tmp = dest.with_suffix(dest.suffix + ".part")
        with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
            f.write(r.read())
        tmp.replace(dest)


if __name__ == "__main__":
    ensure(quiet=False)
    print("lexicons ready in", RESOURCES / "lexicons")
