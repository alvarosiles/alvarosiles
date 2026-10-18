"""Textos de las tarjetas en español e inglés.

Cada tarjeta se genera una vez por idioma: `metrics/<nombre>.svg` en español
y `metrics/<nombre>-en.svg` en inglés.
"""

LANGS = ("es", "en")

MONTHS = {
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}

TEXTS = {
    "es": {
        "languages.title": "Lenguajes en todos mis commits",
        "languages.sub": "{commits:,} commits · {repos} repos · {lines:,} líneas añadidas",
        "stats.title": "Estadísticas de GitHub",
        "stats.sub": "Incluye contribuciones privadas y de organizaciones · desde {since}",
        "stats.contributions": "Contribuciones totales",
        "stats.commits": "Commits (gráfico de GitHub)",
        "stats.all_commits": "Commits en todas las ramas",
        "stats.lines": "Líneas añadidas",
        "stats.prs": "Pull requests",
        "stats.issues": "Issues",
        "stats.contributed": "Repos en los que contribuí",
        "stats.orgs": "Organizaciones",
        "streak.label": "Constancia y rachas",
        "streak.total": "Contribuciones totales",
        "streak.since": "desde {since}",
        "streak.current_days": "Racha actual (días)",
        "streak.current_days.sub": "días seguidos con actividad",
        "streak.longest_days": "Racha más larga (días)",
        "streak.current_weeks": "Racha actual (semanas)",
        "streak.current_weeks.sub": "semanas seguidas con actividad",
        "streak.longest_weeks": "Racha más larga (semanas)",
        "tech.label": "Tecnologías y comandos que uso",
        "tech.tools.title": "Herramientas y plataformas",
        "tech.tools.sub": "Detectadas en los archivos que modifiqué en mis commits",
        "tech.file": "archivo",
        "tech.files": "archivos",
        "tech.commands.title": "Comandos de terminal que más uso",
        "tech.commands.sub": "En scripts de shell, Dockerfiles, workflows de CI, servicios systemd y bloques de código de documentación",
    },
    "en": {
        "languages.title": "Languages across all my commits",
        "languages.sub": "{commits:,} commits · {repos} repos · {lines:,} lines added",
        "stats.title": "GitHub stats",
        "stats.sub": "Includes private and organization contributions · since {since}",
        "stats.contributions": "Total contributions",
        "stats.commits": "Commits (GitHub graph)",
        "stats.all_commits": "Commits across all branches",
        "stats.lines": "Lines added",
        "stats.prs": "Pull requests",
        "stats.issues": "Issues",
        "stats.contributed": "Repos contributed to",
        "stats.orgs": "Organizations",
        "streak.label": "Consistency and streaks",
        "streak.total": "Total contributions",
        "streak.since": "since {since}",
        "streak.current_days": "Current streak (days)",
        "streak.current_days.sub": "consecutive days with activity",
        "streak.longest_days": "Longest streak (days)",
        "streak.current_weeks": "Current streak (weeks)",
        "streak.current_weeks.sub": "consecutive weeks with activity",
        "streak.longest_weeks": "Longest streak (weeks)",
        "tech.label": "Technologies and commands I use",
        "tech.tools.title": "Tools and platforms",
        "tech.tools.sub": "Detected in the files I changed in my commits",
        "tech.file": "file",
        "tech.files": "files",
        "tech.commands.title": "Most used terminal commands",
        "tech.commands.sub": "In shell scripts, Dockerfiles, CI workflows, systemd services and documentation code blocks",
    },
}


def t(lang, key, **values):
    return TEXTS[lang][key].format(**values)


def fmt_date(d, lang):
    return f"{d.day} {MONTHS[lang][d.month - 1]} {d.year}"


def filename(name, lang):
    return f"{name}.svg" if lang == "es" else f"{name}-{lang}.svg"
