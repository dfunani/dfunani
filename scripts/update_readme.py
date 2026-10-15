#!/usr/bin/env python3
"""Rebuild README.md from live GitHub repos + README.template.md."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USERNAME = "dfunani"
API = "https://api.github.com"

FEATURED_COUNT = 8
FEATURED_ORDER = [
    "typedantic",
    "rusticorn",
    "stackforge",
    "py_vui",
    "r_python",
    "r_check",
    "r_tvui",
    "pixel_joy",
    "AfroChat",
    "fast_pay",
    "homehub",
    "stockhub",
]

# Satellite repos fold into a parent so the catalog stays readable.
COMPANIONS = {
    "typedantic-web": "typedantic",
    "py_vui_web": "py_vui",
    "stackforge_web": "stackforge",
    "r_python_web": "r_python",
    "r_tvui_web": "r_tvui",
    "r_check_web": "r_check",
    "pixel_joy_cli": "pixel_joy",
    "WebAfroChat": "AfroChat",
    "AndroidAfroChat": "AfroChat",
    "IOSAfroChat": "AfroChat",
}

EXCLUDE_NAMES = {
    "dfunani",
    "CS50",
    "build-your-own-x",
    "top-github-repositories-which-everyone-should-look",
}
EXCLUDE_PREFIXES = ("alx-",)

FALLBACK_BLURBS = {
    "typedantic": "Pydantic-style validation for TypeScript",
    "rusticorn": "Production-grade ASGI server for Python, written in Rust",
    "stackforge": "Local AWS cloud emulator for development, testing, and CI",
    "py_vui": "Free local drag-and-drop GUI builder that exports Python UI code",
    "r_python": "Memory-safe, statically typed language with Python-shaped syntax",
    "r_check": "mypy-compatible Python type checker implemented in Rust",
    "r_tvui": "Keyboard-driven TUI file explorer in Rust",
    "pixel_joy": "Studio of common and retro games in the browser",
    "AfroChat": "Realtime Slack-style chat across web, iOS, and Android",
    "fast_pay": "Mobile payments platform — USSD, wallet, merchant QR, microservices",
    "homehub": "South African household services showroom and lead capture",
    "stockhub": "South African livestock showroom and lead capture",
    "names-game": "Solo vocabulary game — pick a letter, fill every category",
    "py_boiler": "Python project scaffolding and boilerplate generator",
    "MyDecoder": "Encode and decode Base64 in the browser",
    "omo-game": "Browser game experiment",
    "afroMQ": "Message queue in Go",
    "deltabase": "Database experiment in Rust",
    "R3D": "3D rendering in Rust",
    "rcmd": "Command-line tooling in Rust",
    "tree-node": "Tree / node visualisation",
    "software_design": "Notes and exercises in software design",
    "linux-selfhosting": "Homelab path on Ubuntu Server in UTM",
    "Linux-Setup": "Local Linux setup documentation",
    "linux-for-dummies": "Linux learning notes",
    "password_generator": "Password generator",
    "afro_llm": "LLM experiments",
    "Advent_of_code": "Advent of Code solutions",
    "RenderEngine--3D-Imaging": "Simple 3D render engine",
    "RenderEngine--2D-Imaging": "Ray-tracing introduction — 2D images",
    "OpenGL--3D-Renderer": "OpenGL 3D renderer",
}

GROUPS = [
    (
        "Languages & tooling",
        [
            "typedantic",
            "r_python",
            "r_check",
            "rusticorn",
            "py_vui",
            "py_boiler",
            "rcmd",
        ],
    ),
    (
        "Cloud, data & infra",
        [
            "stackforge",
            "r_tvui",
            "afroMQ",
            "deltabase",
            "linux-selfhosting",
            "Linux-Setup",
        ],
    ),
    (
        "Products",
        [
            "AfroChat",
            "fast_pay",
            "homehub",
            "stockhub",
            "MyDecoder",
            "password_generator",
            "names-game",
        ],
    ),
    (
        "Games & graphics",
        [
            "pixel_joy",
            "omo-game",
            "R3D",
            "RenderEngine--3D-Imaging",
            "RenderEngine--2D-Imaging",
            "OpenGL--3D-Renderer",
        ],
    ),
]

PIN_QS = (
    "title_color=22d3ee&text_color=e7e5e4&icon_color=22d3ee"
    "&bg_color=0c0a09&hide_border=true&locale=en"
)


def github_get(path: str, token: str | None) -> object:
    url = f"{API}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "dfunani-profile-readme",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode())
        link = resp.headers.get("Link", "")
    return body, link


def parse_next(link: str) -> str | None:
    for part in link.split(","):
        if 'rel="next"' in part:
            match = re.search(r"<([^>]+)>", part)
            if match:
                return match.group(1)
    return None


def fetch_repos(token: str | None) -> list[dict]:
    repos: list[dict] = []
    path = f"/users/{USERNAME}/repos?per_page=100&type=owner&sort=updated"
    while path:
        if path.startswith("http"):
            parsed = urllib.parse.urlparse(path)
            path = parsed.path + ("?" + parsed.query if parsed.query else "")
        page, link = github_get(path, token)
        repos.extend(page)
        nxt = parse_next(link)
        path = nxt or ""
    return repos


def keep(repo: dict) -> bool:
    name = repo["name"]
    if repo.get("fork") or repo.get("archived"):
        return False
    if name in EXCLUDE_NAMES:
        return False
    if name.startswith(EXCLUDE_PREFIXES):
        return False
    return True


def blurb(repo: dict) -> str:
    return (repo.get("description") or "").strip() or FALLBACK_BLURBS.get(
        repo["name"], "Work in progress"
    )


def pin(name: str) -> str:
    src = (
        f"https://github-readme-stats.vercel.app/api/pin/"
        f"?username={USERNAME}&repo={urllib.parse.quote(name)}&{PIN_QS}"
    )
    return (
        f'<a href="https://github.com/{USERNAME}/{name}">'
        f'<img src="{src}" alt="{name}" /></a>'
    )


def featured_html(chosen: list[dict]) -> str:
    rows = []
    for i in range(0, len(chosen), 2):
        left = chosen[i]
        right = chosen[i + 1] if i + 1 < len(chosen) else None
        cells = [
            f'<td width="50%" valign="top">\n\n{pin(left["name"])}\n\n</td>'
        ]
        if right:
            cells.append(
                f'<td width="50%" valign="top">\n\n{pin(right["name"])}\n\n</td>'
            )
        else:
            cells.append('<td width="50%" valign="top"></td>')
        rows.append("<tr>\n" + "\n".join(cells) + "\n</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def pick_featured(by_name: dict[str, dict], recent: list[dict]) -> list[dict]:
    picked: list[dict] = []
    seen: set[str] = set()
    for name in FEATURED_ORDER:
        repo = by_name.get(name)
        if repo and name not in seen:
            picked.append(repo)
            seen.add(name)
        if len(picked) >= FEATURED_COUNT:
            return picked
    for repo in recent:
        name = repo["name"]
        if name in seen or name in COMPANIONS:
            continue
        picked.append(repo)
        seen.add(name)
        if len(picked) >= FEATURED_COUNT:
            break
    return picked


def catalog_md(by_name: dict[str, dict], all_kept: list[dict]) -> str:
    grouped: dict[str, list[dict]] = {title: [] for title, _ in GROUPS}
    grouped["More"] = []
    assigned: set[str] = set()

    for title, names in GROUPS:
        for name in names:
            repo = by_name.get(name)
            if repo:
                grouped[title].append(repo)
                assigned.add(name)

    for repo in all_kept:
        name = repo["name"]
        if name in assigned or name in COMPANIONS:
            continue
        grouped["More"].append(repo)

    parts: list[str] = []
    for title, _ in GROUPS + [("More", [])]:
        items = grouped[title]
        if not items:
            continue
        parts.append(f"### {title}\n")
        parts.append("| Project | What it is |")
        parts.append("|---|---|")
        for repo in items:
            name = repo["name"]
            extras = []
            kids = [
                child
                for child, parent in COMPANIONS.items()
                if parent == name and child in by_name
            ]
            homepage = (repo.get("homepage") or "").strip()
            if not homepage:
                for child in kids:
                    homepage = (by_name[child].get("homepage") or "").strip()
                    if homepage:
                        break
            if homepage:
                extras.append(f"[site]({homepage})")
            for child in kids:
                extras.append(f"[{child}](https://github.com/{USERNAME}/{child})")
            extra = f" · {' · '.join(extras)}" if extras else ""
            parts.append(
                f"| **[{name}](https://github.com/{USERNAME}/{name})**{extra} "
                f"| {blurb(repo)} |"
            )
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    raw = fetch_repos(token)
    public_count = sum(1 for r in raw if not r.get("private"))
    kept = [r for r in raw if keep(r)]
    kept.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)
    by_name = {r["name"]: r for r in kept}

    featured = pick_featured(by_name, kept)
    template = (ROOT / "README.template.md").read_text(encoding="utf-8")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    readme = (
        template.replace("{{FEATURED}}", featured_html(featured))
        .replace("{{CATALOG}}", catalog_md(by_name, kept))
        .replace("{{GENERATED_AT}}", now)
        .replace("{{REPO_COUNT}}", str(public_count))
    )
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print(f"Wrote README.md · {public_count} public repos · {len(featured)} featured")


if __name__ == "__main__":
    main()
