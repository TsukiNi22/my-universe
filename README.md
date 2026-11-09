# my-universe

> [!TIP]
> Site [tsukini22.github.io/my-universe](https://tsukini22.github.io/my-universe/) (catalog with search and filters, install commands for every distribution, EN / FR).

Every package of my projects in one place: one set of repositories for `dnf`, `apt` and `pacman`, a catalog and a CLI.
The packages stay in the gh-pages repository of each project, my-universe only reads them (every day at 00:00 UTC) and points to them.

<!-- universe:badges:start -->
![Packages](https://img.shields.io/endpoint?url=https%3A%2F%2Ftsukini22.github.io%2Fmy-universe%2Fbadges%2Fpackages.json) ![Last update](https://img.shields.io/endpoint?url=https%3A%2F%2Ftsukini22.github.io%2Fmy-universe%2Fbadges%2Fupdated.json) ![Checked](https://img.shields.io/endpoint?url=https%3A%2F%2Ftsukini22.github.io%2Fmy-universe%2Fbadges%2Fchecked.json) ![hand-made](https://img.shields.io/endpoint?url=https%3A%2F%2Ftsukini22.github.io%2Fmy-universe%2Fbadges%2Fhand-made.json) ![ai-made](https://img.shields.io/endpoint?url=https%3A%2F%2Ftsukini22.github.io%2Fmy-universe%2Fbadges%2Fai-made.json) ![Update](https://github.com/TsukiNi22/my-universe/actions/workflows/update.yml/badge.svg)
<!-- universe:badges:end -->

### Table of Contents
 - [Packages](#packages)
 - [Quick Setup - 1 (All)](#quick-setup---1-all)
 - [Quick Setup - 2 (Limited)](#quick-setup---2-limited)
 - [Usage](#usage)
 - [Private packages](#private-packages)
 - [Add a package](#add-a-package)
 - [Workflows/Release](#workflowsrelease)

## Packages

> [!NOTE]
> Two categories: **hand-made** (written by hand, the AI only helped) and **ai-made** (mostly written with an AI).
>
> Most packages have a pre-release/unstable version named `<package_name>-pre`, obsoleted by any stable package of the same version or higher.

<!-- universe:catalog:start -->
### hand-made

| Name + Link | Version | Pre-release | Formats | Release | Last Update | Content |
| ----------- | ------- | ----------- | ------- | ------- | ----------- | ------- |
| [libutils](https://github.com/TsukiNi22/libutils) | `4.2.0` | `4.3.1-47` | `rpm` `deb` `arch` | [v4.2.0](https://github.com/TsukiNi22/libutils/releases/tag/v4.2.0) | ![](https://img.shields.io/github/last-commit/TsukiNi22/libutils) | C++20 library for many different tools: arguments, exceptions, network, IPC, cli, maths... |
| [brain](https://github.com/TsukiNi22/banana-brain) | `1.0.0` | - | `rpm` `deb` `arch` | [v1.0.0](https://github.com/TsukiNi22/banana-brain/releases/tag/v1.0.0) | ![](https://img.shields.io/github/last-commit/TsukiNi22/banana-brain) | C++20 neural network library with several kinds of networks (banana included) |
| [context-forge](https://github.com/TsukiNi22/context-forge) | `1.0.0` | - | `rpm` `deb` | [v1.0.0](https://github.com/TsukiNi22/context-forge/releases/tag/v1.0.0) | ![](https://img.shields.io/github/last-commit/TsukiNi22/context-forge) | Formatting of compiler output (stderr) with ollama and other means, for C++ compilers |

### ai-made

| Name + Link | Version | Pre-release | Formats | Release | Last Update | Content |
| ----------- | ------- | ----------- | ------- | ------- | ----------- | ------- |
| [xstyle](https://github.com/TsukiNi22/xstyle) | `1.0.0` | - | `rpm` `deb` `arch` | [v1.0.0](https://github.com/TsukiNi22/xstyle/releases/tag/v1.0.0) | ![](https://img.shields.io/github/last-commit/TsukiNi22/xstyle) | Checker and fixer of my coding style: C++20 / libutils first, then Python, shell, Rust, CMake and generic rules |
| [xdesk](https://github.com/TsukiNi22/xdesk) | `1.0.0` | - | `rpm` `deb` `arch` | [v1.0.0](https://github.com/TsukiNi22/xdesk/releases/tag/v1.0.0) | ![](https://img.shields.io/github/last-commit/TsukiNi22/xdesk) | Remote desktop and terminal in one binary (Windows / Unix), Qt6 or TTY, TLS 1.3 post-quantum |
<!-- universe:catalog:end -->

## Quick Setup - 1 (All)
> Register every package repository of the universe

> [!WARNING]
> Restriction: `fedora-based (rpm)`, `debian-based (deb)`, `arch-based (pacman)`

> [!NOTE]
> A package repository already set up on its own (ex: `/etc/yum.repos.d/libutils.repo` from the `setup.sh` of libutils) is kept and skipped: apt refuses the same source twice with two keys.

The script detects the distribution from `/etc/os-release`, imports the signing key (`RPM-GPG-KEY-tsukini`, the same for every project) and adds:
1. `rpm`: `/etc/yum.repos.d/universe.repo` (one `[universe-<name>]` section per package).
2. `deb`: the key in `/etc/apt/keyrings/universe.gpg` and the sources in `/etc/apt/sources.list.d/universe.list`, then `apt-get update`.
3. `arch`: the key in the pacman keyring and one `[<database>]` repository per package in `/etc/pacman.conf`, then `pacman -Sy`.

```bash
curl -fsSL https://tsukini22.github.io/my-universe/install.sh | bash -s
```

or with `wget`:

```bash
wget -qO- https://tsukini22.github.io/my-universe/install.sh | bash -s
```

Then install the packages: `sudo dnf install libutils`, `sudo apt install libutils` or `sudo pacman -S libutils`.

| Argument | Effect |
| -------- | ------ |
| `--only libutils,brain` | Register only these packages |
| `--no-sudo` | Run without `sudo` (the script must already run as root) |
| `--dry-run` | Print what would be done, change nothing |
| `-h`, `--help` | Display the usage |

## Quick Setup - 2 (Limited)
> One file per package manager, by hand

| File | Content |
| ---- | ------- |
| [`universe.repo`](https://tsukini22.github.io/my-universe/universe.repo) | Every rpm repository, for `/etc/yum.repos.d/` |
| [`universe.list`](https://tsukini22.github.io/my-universe/universe.list) | Every deb repository, for `/etc/apt/sources.list.d/` (key in `/etc/apt/keyrings/universe.gpg`) |
| [`universe.conf`](https://tsukini22.github.io/my-universe/universe.conf) | Every pacman repository, to append to `/etc/pacman.conf` |
| [`index.json`](https://tsukini22.github.io/my-universe/index.json) | The whole catalog: versions, formats, sub-packages, links, dates |
| [`badges/`](https://tsukini22.github.io/my-universe/#badges) | One [shields.io endpoint](https://shields.io/badges/endpoint-badge) per package and for the global information |

```bash
sudo curl -fsSL -o /etc/yum.repos.d/universe.repo https://tsukini22.github.io/my-universe/universe.repo
sudo rpm --import https://tsukini22.github.io/my-universe/RPM-GPG-KEY-tsukini
```

## Usage
> `universe`: Python 3.11+ only (standard library), from a clone of the repository

```bash
./universe setup [--private]                    # register the package repositories (--private: + the mirrored private ones)
./universe install NAME... | all [--hand-made] [--ai-made] [--pre] [--yes]  # install packages (--pre: the -pre ones)
./universe update [--yes]                       # refresh the mirror, then upgrade the installed universe packages
./universe list [--hand-made] [--ai-made]       # every package: category, version, pre-release, installed, formats
./universe outdated                             # installed packages with a newer version
./universe info [NAME...]                       # everything about one / every package (dnf info style), installed or not
./universe links [NAME...]                      # repository, docs, release, package repository, key, mirror of each package
./universe mirror [--all] [NAME...]             # clone / pull the gh-pages of the private (--all: every) package repositories
```

| Option | Effect |
| ------ | ------ |
| `--online` | Read the versions from the package repositories instead of `packages.json` (`list`, `outdated`, `info`) |
| `--dry-run` | Print the commands (`setup`, `install`, `update`), change nothing |
| `--no-sudo` | Run the root commands without `sudo` (already root) |
| `--rtk` | Compact output (no table, one line per package), made for an AI |

> [!NOTE]
> `packages.json` is updated by the workflow: a `git pull` is enough to get the new versions locally.
> The root commands use `sudo`, or `sudo -A` when `SUDO_ASKPASS` is set (graphical password prompt).

## Private packages

> [!IMPORTANT]
> The private repositories are never published: they are neither in `sources.toml` nor on the site.

They are listed in `private.toml` (git ignored, same format as `sources.toml`) and only read by the local CLI:
1. `./universe mirror` clones the `gh-pages` branch of each private repository with your own git access (ssh key / `gh auth`) into `~/.local/share/universe/<repo>`.
2. `./universe setup --private` registers these mirrors as local repositories (`file://`).
3. `list`, `info`, `outdated`, `install` and `update` show them with the public ones; `update` refreshes the mirror first.

## Add a package

1. Add a `[[source]]` in `sources.toml` (public) or `private.toml` (private):
   ```toml
   [[source]]
   name = "libutils"         # name used by the CLI and the site
   repo = "libutils"         # GitHub repository whose gh-pages holds the package repository
   category = "hand-made"    # hand-made | ai-made
   main = "libutils"         # package installed by `universe install libutils`
   summary_en = "..."
   summary_fr = "..."
   docs = "https://..."      # optional
   ```
2. Check it locally: `python3 scripts/update.py && python3 scripts/render.py --readme --site dist`.
3. Push: the workflow renders the README and deploys the site.

The formats are detected from the gh-pages branch (`fedora/<release>/<arch>/repodata`, `debian/dists/stable`, `arch/<arch>/<db>.db`), the versions are read from the `Packages` index (deb), else the rpm metadata, else the pacman database.

## Workflows/Release

### Workflows
- `update.yml`: every day at 00:00 UTC (and on a push of the sources / scripts / site, or by hand): reads every package repository, commits `packages.json` and the README when a version changed (`chore(packages): update versions (...)`), renders and force pushes the site on the `gh-pages` branch.

### Setup of the repository
- Variable `RUNNER`: the runner of the jobs (`gh variable set RUNNER --repo TsukiNi22/my-universe --body <label>`).
- Pages: `gh-pages` branch, `/` folder (Settings > Pages), once the first deployment is done.
- No secret: the public package repositories are read with the `GITHUB_TOKEN` of the run.
