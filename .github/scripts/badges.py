"""Genera metrics/badges.svg: una fila de badges estilo shields.io con datos de la API de GitHub.

shields.io devuelve "invalid" en muchos badges de GitHub, así que se generan
aquí con el token del usuario. Sin dependencias externas.

Variables de entorno:
  GH_TOKEN  token con permisos repo y read:org (obligatorio)
  GH_USER   usuario (por defecto alvarosiles)
  OUTDIR    carpeta de salida (por defecto metrics)
"""

import collections
import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape

from i18n import fmt_date

BLUE, GREEN, GREY, LABEL = "#1f6feb", "#2ea043", "#6e7681", "#30363d"

QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    followers { totalCount }
    following { totalCount }
    repositories(ownerAffiliations: OWNER, first: 100, after: $after) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        forkCount
        pushedAt
        watchers { totalCount }
        issues(states: OPEN) { totalCount }
        pullRequests(states: OPEN) { totalCount }
        licenseInfo { spdxId }
        releases(first: 20) { nodes { releaseAssets(first: 50) { nodes { downloadCount } } } }
      }
    }
  }
}
"""


def api(token, url, body=None):
    req = urllib.request.Request(url, data=body, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.load(res)


def graphql(token, variables):
    data = api(token, "https://api.github.com/graphql", json.dumps({"query": QUERY, "variables": variables}).encode())
    if "errors" in data:
        sys.exit(f"Error de GraphQL: {data['errors']}")
    return data["data"]


def collect(token, user):
    repos, after = [], None
    while True:
        u = graphql(token, {"login": user, "after": after})["user"]
        repos += u["repositories"]["nodes"]
        page = u["repositories"]["pageInfo"]
        if not page["hasNextPage"]:
            break
        after = page["endCursor"]
    contributors = api(token, f"https://api.github.com/repos/{user}/{user}/contributors?per_page=100")
    return u, repos, len(contributors)


def text_width(text):
    # Aproximación del ancho de Verdana 11px, como shields.io.
    return sum(4.5 if c in " .,:;il|!'" else 8.5 if c in "mwMW" else 7 for c in text)


def badge(x, y, label, value, color):
    lw, vw = text_width(label) + 12, text_width(value) + 12
    w = lw + vw
    return w, f"""
  <g transform="translate({x:.1f},{y})">
    <rect width="{w:.1f}" height="20" rx="3" fill="{LABEL}"/>
    <rect x="{lw:.1f}" width="{vw:.1f}" height="20" rx="3" fill="{color}"/>
    <rect x="{lw:.1f}" width="4" height="20" fill="{color}"/>
    <text x="{lw / 2:.1f}" y="14" text-anchor="middle">{escape(label)}</text>
    <text x="{lw + vw / 2:.1f}" y="14" text-anchor="middle">{escape(value)}</text>
  </g>"""


def render(items, width=840, gap=6):
    rows, row, row_w = [], [], 0
    for item in items:
        w = text_width(item[0]) + text_width(item[1]) + 24
        if row and row_w + gap + w > width:
            rows.append((row, row_w))
            row, row_w = [], 0
        row_w += (gap if row else 0) + w
        row.append(item)
    rows.append((row, row_w))

    parts = []
    for i, (row, row_w) in enumerate(rows):
        x = (width - row_w) / 2
        for label, value, color in row:
            w, svg = badge(x, i * 28, label, value, color)
            parts.append(svg)
            x += w + gap
    height = len(rows) * 28 - 8
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>text {{ font: 400 11px Verdana, 'DejaVu Sans', sans-serif; fill: #fff; }}</style>{''.join(parts)}
</svg>
"""


def main():
    token = os.environ.get("GH_TOKEN") or sys.exit("Falta GH_TOKEN")
    user = os.environ.get("GH_USER", "alvarosiles")
    outdir = os.environ.get("OUTDIR", "metrics")

    u, repos, contributors = collect(token, user)
    licenses = collections.Counter(r["licenseInfo"]["spdxId"] for r in repos if r["licenseInfo"] and r["licenseInfo"]["spdxId"] != "NOASSERTION")
    downloads = sum(a["downloadCount"] for r in repos for rel in r["releases"]["nodes"] for a in rel["releaseAssets"]["nodes"])
    last = max(dt.datetime.fromisoformat(r["pushedAt"].replace("Z", "+00:00")) for r in repos if r["pushedAt"])
    issues = sum(r["issues"]["totalCount"] for r in repos)
    prs = sum(r["pullRequests"]["totalCount"] for r in repos)

    items = [
        ("status", "active", GREEN),
        ("followers", f"{u['followers']['totalCount']:,}", BLUE),
        ("following", f"{u['following']['totalCount']:,}", BLUE),
        ("repos", f"{len(repos):,}", BLUE),
        ("stars", f"{sum(r['stargazerCount'] for r in repos):,}", BLUE),
        ("forks", f"{sum(r['forkCount'] for r in repos):,}", BLUE),
        ("watchers", f"{sum(r['watchers']['totalCount'] for r in repos):,}", BLUE),
        ("pull requests", f"{prs:,} open", GREEN if prs == 0 else BLUE),
        ("issues", f"{issues:,} open", GREEN if issues == 0 else BLUE),
        ("contributors", f"{contributors:,}", BLUE),
        # Las etiquetas de los badges están en inglés, así que la fecha también.
        ("last commit", fmt_date(last, "en"), BLUE),
        ("downloads", f"{downloads:,}", BLUE if downloads else GREY),
        ("license", licenses.most_common(1)[0][0] if licenses else "none", BLUE if licenses else GREY),
    ]

    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "badges.svg"), "w", encoding="utf-8") as f:
        f.write(render(items))
    print(f"badges.svg: {len(items)} badges")


if __name__ == "__main__":
    main()
