"""Genera metrics/stats.svg y metrics/streak.svg con datos de la API de GitHub.

Cada tarjeta se genera en español y en inglés (ver i18n.py).

Usa el token del usuario, así que incluye contribuciones privadas y de
organizaciones. Si existe OUTDIR/commits.json (de languages.py) añade los
commits y líneas de todas las ramas. Sin dependencias externas.

Variables de entorno:
  GH_TOKEN  token con permisos repo y read:org (obligatorio)
  GH_USER   usuario (por defecto alvarosiles)
  OUTDIR    carpeta de salida (por defecto metrics)
"""

import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape

from i18n import LANGS, filename, fmt_date, t

STYLE = """
    .title { font: 600 18px 'Segoe UI', Ubuntu, sans-serif; fill: #58a6ff; }
    .sub { font: 400 12px 'Segoe UI', Ubuntu, sans-serif; fill: #8b949e; }
    .label { font: 400 13px 'Segoe UI', Ubuntu, sans-serif; fill: #c9d1d9; }
    .value { font: 700 13px 'Segoe UI', Ubuntu, sans-serif; fill: #c9d1d9; }
    .big { font: 700 30px 'Segoe UI', Ubuntu, sans-serif; fill: #c9d1d9; }
    .accent { fill: #f78166; }
    .caption { font: 600 13px 'Segoe UI', Ubuntu, sans-serif; fill: #c9d1d9; }
    .date { font: 400 11px 'Segoe UI', Ubuntu, sans-serif; fill: #8b949e; }
"""


def graphql(token, query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as res:
        data = json.load(res)
    if "errors" in data:
        sys.exit(f"Error de GraphQL: {data['errors']}")
    return data["data"]


USER_QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    createdAt
    organizations { totalCount }
    repositoriesContributedTo(includeUserRepositories: true, contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    repositories(ownerAffiliations: OWNER, first: 100, isFork: false) {
      totalCount
      nodes { stargazerCount }
    }
  }
}
"""

YEAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def collect(token, login):
    user = graphql(token, USER_QUERY, {"login": login})["user"]
    start = dt.datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00")).date()
    today = dt.date.today()

    totals = {"commits": 0, "prs": 0, "issues": 0, "reviews": 0, "contributions": 0}
    days = {}
    year_start = start
    while year_start <= today:
        year_end = min(dt.date(year_start.year, 12, 31), today)
        c = graphql(token, YEAR_QUERY, {
            "login": login,
            "from": f"{year_start}T00:00:00Z",
            "to": f"{year_end}T23:59:59Z",
        })["user"]["contributionsCollection"]
        totals["commits"] += c["totalCommitContributions"]
        totals["prs"] += c["totalPullRequestContributions"]
        totals["issues"] += c["totalIssueContributions"]
        totals["reviews"] += c["totalPullRequestReviewContributions"]
        totals["contributions"] += c["contributionCalendar"]["totalContributions"]
        for week in c["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                days[dt.date.fromisoformat(day["date"])] = day["contributionCount"]
        year_start = dt.date(year_start.year + 1, 1, 1)

    return {
        "name": user["name"] or login,
        "since": start,
        "stars": sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
        "repos": user["repositories"]["totalCount"],
        "contributed": user["repositoriesContributedTo"]["totalCount"],
        "orgs": user["organizations"]["totalCount"],
        "days": dict(sorted(days.items())),
        **totals,
    }


def runs(counts, current, step):
    """(racha actual, racha más larga, (inicio, fin) de la más larga) sobre unidades consecutivas.

    La unidad en curso sin actividad todavía no rompe la racha actual.
    """
    longest, best, start = 0, (None, None), None
    for unit in sorted(counts):
        if counts[unit] > 0:
            start = start or unit
            length = (unit - start).days // step + 1
            if length > longest:
                longest, best = length, (start, unit)
        else:
            start = None

    now, unit = 0, current if counts.get(current, 0) > 0 else current - dt.timedelta(days=step)
    while counts.get(unit, 0) > 0:
        now += 1
        unit -= dt.timedelta(days=step)
    return now, longest, best


def week_of(d):
    # Semanas de domingo a sábado, como el calendario de GitHub
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)


def streaks(days, today):
    weeks = {}
    for d, n in days.items():
        weeks[week_of(d)] = weeks.get(week_of(d), 0) + n
    return runs(days, today, 1), runs(weeks, week_of(today), 7)


def render_stats(s, lang, width=495, height=250):
    rows = [
        (t(lang, "stats.contributions"), s["contributions"]),
        (t(lang, "stats.commits"), s["commits"]),
        (t(lang, "stats.all_commits"), s.get("all_commits", 0)),
        (t(lang, "stats.lines"), s.get("lines", 0)),
        (t(lang, "stats.prs"), s["prs"]),
        (t(lang, "stats.issues"), s["issues"]),
        (t(lang, "stats.contributed"), s["contributed"]),
        (t(lang, "stats.orgs"), s["orgs"]),
    ]
    items = []
    for i, (label, value) in enumerate(rows):
        x, y = 25 + (i % 2) * 230, 100 + (i // 2) * 34
        items.append(
            f'<text x="{x}" y="{y}" class="label">{escape(label)}</text>'
            f'<text x="{x + 205}" y="{y}" class="value" text-anchor="end">{value:,}</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{t(lang, 'stats.title')}">
  <style>{STYLE}</style>
  <rect width="{width}" height="{height}" rx="4.5" fill="#0d1117"/>
  <text x="25" y="36" class="title">{t(lang, 'stats.title')}</text>
  <text x="25" y="58" class="sub">{t(lang, 'stats.sub', since=fmt_date(s['since'], lang))}</text>
  {"".join(items)}
</svg>
'''


def render_streak(s, daily, weekly, lang, width=990, height=200):
    def period(best):
        a, b = best
        return f"{fmt_date(a, lang)} – {fmt_date(b, lang)}" if a else "—"

    cols = [
        (s["contributions"], t(lang, "streak.total"), t(lang, "streak.since", since=fmt_date(s["since"], lang)), False),
        (daily[0], t(lang, "streak.current_days"), t(lang, "streak.current_days.sub"), True),
        (daily[1], t(lang, "streak.longest_days"), period(daily[2]), False),
        (weekly[0], t(lang, "streak.current_weeks"), t(lang, "streak.current_weeks.sub"), True),
        (weekly[1], t(lang, "streak.longest_weeks"), period(weekly[2]), False),
    ]
    col_w = width / len(cols)
    parts = []
    for i, (value, caption, date, accent) in enumerate(cols):
        cx = col_w * i + col_w / 2
        if i:
            parts.append(f'<line x1="{col_w * i:.1f}" y1="45" x2="{col_w * i:.1f}" y2="{height - 35}" stroke="#30363d"/>')
        parts.append(
            f'<text x="{cx:.1f}" y="95" class="big{" accent" if accent else ""}" text-anchor="middle">{value:,}</text>'
            f'<text x="{cx:.1f}" y="128" class="caption" text-anchor="middle">{escape(caption)}</text>'
            f'<text x="{cx:.1f}" y="150" class="date" text-anchor="middle">{escape(date)}</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{t(lang, 'streak.label')}">
  <style>{STYLE}</style>
  <rect width="{width}" height="{height}" rx="4.5" fill="#0d1117"/>
  {"".join(parts)}
</svg>
'''


def main():
    token = os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("Falta GH_TOKEN")
    login = os.environ.get("GH_USER", "alvarosiles")
    outdir = os.environ.get("OUTDIR", "metrics")

    s = collect(token, login)
    try:  # totales de todas las ramas, generados antes por languages.py
        with open(os.path.join(outdir, "commits.json"), encoding="utf-8") as f:
            data = json.load(f)
        s["all_commits"], s["lines"] = data["commits"], data["lines"]
    except (OSError, ValueError, KeyError):
        pass
    daily, weekly = streaks(s["days"], dt.date.today())
    os.makedirs(outdir, exist_ok=True)
    for lang in LANGS:
        with open(os.path.join(outdir, filename("stats", lang)), "w", encoding="utf-8") as f:
            f.write(render_stats(s, lang))
        with open(os.path.join(outdir, filename("streak", lang)), "w", encoding="utf-8") as f:
            f.write(render_streak(s, daily, weekly, lang))
    print(f"Contribuciones {s['contributions']:,} · commits {s['commits']:,} · PRs {s['prs']} · issues {s['issues']}")
    print(f"Racha diaria actual {daily[0]}, máxima {daily[1]} {daily[2]}")
    print(f"Racha semanal actual {weekly[0]}, máxima {weekly[1]} {weekly[2]}")


if __name__ == "__main__":
    main()
