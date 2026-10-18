"""Detección de herramientas y comandos de terminal en mis commits.

- Herramientas: por nombre/ruta de los archivos que toqué y, para Kubernetes,
  también por el contenido YAML (kind: Deployment, Service, ...).
- Comandos: primera palabra de cada comando en las líneas que añadí en scripts
  de shell, RUN/CMD de Dockerfiles, workflows de CI, Makefiles y bloques de
  código de archivos Markdown.
"""

import re
from collections import Counter
from html import escape

from i18n import t

# (nombre, color, función que decide si una ruta pertenece a la herramienta)
TOOLS = [
    ("Docker", "#2496ED", lambda p, n: n.startswith(("dockerfile", "docker-compose", "compose.y")) or n == ".dockerignore"),
    ("Kubernetes", "#326CE5", lambda p, n: any(d in p for d in ("k8s/", "kubernetes/", "helm/", "charts/")) or n in ("kustomization.yaml", "chart.yaml")),
    ("GitHub Actions", "#2088FF", lambda p, n: p.startswith(".github/workflows/")),
    ("Bash / Shell", "#89e051", lambda p, n: n.endswith((".sh", ".bash", ".zsh"))),
    ("PowerShell", "#5391FE", lambda p, n: n.endswith((".ps1", ".psm1"))),
    ("Nginx", "#009639", lambda p, n: "nginx" in p),
    ("systemd", "#30D475", lambda p, n: n.endswith((".service", ".timer"))),
    ("Terraform", "#844FBA", lambda p, n: n.endswith((".tf", ".tfvars"))),
    ("Ansible", "#EE0000", lambda p, n: "ansible" in p or "playbook" in n),
    ("Makefile", "#427819", lambda p, n: n in ("makefile", "gnumakefile")),
    ("Node.js / npm", "#5FA04E", lambda p, n: n == "package.json"),
    ("Maven", "#C71A36", lambda p, n: n == "pom.xml"),
    ("Gradle", "#02303A", lambda p, n: n.startswith("build.gradle") or n.startswith("settings.gradle")),
    ("Python / pip", "#3776AB", lambda p, n: n in ("requirements.txt", "pyproject.toml", "setup.py", "pipfile")),
    ("Android", "#3DDC84", lambda p, n: n == "androidmanifest.xml" or p.startswith("android/") or "/android/" in p),
    ("iOS / Xcode", "#147EFB", lambda p, n: n == "podfile" or ".xcodeproj/" in p or p.startswith("ios/") or "/ios/" in p),
    ("SQL", "#e38c00", lambda p, n: n.endswith(".sql")),
    ("Firebase", "#FFCA28", lambda p, n: n.startswith("firebase") or n == "google-services.json"),
    ("Vercel / Netlify", "#a0a0a0", lambda p, n: n in ("vercel.json", "netlify.toml")),
    ("VS Code", "#007ACC", lambda p, n: p.startswith(".vscode/") or n.endswith((".code-workspace", ".vsix"))),
    ("Git hooks / config", "#F05032", lambda p, n: n in (".gitignore", ".gitattributes") or ".husky/" in p),
]
TOOL_COLORS = {name: color for name, color, _ in TOOLS}

K8S_KIND = re.compile(r"^\s*kind:\s*(Deployment|Service|Ingress|StatefulSet|DaemonSet|ConfigMap|Secret|Pod|CronJob|Job|Namespace|PersistentVolumeClaim|HorizontalPodAutoscaler)\b")

COMMANDS = set("""
ls cp mv rm mkdir rmdir chmod chown chgrp ln cat less grep egrep sed awk find xargs tar gzip gunzip zip unzip
curl wget ssh scp sftp rsync ssh-keygen ssh-copy-id systemctl service journalctl apt apt-get dpkg yum dnf apk snap brew
pip pip3 python python3 node npm npx yarn pnpm pm2 nvm deno bun git gh docker docker-compose podman kubectl helm minikube
kind k3s k9s kubeadm nginx certbot ufw iptables crontab useradd usermod groupadd passwd sudo su ps kill killall pkill top htop
df du free lsblk mount umount fdisk ip ifconfig netstat ss ping traceroute dig nslookup nmap openssl tmux screen nano vim vi
java javac mvn gradle gradlew psql pg_dump pg_restore createdb mysql mysqldump redis-cli mongo mongosh mongodump sqlite3
ffmpeg adb fastboot gcloud aws az terraform ansible ansible-playbook make cmake gcc g++ go cargo rustc tee touch head tail
sort uniq wc cut tr diff patch watch nohup timedatectl hostnamectl lsof chroot dd mkfs uname whoami hostname
code expo eas react-native pod xcodebuild flutter dart firebase vercel netlify wrangler supabase jq yq base64 sha256sum md5sum
""".split())

PATCH_PATHS = ["*.sh", "*.bash", "*.zsh", "*Dockerfile*", "*.dockerfile", "*.yml", "*.yaml", "*Makefile", "*.md", "*.service"]

COMMIT = re.compile(r"^@[0-9a-f]{40}$")
SEGMENT = re.compile(r"&&|\|\||;|\|")
PREFIX = re.compile(r"^(?:\$\s*|#\s+|sudo\s+(?:-\S+\s+)*|exec\s+|time\s+|nohup\s+|(?:[A-Z_][A-Z0-9_]*=\S*\s+)+)+")


class Tech:
    def __init__(self):
        self.tools = {}  # herramienta -> set de archivos
        self.commands = Counter()

    def add_path(self, repo, path):
        p, n = path.lower(), path.rsplit("/", 1)[-1].lower()
        for name, _, match in TOOLS:
            if match(p, n):
                self.tools.setdefault(name, set()).add(f"{repo}:{path}")

    def add_commands(self, text):
        for segment in SEGMENT.split(text):
            words = PREFIX.sub("", segment.strip()).split()
            if words:
                cmd = words[0].rsplit("/", 1)[-1].lower()
                if cmd in COMMANDS:
                    self.commands[cmd] += 1

    def scan_patch(self, repo, patch, commits, skip):
        """Recorre la salida de `git log -p` y procesa las líneas añadidas en commits de `commits`."""
        current, path, fenced = None, None, False
        for raw in patch.splitlines():
            if COMMIT.match(raw):
                current = raw[1:] if raw[1:] in commits else None
                continue
            if current is None:
                continue
            if raw.startswith("+++ "):
                path = raw[6:] if raw.startswith("+++ b/") else None
                path = None if path and skip(path) else path
                fenced = False
                continue
            if not path or not raw.startswith("+"):
                continue
            line, name = raw[1:].strip(), path.rsplit("/", 1)[-1].lower()
            if len(line) > 300:
                continue

            if name.endswith((".yml", ".yaml")) and K8S_KIND.match(line):
                self.tools.setdefault("Kubernetes", set()).add(f"{repo}:{path}")

            if name.endswith(".md"):
                if line.startswith("```"):
                    fenced = not fenced
                    continue
                if not fenced:
                    continue
            elif line.startswith("#"):
                continue

            if "dockerfile" in name:
                m = re.match(r"^(RUN|CMD|ENTRYPOINT)\s+(.*)", line, re.I)
                if not m:
                    continue
                line = m.group(2).strip("[]\"' ")
            elif name.endswith((".yml", ".yaml")):
                line = re.sub(r"^-?\s*(run|command|script|args)\s*:\s*[|>]?-?\s*", "", line)
                line = line.lstrip("- ").strip("\"'")
            elif name.endswith(".service"):
                m = re.match(r"^Exec\w*=\s*-?(.*)", line)
                if not m:
                    continue
                line = m.group(1)
            self.add_commands(line)


def chip_rows(items, width, x0=25, gap=10, char=7.2, pad=34):
    """Coloca chips de texto en filas; devuelve [(x, fila, ancho, item)]."""
    placed, x, row = [], x0, 0
    for item in items:
        w = pad + char * len(item[0])
        if x + w > width - x0:
            x, row = x0, row + 1
        placed.append((x, row, w, item))
        x += w + gap
    return placed, row + 1


def render(tech, lang, width=990):
    tools = sorted(((n, len(f)) for n, f in tech.tools.items()), key=lambda kv: -kv[1])
    commands = tech.commands.most_common(30)
    tool_items = [(f"{n} · {c} {t(lang, 'tech.file' if c == 1 else 'tech.files')}", TOOL_COLORS.get(n, "#8b949e")) for n, c in tools]
    cmd_items = [(f"{c}  ×{n:,}", "#8b949e") for c, n in commands]

    tool_chips, tool_rows = chip_rows(tool_items, width)
    cmd_chips, cmd_rows = chip_rows(cmd_items, width, char=7.4)
    y_tools = 92
    y_cmd_title = y_tools + tool_rows * 36 + 30
    y_cmds = y_cmd_title + 62
    height = y_cmds + cmd_rows * 36 + 20

    parts = []
    for x, row, w, (label, color) in tool_chips:
        y = y_tools + row * 36
        parts.append(
            f'<rect x="{x:.1f}" y="{y - 18}" width="{w:.1f}" height="26" rx="13" fill="#161b22" stroke="#30363d"/>'
            f'<circle cx="{x + 14:.1f}" cy="{y - 5}" r="5" fill="{color}"/>'
            f'<text x="{x + 25:.1f}" y="{y}" class="chip">{escape(label)}</text>'
        )
    for x, row, w, (label, _) in cmd_chips:
        y = y_cmds + row * 36
        parts.append(
            f'<rect x="{x:.1f}" y="{y - 18}" width="{w:.1f}" height="26" rx="6" fill="#161b22" stroke="#30363d"/>'
            f'<text x="{x + 12:.1f}" y="{y}" class="cmd">$ {escape(label)}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{t(lang, 'tech.label')}">
  <style>
    .title {{ font: 600 18px 'Segoe UI', Ubuntu, sans-serif; fill: #58a6ff; }}
    .sub {{ font: 400 12px 'Segoe UI', Ubuntu, sans-serif; fill: #8b949e; }}
    .chip {{ font: 400 13px 'Segoe UI', Ubuntu, sans-serif; fill: #c9d1d9; }}
    .cmd {{ font: 400 13px Consolas, 'SFMono-Regular', Menlo, monospace; fill: #7ee787; }}
  </style>
  <rect width="{width}" height="{height}" rx="4.5" fill="#0d1117"/>
  <text x="25" y="36" class="title">{t(lang, 'tech.tools.title')}</text>
  <text x="25" y="58" class="sub">{t(lang, 'tech.tools.sub')}</text>
  {"".join(p for p in parts[:len(tool_chips)])}
  <text x="25" y="{y_cmd_title}" class="title">{t(lang, 'tech.commands.title')}</text>
  <text x="25" y="{y_cmd_title + 22}" class="sub">{t(lang, 'tech.commands.sub')}</text>
  {"".join(p for p in parts[len(tool_chips):])}
</svg>
'''
