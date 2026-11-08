"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Edition:
##  09/11/2026 by Tsukini

File Name:
##  render.py

File Description:
##  Render the README catalog and the gh-pages site
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

##### Import #####
# Import that can't be in the try
from catalog import CatalogError, load_config, version_key, urls, dnf_section, apt_line, pacman_section
from const import RETURN, ERROR, FILES, VALUES, MARKERS
from sys import exit, stderr

# Import that can be checked
try:
    from datetime import datetime, timezone # Used for the date of the check
    from urllib.parse import quote # Used for the badge urls
    from pathlib import Path # Used for the output files
    from html import escape # Used to escape the generated html
    import argparse # Used for the arguments
    import shutil # Used to copy the signing key
    import json # Used to read packages.json and write index.json / badges
    import re # Used to fill the templates
except ImportError as e:
    stderr.write(f"Import Error ({__file__}): {e}\n")
    exit(255)

# Check if the program is call and not imported
if __name__ != "__main__":
    stderr.write(f"The {__file__} can only be executed and not imported!\n")
    exit(ERROR.FATAL)

##### Const #####
LANG_SWITCH = """<div class="lang-switch" role="group" aria-label="Language" data-i18n-aria-label>
    <button type="button" data-set-lang="en" class="on">EN</button>
    <button type="button" data-set-lang="fr">FR</button>
  </div>
  <span class="divider" aria-hidden="true"></span>"""
GITHUB_LINK = """<a class="icon-btn" href="https://github.com/{owner}/my-universe" aria-label="GitHub repository" data-i18n-aria-label title="GitHub repository" data-i18n-title><svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg></a>"""
DISTROS = {"rpm": ("Fedora", "sudo dnf install"), "deb": ("Debian / Ubuntu", "sudo apt install"), "arch": ("Arch", "sudo pacman -S")}
COLORS = {"hand-made": "2f5bd3", "ai-made": "1f7a4a", "version": "2f5bd3", "pre": "a8540a", "info": "5d636e"}

##### Tools #####
def read(path: Path) -> str: # Content of a text file
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write(path: Path, content: str) -> None: # Write a text file (parents created)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def lang(en: str, fr: str) -> str: # Bilingual text of the site (already escaped html)
    return f'<span data-lang="en">{en}</span><span data-lang="fr">{fr}</span>'

def short(version: str) -> str: # 4.2.0-1 -> 4.2.0 (the release number of a stable package says nothing)
    return version.split("-")[0] if version else ""

def has_pre(entry: dict) -> bool: # A pre-release newer than the stable version
    return bool(entry["pre"]) and (not entry["version"] or version_key(entry["pre"]) > version_key(entry["version"]))

def badge_url(site: str, name: str) -> str: # shields.io endpoint badge of the site
    return f"https://img.shields.io/endpoint?url={quote(f'{site}/badges/{name}.json', safe='')}"

def badges(catalog: dict, checked: str) -> dict[str, dict]: # Every badge of the site: file name -> shields.io payload
    entries = catalog["sources"]
    out = {
        "packages": ("packages", str(len(entries)), COLORS["version"]),
        "updated": ("last update", catalog["updated"], COLORS["info"]),
        "checked": ("checked", checked[:10], COLORS["info"]),
    }
    for category in VALUES.CATEGORIES:
        out[category] = (category, str(sum(e["category"] == category for e in entries)), COLORS[category])
    for entry in entries:
        out[entry["name"]] = (entry["name"], short(entry["version"]) or "none", COLORS["version"])
        if has_pre(entry):
            out[f"{entry['name']}-pre"] = (f"{entry['name']}-pre", entry["pre"], COLORS["pre"])
    return {name: {"schemaVersion": 1, "label": label, "message": message, "color": color} for name, (label, message, color) in out.items()}

def replace_between(text: str, start: str, end: str, content: str) -> str: # Replace the generated part of the README
    if start not in text or end not in text:
        raise CatalogError(f"missing markers {start} / {end} in {FILES.README}")
    head, rest = text.split(start, 1)
    return f"{head}{start}\n{content}\n{end}{rest.split(end, 1)[1]}"

##### Readme #####
def readme_badges(catalog: dict, owner: str) -> str: # Global badges of the README
    site = catalog["site"]
    items = [("Packages", "packages"), ("Last update", "updated"), ("Checked", "checked")] + [(c, c) for c in VALUES.CATEGORIES]
    line = " ".join(f"![{label}]({badge_url(site, name)})" for label, name in items)
    return f"{line} ![Update](https://github.com/{owner}/my-universe/actions/workflows/update.yml/badge.svg)"

def readme_catalog(catalog: dict) -> str: # Tables of the packages, by category
    out: list[str] = []
    for category in VALUES.CATEGORIES:
        entries = [e for e in catalog["sources"] if e["category"] == category]
        out.append(f"### {category}\n")
        if not entries:
            out.append("> [!NOTE]\n> No public package in this category yet.\n")
            continue
        out.append("| Name + Link | Version | Pre-release | Formats | Release | Last Update | Content |")
        out.append("| ----------- | ------- | ----------- | ------- | ------- | ----------- | ------- |")
        for e in entries:
            pre = f"`{e['pre']}`" if has_pre(e) else "-"
            release = f"[{e['release']['tag']}]({e['release']['url']})" if e.get("release") else "-"
            formats = " ".join(f"`{f}`" for f in VALUES.FORMATS if f in e["formats"]) or "-"
            commit = f"![](https://img.shields.io/github/last-commit/{catalog['owner']}/{e['repo']})"
            out.append(f"| [{e['name']}]({e['repository']}) | `{short(e['version']) or '-'}` | {pre} | {formats} | {release} | {commit} | {e['summary']['en']} |")
        out.append("")
    return "\n".join(out).rstrip()

##### Site #####
def card(settings: dict, entry: dict) -> str: # Card of one package
    name = escape(entry["name"])
    pre = has_pre(entry)
    stable_attr = ' data-channel="stable"' if pre else ""
    head = f'<span class="badge"{stable_attr}>{escape(short(entry["version"]) or "no stable")}</span>'
    if pre:
        head += f'<span class="badge pre" data-channel="pre">{escape(entry["pre"])} pre</span>'

    # Install commands, one tab per format (+ the CLI)
    tabs = [f for f in VALUES.FORMATS if f in entry["formats"]] + ["cli"]
    group = f"cmd-{name}"
    bar = "".join(f'<button type="button" data-tab="{t}">{DISTROS[t][0] if t in DISTROS else "universe"}</button>' for t in tabs)
    panels = ""
    for tab in tabs:
        stable_cmd = f"{DISTROS[tab][1]} {entry['main']}" if tab in DISTROS else f"./universe install {entry['name']}"
        pre_cmd = f"{DISTROS[tab][1]} {entry['main']}{VALUES.PRE_SUFFIX}" if tab in DISTROS else f"./universe install {entry['name']} --pre"
        blocks = f'<pre data-title="bash"{stable_attr}><code>{escape(stable_cmd)}</code></pre>'
        if pre:
            blocks += f'<pre data-title="bash" data-channel="pre"><code>{escape(pre_cmd)}</code></pre>'
        panels += f'<div class="ctab-panel" data-tabs="{group}" data-tab="{tab}">{blocks}</div>'

    # Links and sub-packages
    links = urls(settings, entry)
    items = [(links["repository"], lang("Repository", "Dépôt"))]
    if links.get("docs"):
        items.append((links["docs"], "Docs"))
    if links.get("release"):
        items.append((links["release"], f"Release {escape(entry['release']['tag'])}"))
    if links.get("pages"):
        items.append((links["pages"], lang("Package repository", "Dépôt de paquets")))
    link_row = "".join(f'<a href="{escape(url)}">{label}</a>' for url, label in items)
    rows = "".join(f'<tr><td><code>{escape(p["name"])}</code></td><td><code>{escape(p["version"])}</code></td><td>{escape(p["description"])}</td></tr>' for p in entry["packages"])
    count = len(entry["packages"])
    table = (f'<details class="more"><summary>{lang(f"{count} packages", f"{count} paquets")}</summary><div>'
             f'<div class="table-wrap" role="region" tabindex="0" aria-label="Packages of {name}"><table><thead><tr>'
             f'<th scope="col">{lang("Package", "Paquet")}</th><th scope="col">Version</th><th scope="col">Description</th>'
             f'</tr></thead><tbody>{rows}</tbody></table></div></div></details>') if count else ""
    formats = " ".join(f for f in VALUES.FORMATS if f in entry["formats"])
    fmts = "".join(f'<span class="pill">{f}</span>' for f in formats.split())
    search = " ".join([entry["name"], entry["repo"], entry["main"], entry["category"], formats, entry["summary"]["en"], entry["summary"]["fr"]] + [p["name"] for p in entry["packages"]])
    return (f'<article class="pkg" id="pkg-{name}" data-category="{escape(entry["category"])}" data-formats="{formats}" data-search="{escape(search)}">'
            f'<div class="pkg-head"><h4><a href="#pkg-{name}">{name}</a></h4><span class="pill cat-{escape(entry["category"])}">{escape(entry["category"])}</span>'
            f'<span class="spacer"></span>{head}</div>'
            f'<p class="sum">{lang(escape(entry["summary"]["en"]), escape(entry["summary"]["fr"]))}</p>'
            f'<div class="fmts">{fmts}</div>'
            f'<div class="ctabs" data-tabs="{group}" data-distro>{bar}</div>{panels}'
            f'<div class="links">{link_row}</div>{table}'
            f'<div class="page-meta"><span>{lang("Updated", "Mis à jour")} {escape(entry["updated"])}</span></div></article>')

def groups(settings: dict, catalog: dict) -> str: # One group of cards per category
    out = ""
    for category in VALUES.CATEGORIES:
        entries = [e for e in catalog["sources"] if e["category"] == category]
        cards = "".join(card(settings, e) for e in entries) or f'<p class="none-yet">{lang("No public package in this category yet.", "Pas encore de paquet public dans cette catégorie.")}</p>'
        out += (f'<div class="cat-group" data-category="{category}"><h3 id="{category}"><span class="pill cat-{category}">{category}</span>'
                f'<span class="count">{len(entries)}</span></h3><div class="pkgs">{cards}</div></div>')
    return out

def search_index(catalog: dict) -> str: # window.DOCS_INDEX of the site search (both languages)
    entries: list[dict] = []
    for e in catalog["sources"]:
        for code in ("en", "fr"):
            text = " ".join([e["repo"], e["main"], e["category"], " ".join(e["formats"])] + [p["name"] for p in e["packages"]])
            entries.append({"k": e["category"], "l": code, "t": e["name"], "d": e["summary"][code], "u": f"#pkg-{e['name']}", "x": text})
    pages = [("install", "Get everything", "Tout récupérer", "install.sh curl wget one line setup"),
             ("manual", "By hand", "À la main", "universe.repo universe.list universe.conf dnf apt pacman"),
             ("cli", "With the CLI", "Avec la CLI", "universe setup install update info outdated list mirror links"),
             ("files", "Repository files", "Fichiers du dépôt", "universe.repo universe.list universe.conf index.json key"),
             ("badges", "Badges", "Badges", "shields.io endpoint markdown readme")]
    for anchor, en, fr, text in pages:
        entries.append({"k": "page", "l": "en", "t": en, "d": "", "u": f"#{anchor}", "x": text})
        entries.append({"k": "page", "l": "fr", "t": fr, "d": "", "u": f"#{anchor}", "x": text})
    return f"<script>window.DOCS_INDEX = {json.dumps({'entries': entries}, ensure_ascii=False)};</script>"

def badge_rows(catalog: dict, payloads: dict[str, dict]) -> str: # Rows of the badges table
    return "".join(f'<tr><td><code>{escape(p["label"])}: {escape(p["message"])}</code></td><td><a href="badges/{escape(n)}.json"><code>{escape(n)}.json</code></a></td></tr>'
                   for n, p in payloads.items())

def badge_markdown(catalog: dict, payloads: dict[str, dict]) -> str: # Markdown of every badge, one per line
    return escape("\n".join(f"![{p['label']}]({badge_url(catalog['site'], n)})" for n, p in payloads.items()))

def build_page(settings: dict, catalog: dict, checked: str, payloads: dict[str, dict]) -> str: # index.html, self-contained
    entries = catalog["sources"]
    stats = " ".join(f'<span><span class="pill cat-{c}">{c}</span> <b>{sum(e["category"] == c for e in entries)}</b></span>' for c in VALUES.CATEGORIES)
    buttons = "".join(f'<button type="button" data-value="{c}" aria-pressed="false">{c}</button>' for c in VALUES.CATEGORIES)
    values = {"COUNT": str(len(entries)), "UPDATED": catalog["updated"], "CHECKED": checked.replace("T", " ")[:16] + " UTC",
              "CATEGORY_STATS": stats, "CATEGORY_BUTTONS": buttons, "SITE": catalog["site"], "KEY": catalog["key"],
              "FINGERPRINT": settings.get("fingerprint", ""), "OWNER": catalog["owner"], "GROUPS": groups(settings, catalog),
              "BADGES": badge_rows(catalog, payloads), "BADGES_MD": badge_markdown(catalog, payloads), "INDEX": search_index(catalog)}
    body = re.sub(r"@@([A-Z_]+)@@", lambda m: values[m.group(1)], read(FILES.SITE / "home.html")).strip()
    body = body.replace("<main>", '<main id="main" tabindex="-1">', 1) # target of the skip link (RGAA 12.7)

    # html-style page + better-html-style layer + the catalog
    vendor = FILES.VENDOR
    page = read(vendor / "page.html")
    page = page.replace("/*@STYLE@*/", "\n".join(read(vendor / f) for f in ("style.css", "site.css")) + read(FILES.SITE / "universe.css"))
    page = page.replace("/*@SCRIPT@*/", "\n".join(read(vendor / f) for f in ("base.js", "site.js")) + read(FILES.SITE / "universe.js"))
    page = page.replace("<!--@ACTIONS@-->", LANG_SWITCH + read(vendor / "search.html") + GITHUB_LINK.format(owner=catalog["owner"]))
    page = page.replace("<!--@BODY@-->", body)
    page = page.replace("<html ", '<html data-channel-view="stable" ', 1)
    page = page.replace('<div class="layout" id="top">', '<div class="layout wide" id="top">', 1)
    page = re.sub(r'<svg class="logo".*?</svg>', lambda m: read(FILES.SITE / "logo.svg").strip(), page, count=1, flags=re.S)
    footer = (f'my-universe · {lang("catalog checked", "catalogue vérifié le")} {escape(values["CHECKED"])} · '
              f'<a href="https://github.com/{catalog["owner"]}/my-universe">GitHub</a>')
    fill = {"STORAGE_KEY": "my-universe", "TITLE": "my-universe", "PROJECT": "my-universe", "VERSION": "", "FOOTER": footer}
    page = re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: fill.get(m.group(1), m.group(0)), page)
    left = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}|@@[A-Z_]+@@", page)))
    if left:
        raise CatalogError(f"unfilled placeholders in the site: {', '.join(left)}")
    return page

def render_site(settings: dict, catalog: dict, out: Path, checked: str) -> None: # Every file of the gh-pages branch
    site, key = catalog["site"], catalog["key"]
    key_url = f"{site}/{key}"
    entries = [e for e in catalog["sources"] if not e.get("private") and e.get("pages")]
    payloads = badges(catalog, checked)
    out.mkdir(parents=True, exist_ok=True)
    write(out / "index.html", build_page(settings, catalog, checked, payloads))
    write(out / ".nojekyll", "")
    write(out / "index.json", json.dumps({**catalog, "checked": checked}, indent=2, ensure_ascii=False) + "\n")
    shutil.copyfile(FILES.KEY, out / key)
    for name, payload in payloads.items():
        write(out / "badges" / f"{name}.json", json.dumps(payload) + "\n")

    # Aggregated repository files
    head = f"# my-universe: every package repository of {site}\n# Generated on {checked[:10]}, the packages stay in the gh-pages of each project\n\n"
    write(out / "universe.repo", head + "\n".join(dnf_section(e, e["pages"], key_url) for e in entries if "rpm" in e["formats"]))
    write(out / "universe.list", head + "".join(apt_line(e, e["pages"], "/etc/apt/keyrings/universe.gpg") for e in entries if "deb" in e["formats"]))
    write(out / "universe.conf", head + "\n".join(pacman_section(e, e["pages"]) for e in entries if "arch" in e["formats"]))
    lines = "\n".join(f'    "{e["name"]}|{e["pages"]}|{" ".join(f for f in VALUES.FORMATS if f in e["formats"])}|{e["formats"].get("arch", {}).get("db", "")}"' for e in entries)
    script = read(FILES.SITE / "install.sh").replace("@@SOURCES@@", lines)
    script = script.replace("@@SITE@@", site).replace("@@KEY@@", key).replace("@@FINGERPRINT@@", settings.get("fingerprint", ""))
    write(out / "install.sh", script)
    print(f"✓ site rendered in {out} ({len(entries)} packages, {len(payloads)} badges)")

##### Program #####
parser = argparse.ArgumentParser(description="Render the catalog of packages.json in the README and in the gh-pages site")
parser.add_argument("--packages", type=Path, default=FILES.PACKAGES, help="catalog to render (default: packages.json)")
parser.add_argument("--readme", type=Path, nargs="?", const=FILES.README, help="update the generated parts of the README")
parser.add_argument("--site", type=Path, help="output folder of the site (ex: dist)")
parser.add_argument("--checked", default="", help="date of the check (default: now, UTC)")
args = parser.parse_args()
if args.readme is None and args.site is None:
    parser.error("nothing to render: give --readme and / or --site")

try:
    settings, _ = load_config()
    with open(args.packages, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    checked = args.checked or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if args.readme is not None:
        text = read(args.readme)
        text = replace_between(text, MARKERS.BADGES_START, MARKERS.BADGES_END, readme_badges(catalog, catalog["owner"]))
        text = replace_between(text, MARKERS.CATALOG_START, MARKERS.CATALOG_END, readme_catalog(catalog))
        write(args.readme, text)
        print(f"✓ {args.readme} rendered")
    if args.site is not None:
        render_site(settings, catalog, args.site, checked)
except (OSError, json.JSONDecodeError, CatalogError) as e:
    stderr.write(f"Error: {e}\n")
    exit(ERROR.ACTION)
exit(RETURN.OK)
