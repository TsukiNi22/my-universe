"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Edition:
##  09/11/2026 by Tsukini

File Name:
##  catalog.py

File Description:
##  Read the package repositories (gh-pages) and build the catalog
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

##### Import #####
# Import that can't be in the try
from const import FILES, VALUES
from sys import exit, stderr

# Import that can be checked
try:
    from urllib.request import Request, urlopen # Used for the http requests
    from urllib.error import HTTPError, URLError # Used to tell a missing file from a network error
    from xml.etree import ElementTree # Used to read the rpm metadata
    from pathlib import Path # Used for the local mirror
    from os import environ # Used for the GitHub token
    from io import BytesIO # Used to open the archives in memory
    import tarfile # Used to read the arch databases
    import tomllib # Used to read sources.toml / private.toml
    import json # Used for the GitHub API answers
    import gzip # Used for the compressed rpm metadata
    import lzma # Used for the xz rpm metadata
    import bz2 # Used for the bzip2 rpm metadata
    import re # Used to detect the formats from the paths
except ImportError as e:
    stderr.write(f"Import Error ({__file__}): {e}\n")
    exit(255)

# Check if the module is imported and not executed
if __name__ == "__main__":
    stderr.write(f"The {__file__} can only be imported and not executed!\n")
    exit(255)

##### Class #####
class CatalogError(Exception):
    """
        Error while reading the sources or a package repository
    """

class HttpSource():
    """
        Package repository read from GitHub Pages (files) and the GitHub API (tree, release)
    """
    def __init__(self, settings: dict, source: dict) -> None:
        self._owner = settings["owner"]
        self._repo = source["repo"]
        self.base = f"{settings['pages']}/{source['repo']}"
        self._token = environ.get("GITHUB_TOKEN") or environ.get("GH_TOKEN") or ""

    def _api(self, path: str) -> dict | None: # GitHub API call, None when the resource does not exist
        data = http_get(f"https://api.github.com/repos/{self._owner}/{self._repo}/{path}", self._token, "application/vnd.github+json")
        return json.loads(data) if data is not None else None

    def files(self) -> list[str]:
        """Every path of the gh-pages branch"""
        tree = self._api("git/trees/gh-pages?recursive=1")
        if tree is None:
            raise CatalogError(f"no gh-pages branch in {self._owner}/{self._repo}")
        return [node["path"] for node in tree.get("tree", []) if node.get("type") == "blob"]

    def read(self, path: str) -> bytes | None:
        """Content of a file of the package repository"""
        return http_get(f"{self.base}/{path}")

    def release(self) -> dict | None:
        """Latest GitHub release of the repository"""
        release = self._api("releases/latest")
        if release is None:
            return None
        return {"tag": release.get("tag_name", ""), "date": (release.get("published_at") or "")[:10], "url": release.get("html_url", "")}

class LocalSource():
    """
        Package repository read from the local mirror (clone of the gh-pages branch)
    """
    def __init__(self, source: dict, root: Path = FILES.MIRROR) -> None:
        self.path = root / source["repo"]
        self.base = f"file://{self.path}"

    def files(self) -> list[str]:
        """Every path of the mirror"""
        if not self.path.is_dir():
            raise CatalogError(f"no mirror of {self.path.name} (run: universe mirror)")
        return [str(p.relative_to(self.path)) for p in self.path.rglob("*") if p.is_file() and ".git" not in p.parts]

    def read(self, path: str) -> bytes | None:
        """Content of a file of the mirror"""
        file = self.path / path
        return file.read_bytes() if file.is_file() else None

    def release(self) -> dict | None:
        """No release information for a mirror"""
        return None

##### Tools #####
def http_get(url: str, token: str = "", accept: str = "") -> bytes | None: # GET, None on a 404
    request = Request(url, headers={"User-Agent": VALUES.USER_AGENT})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    if accept:
        request.add_header("Accept", accept)
    try:
        with urlopen(request, timeout=VALUES.TIMEOUT) as answer:
            return answer.read()
    except HTTPError as e:
        if e.code == 404:
            return None
        raise CatalogError(f"{url}: http {e.code}") from e
    except (URLError, TimeoutError) as e:
        raise CatalogError(f"{url}: {e}") from e

def load_config(private: bool = False) -> tuple[dict, list[dict]]: # Settings + sources (private.toml added on request)
    files = [FILES.SOURCES] + ([FILES.PRIVATE] if private and FILES.PRIVATE.is_file() else [])
    settings: dict = {}
    sources: list[dict] = []
    for file in files:
        try:
            with open(file, "rb") as f:
                data = tomllib.load(f)
        except (OSError, tomllib.TOMLDecodeError) as e:
            raise CatalogError(f"cannot read {file}: {e}") from e
        settings = settings or data.get("universe", {})
        for source in data.get("source", []):
            source["private"] = file == FILES.PRIVATE
            sources.append(source)

    # Check the content
    for key in ("owner", "pages", "site", "key"):
        if key not in settings:
            raise CatalogError(f"missing '{key}' in the [universe] table of {FILES.SOURCES}")
    names: set[str] = set()
    for source in sources:
        for key in ("name", "repo", "category", "main"):
            if key not in source:
                raise CatalogError(f"missing '{key}' in a [[source]] ({source.get('name', '?')})")
        if source["category"] not in VALUES.CATEGORIES:
            raise CatalogError(f"unknown category '{source['category']}' for {source['name']} ({', '.join(VALUES.CATEGORIES)})")
        if source["name"] in names:
            raise CatalogError(f"source '{source['name']}' defined twice")
        names.add(source["name"])
    return settings, sources

def version_key(version: str) -> tuple: # Comparable key of a version (epoch and dist suffix ignored)
    version = strip_version(version)
    return tuple((1, int(part)) if part.isdigit() else (0, part) for part in re.findall(r"\d+|[a-zA-Z]+", version))

def strip_version(version: str) -> str: # 1:4.2.0-1.fc44 -> 4.2.0-1
    version = re.sub(r"^\d+:", "", version.strip())
    return re.sub(r"\.(fc|el|mga)\d+.*$", "", version)

def detect_formats(paths: list[str]) -> dict: # Formats of a package repository from the paths of its files
    formats: dict = {}
    rpm = [m.groups() for m in (re.match(r"^fedora/(\d+)/([^/]+)/repodata/repomd\.xml$", p) for p in paths) if m]
    deb = [m.group(1) for m in (re.match(rf"^debian/dists/{VALUES.DEB_SUITE}/main/binary-([^/]+)/Packages$", p) for p in paths) if m]
    arch = [m.groups() for m in (re.match(r"^arch/([^/]+)/([^/]+)\.db$", p) for p in paths) if m]
    if rpm:
        formats["rpm"] = {"releases": sorted({r for r, _ in rpm}, key=int), "arches": sorted({a for _, a in rpm})}
    if deb:
        formats["deb"] = {"arches": sorted(set(deb))}
    if arch:
        formats["arch"] = {"db": arch[0][1], "arches": sorted({a for a, _ in arch})}
    return formats

def parse_deb(text: str) -> list[dict]: # Packages index of a debian repository
    packages: list[dict] = []
    for stanza in re.split(r"\n\s*\n", text):
        fields: dict[str, str] = {}
        last = ""
        for line in stanza.splitlines():
            if line[:1] in (" ", "\t") and last: # continuation of a multi-line field
                continue
            if ":" in line:
                last, value = line.split(":", 1)
                fields[last] = value.strip()
        if "Package" in fields and "Version" in fields:
            packages.append({"name": fields["Package"], "version": fields["Version"], "description": fields.get("Description", "")})
    return packages

def decompress(data: bytes) -> bytes: # gzip / xz / bzip2 / zstd (createrepo_c default) data, as is otherwise
    if data[:2] == b"\x1f\x8b":
        return gzip.decompress(data)
    if data[:6] == b"\xfd7zXZ\x00":
        return lzma.decompress(data)
    if data[:3] == b"BZh":
        return bz2.decompress(data)
    if data[:4] == b"\x28\xb5\x2f\xfd":
        try:
            from compression import zstd # Python 3.14+ only
        except ImportError as e:
            raise CatalogError("zstd metadata needs Python 3.14+ (compression.zstd)") from e
        return zstd.decompress(data)
    return data

def parse_rpm(source: HttpSource | LocalSource, base: str) -> list[dict]: # primary.xml of a rpm repository
    ns = {"repo": "http://linux.duke.edu/metadata/repo", "common": "http://linux.duke.edu/metadata/common"}
    repomd = source.read(f"{base}/repodata/repomd.xml")
    if repomd is None:
        return []
    location = ElementTree.fromstring(repomd).find("repo:data[@type='primary']/repo:location", ns)
    if location is None:
        return []
    primary = source.read(f"{base}/{location.get('href')}")
    if primary is None:
        return []
    primary = decompress(primary)
    packages: list[dict] = []
    for package in ElementTree.fromstring(primary).findall("common:package", ns):
        version = package.find("common:version", ns)
        if version is None:
            continue
        packages.append({"name": package.findtext("common:name", "", ns), "description": package.findtext("common:summary", "", ns),
                         "version": f"{version.get('ver')}-{strip_version(version.get('rel', '0'))}"})
    return packages

def parse_arch(data: bytes) -> list[dict]: # Database of a pacman repository (tar of */desc files)
    packages: list[dict] = []
    try:
        with tarfile.open(fileobj=BytesIO(data), mode="r:*") as archive:
            for member in archive.getmembers():
                if not member.name.endswith("/desc"):
                    continue
                file = archive.extractfile(member)
                fields = dict(re.findall(r"%([A-Z]+)%\n([^\n]*)", file.read().decode("utf-8", "replace"))) if file else {}
                if "NAME" in fields and "VERSION" in fields:
                    packages.append({"name": fields["NAME"], "version": fields["VERSION"], "description": fields.get("DESC", "")})
    except (tarfile.TarError, EOFError) as e:
        raise CatalogError(f"cannot read the arch database: {e}") from e
    return packages

def read_packages(source: HttpSource | LocalSource, formats: dict) -> list[dict]: # Packages of a repository (deb > rpm > arch)
    if "deb" in formats:
        arch = "amd64" if "amd64" in formats["deb"]["arches"] else formats["deb"]["arches"][0]
        data = source.read(f"debian/dists/{VALUES.DEB_SUITE}/main/binary-{arch}/Packages")
        if data is not None:
            return parse_deb(data.decode("utf-8", "replace"))
    if "rpm" in formats:
        arch = "x86_64" if "x86_64" in formats["rpm"]["arches"] else formats["rpm"]["arches"][0]
        packages = parse_rpm(source, f"fedora/{formats['rpm']['releases'][-1]}/{arch}")
        if packages:
            return packages
    if "arch" in formats:
        arch = "x86_64" if "x86_64" in formats["arch"]["arches"] else formats["arch"]["arches"][0]
        data = source.read(f"arch/{arch}/{formats['arch']['db']}.db")
        if data is not None:
            return parse_arch(data)
    return []

def latest(packages: list[dict]) -> dict[str, dict]: # Latest version of every package name
    best: dict[str, dict] = {}
    for package in packages:
        current = best.get(package["name"])
        if current is None or version_key(package["version"]) > version_key(current["version"]):
            best[package["name"]] = package
    return best

def build_entry(settings: dict, source: dict, reader: HttpSource | LocalSource, previous: dict | None, today: str) -> dict:
    """Catalog entry of one source, its 'updated' date kept while its versions do not change"""
    formats = detect_formats(reader.files())
    packages = latest(read_packages(reader, formats))
    main = packages.get(source["main"])
    pre = packages.get(source["main"] + VALUES.PRE_SUFFIX)
    entry = {
        "name": source["name"],
        "repo": source["repo"],
        "category": source["category"],
        "private": source.get("private", False),
        "main": source["main"],
        "summary": {"en": source.get("summary_en", ""), "fr": source.get("summary_fr", source.get("summary_en", ""))},
        "repository": f"https://github.com/{settings['owner']}/{source['repo']}",
        "pages": "" if source.get("private") else reader.base,
        "docs": source.get("docs", ""),
        "formats": formats,
        "version": main["version"] if main else "",
        "pre": pre["version"] if pre else "",
        "release": reader.release(),
        "packages": [packages[name] for name in sorted(packages)],
        "updated": today,
    }
    if previous and all(previous.get(k) == entry[k] for k in ("version", "pre", "packages", "formats")):
        entry["updated"] = previous.get("updated", today)
    return entry

def urls(settings: dict, entry: dict) -> dict[str, str]: # Every link of an entry
    base = entry["pages"]
    links = {"repository": entry["repository"], "docs": entry.get("docs", ""),
             "release": (entry.get("release") or {}).get("url", ""), "pages": base}
    if base:
        links["key"] = f"{base}/{settings['key']}"
        if "rpm" in entry["formats"]:
            links["rpm"] = f"{base}/fedora/$releasever/$basearch"
        if "deb" in entry["formats"]:
            links["deb"] = f"{base}/debian"
        if "arch" in entry["formats"]:
            links["arch"] = f"{base}/arch/$arch"
    return links

def dnf_section(entry: dict, base: str, key: str) -> str: # One section of a .repo file
    return (f"[{VALUES.REPO_PREFIX}{entry['name']}]\nname=my-universe - {entry['name']} ({entry['category']})\n"
            f"baseurl={base}/fedora/$releasever/$basearch\nenabled=1\ngpgcheck=1\ngpgkey={key}\n")

def apt_line(entry: dict, base: str, keyring: str) -> str: # One line of a .list file
    arches = ",".join(entry["formats"].get("deb", {}).get("arches", ["amd64"]))
    return f"deb [arch={arches} signed-by={keyring}] {base}/debian {VALUES.DEB_SUITE} main\n"

def pacman_section(entry: dict, base: str) -> str: # One repository of pacman.conf (its name = the name of the database)
    return f"[{entry['formats']['arch']['db']}]\nSigLevel = Required\nServer = {base}/arch/$arch\n"
