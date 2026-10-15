"""Genera metrics/languages.svg con los lenguajes de TODOS mis commits.

Recorre todos los repos accesibles con el token (propios, de colaborador y de
organizaciones) y todas sus ramas, cuenta solo los commits de mis identidades
y suma las líneas añadidas por lenguaje. Sin dependencias externas.

Variables de entorno:
  GH_TOKEN  token con permisos repo y read:org (obligatorio)
  REPOS     lista opcional "owner/repo,owner/repo" para probar con pocos repos
  OUTPUT    ruta del SVG (por defecto metrics/languages.svg)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from html import escape

AUTHORS = ["alvarosiles", "Alvaro Siles"]
EXTRA_REPOS = ["S-ERP/app"]
# El backup tiene en main una copia entera de S-ERP/app con commits a mi nombre;
# su historial real ya se lee directamente desde S-ERP/app.
SKIP_REPOS = {"alvarosiles/alvarosiles", "alvarosiles/S-ERP-app_backup"}

# Archivos con más líneas añadidas que esto en un solo commit se ignoran:
# suelen ser código copiado, generado o importado de otro proyecto.
MAX_LINES_PER_FILE = 3000

SKIP_DIRS = ("node_modules/", "vendor/", "dist/", "build/", ".next/", "Pods/", "target/", ".gradle/", "android/app/build/")
SKIP_SUFFIXES = (".min.js", ".min.css", ".bundle.js", ".map", "-lock.json", ".lock", ".lockb")

LANGUAGES = {
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".groovy": "Groovy", ".gradle": "Groovy",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript", ".cts": "TypeScript",
    ".py": "Python", ".ipynb": "Jupyter Notebook",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".ps1": "PowerShell", ".psm1": "PowerShell", ".bat": "Batchfile", ".cmd": "Batchfile",
    ".html": "HTML", ".htm": "HTML", ".ejs": "EJS",
    ".css": "CSS", ".scss": "SCSS", ".sass": "Sass", ".less": "Less",
    ".sql": "SQL", ".plpgsql": "PLpgSQL",
    ".swift": "Swift", ".m": "Objective-C", ".mm": "Objective-C++",
    ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".hpp": "C++", ".cs": "C#",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby", ".php": "PHP", ".dart": "Dart",
    ".vue": "Vue", ".svelte": "Svelte", ".lua": "Lua", ".r": "R",
}
FILENAMES = {"dockerfile": "Dockerfile", "makefile": "Makefile", "podfile": "Ruby", "gemfile": "Ruby"}

COLORS = {
    "Java": "#b07219", "Kotlin": "#A97BFF", "Groovy": "#4298b8", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "Python": "#3572A5", "Jupyter Notebook": "#DA5B0B", "Shell": "#89e051",
    "PowerShell": "#012456", "Batchfile": "#C1F12E", "HTML": "#e34c26", "EJS": "#a91e50",
    "CSS": "#563d7c", "SCSS": "#c6538c", "Sass": "#a53b70", "Less": "#1d365d", "SQL": "#e38c00",
    "PLpgSQL": "#336790", "Swift": "#F05138", "Objective-C": "#438eff", "Objective-C++": "#6866fb",
    "C": "#555555", "C++": "#f34b7d", "C#": "#178600", "Go": "#00ADD8", "Rust": "#dea584",
    "Ruby": "#701516", "PHP": "#4F5D95", "Dart": "#00B4AB", "Vue": "#41b883", "Svelte": "#ff3e00",
    "Lua": "#000080", "R": "#198CE7", "Dockerfile": "#384d54", "Makefile": "#427819",
}


def api(token, url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.load(res)


def list_repos(token):
    repos, page = [], 1
    while True:
        batch = api(token, f"https://api.github.com/user/repos?affiliation=owner,collaborator,organization_member&per_page=100&page={page}")
        repos += [r["full_name"] for r in batch if not r["fork"]]
        if len(batch) < 100:
            return repos
        page += 1


def language_of(path):
    if " => " in path:  # renombrado: "dir/{a => b}.js" o "a.js => b.js"
        path = path.replace("{", "").replace("}", "").split(" => ")[-1]
    if path.startswith(SKIP_DIRS) or any(f"/{d}" in path for d in SKIP_DIRS) or path.endswith(SKIP_SUFFIXES):
        return None
    name = path.rsplit("/", 1)[-1].lower()
    if name.startswith("dockerfile"):
        return "Dockerfile"
    if name in FILENAMES:
        return FILENAMES[name]
    ext = os.path.splitext(name)[1]
    return LANGUAGES.get(ext)


def analyze(token, repo, workdir, seen, stats):
    path = os.path.join(workdir, repo.replace("/", "__"))
    url = f"https://x-access-token:{token}@github.com/{repo}.git"
    clone = subprocess.run(["git", "clone", "--bare", "--quiet", url, path], capture_output=True, text=True)
    if clone.returncode:
        print(f"  ! no se pudo clonar {repo}")
        return 0
    cmd = ["git", "-C", path, "log", "--all", "--no-merges", "-M", "--numstat", "--format=@%H"]
    cmd += [f"--author={a}" for a in AUTHORS]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    shutil.rmtree(path, ignore_errors=True)

    commits, current = 0, None
    for line in out.splitlines():
        if line.startswith("@"):
            current = line[1:]
            if current in seen:
                current = None
            else:
                seen.add(current)
                commits += 1
            continue
        if not current or not line.strip():
            continue
        added, _, file = line.split("\t", 2)
        if added == "-" or int(added) > MAX_LINES_PER_FILE:
            continue
        lang = language_of(file)
        if lang:
            stats[lang] = stats.get(lang, 0) + int(added)
    return commits


def render(stats, commits, repos, limit=10):
    total = sum(stats.values())
    top = sorted(((k, v) for k, v in stats.items() if v), key=lambda kv: -kv[1])[:limit]
    width, bar_w = 495, 445
    rows = (len(top) + 1) // 2
    height = 120 + rows * 26

    bar, x = [], 25.0
    for name, lines in top:
        w = bar_w * lines / total
        bar.append(f'<rect x="{x:.2f}" y="78" width="{w:.2f}" height="8" fill="{COLORS.get(name, "#8b949e")}"/>')
        x += w

    items = []
    for i, (name, lines) in enumerate(top):
        cx, cy = 25 + (i % 2) * 230, 112 + (i // 2) * 26
        items.append(
            f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{COLORS.get(name, "#8b949e")}"/>'
            f'<text x="{cx + 16}" y="{cy}" class="lang">{escape(name)}</text>'
            f'<text x="{cx + 205}" y="{cy}" class="pct" text-anchor="end">{100 * lines / total:.1f}%</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Lenguajes de todos mis commits">
  <style>
    .title {{ font: 600 18px 'Segoe UI', Ubuntu, sans-serif; fill: #58a6ff; }}
    .sub {{ font: 400 12px 'Segoe UI', Ubuntu, sans-serif; fill: #8b949e; }}
    .lang {{ font: 400 13px 'Segoe UI', Ubuntu, sans-serif; fill: #c9d1d9; }}
    .pct {{ font: 600 13px 'Segoe UI', Ubuntu, sans-serif; fill: #8b949e; }}
  </style>
  <rect width="{width}" height="{height}" rx="4.5" fill="#0d1117"/>
  <text x="25" y="36" class="title">Lenguajes en todos mis commits</text>
  <text x="25" y="58" class="sub">{commits:,} commits · {repos} repos · {total:,} líneas añadidas</text>
  <clipPath id="bar"><rect x="25" y="78" width="{bar_w}" height="8" rx="4"/></clipPath>
  <g clip-path="url(#bar)">{"".join(bar)}</g>
  {"".join(items)}
</svg>
'''


def main():
    token = os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("Falta GH_TOKEN")
    repos = [r.strip() for r in os.environ["REPOS"].split(",")] if os.environ.get("REPOS") else list_repos(token) + EXTRA_REPOS
    repos = [r for r in dict.fromkeys(repos) if r not in SKIP_REPOS]
    print(f"Analizando {len(repos)} repos")

    seen, stats, active = set(), {}, 0
    with tempfile.TemporaryDirectory() as workdir:
        for repo in repos:
            n = analyze(token, repo, workdir, seen, stats)
            if n:
                active += 1
                print(f"  {repo}: {n} commits")

    if not stats:
        sys.exit("No se encontraron commits; no se sobrescribe la tarjeta")
    output = os.environ.get("OUTPUT", "metrics/languages.svg")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(render(stats, len(seen), active))
    for name, lines in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(f"  {name}: {lines:,}")


if __name__ == "__main__":
    main()
