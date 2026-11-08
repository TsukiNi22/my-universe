"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Edition:
##  09/11/2026 by Tsukini

File Name:
##  update.py

File Description:
##  Update packages.json from the package repositories
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

##### Import #####
# Import that can't be in the try
from catalog import CatalogError, HttpSource, load_config, build_entry
from const import RETURN, ERROR, FILES
from sys import exit, stderr

# Import that can be checked
try:
    from datetime import datetime, timezone # Used for the date of the changes
    from pathlib import Path # Used for the output file
    from os import environ # Used for the GitHub Actions output
    import argparse # Used for the arguments
    import json # Used to read / write packages.json
except ImportError as e:
    stderr.write(f"Import Error ({__file__}): {e}\n")
    exit(255)

# Check if the program is call and not imported
if __name__ != "__main__":
    stderr.write(f"The {__file__} can only be executed and not imported!\n")
    exit(ERROR.FATAL)

##### Tools #####
def changes(previous: dict, catalog: dict) -> list[str]: # "name version" of every source whose versions changed
    before = {e["name"]: (e.get("version"), e.get("pre")) for e in previous.get("sources", [])}
    out: list[str] = []
    for entry in catalog["sources"]:
        if before.get(entry["name"]) != (entry["version"], entry["pre"]):
            out.append(f"{entry['name']} {entry['version'] or entry['pre'] or 'none'}")
    removed = set(before) - {e["name"] for e in catalog["sources"]}
    return out + [f"{name} removed" for name in sorted(removed)]

##### Program #####
parser = argparse.ArgumentParser(description="Read every public package repository of sources.toml and update packages.json")
parser.add_argument("-o", "--output", type=Path, default=FILES.PACKAGES, help="catalog to update (default: packages.json)")
parser.add_argument("--github-output", action="store_true", help="write changed= / summary= in $GITHUB_OUTPUT")
args = parser.parse_args()

# Read the sources and the previous catalog
try:
    settings, sources = load_config()
except CatalogError as e:
    stderr.write(f"Error: {e}\n")
    exit(ERROR.FATAL)
previous: dict = {}
if args.output.is_file():
    try:
        with open(args.output, "r", encoding="utf-8") as f:
            previous = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        stderr.write(f"Warning: previous catalog ignored ({args.output}: {e})\n")
old = {e["name"]: e for e in previous.get("sources", [])}
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Read every package repository (a failing one keeps its previous entry)
entries: list[dict] = []
failed = 0
for source in sources:
    try:
        entry = build_entry(settings, source, HttpSource(settings, source), old.get(source["name"]), today)
    except CatalogError as e:
        failed += 1
        print(f"::warning title=Source {source['name']}::{e}")
        if source["name"] in old:
            entries.append(old[source["name"]])
        continue
    entries.append(entry)
    pre = f" (pre {entry['pre']})" if entry["pre"] else ""
    print(f"✓ {entry['name']} {entry['version'] or 'no stable version'}{pre}, {', '.join(entry['formats']) or 'no format'}")
if failed == len(sources) and not entries:
    stderr.write("Error: no package repository could be read\n")
    exit(ERROR.ACTION)

# Write the catalog when it changed
catalog = {
    "owner": settings["owner"],
    "pages": settings["pages"],
    "site": settings["site"],
    "key": settings["key"],
    "updated": max((e["updated"] for e in entries), default=today),
    "sources": entries,
}
changed = catalog != previous
summary = ", ".join(changes(previous, catalog))
if changed:
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        f.write("\n")
print(f"{'✓ catalog updated' if changed else '✓ catalog unchanged'}{f': {summary}' if summary else ''}")
if args.github_output and environ.get("GITHUB_OUTPUT"):
    with open(environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        f.write(f"changed={'true' if changed else 'false'}\nsummary={summary or 'catalog'}\n")
exit(RETURN.OK)
