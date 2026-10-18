"""Genera el banner animado del perfil (assets/banner-<idioma>.gif).

Parte de la imagen estática assets/banner-source.jpg (la misma que usa el
portafolio para redes sociales) y anima dos zonas:
  - el saludo, con la mano 👋 moviéndose
  - el rol, que se escribe y se borra letra por letra
En inglés también reemplaza la línea "+9 años · ..." por su traducción.

No corre en GitHub Actions: usa fuentes de Windows (Consolas, Segoe UI y
Segoe UI Emoji). Se ejecuta a mano cuando cambia el texto del banner:

  pip install pillow
  python .github/scripts/banner.py           # los dos idiomas
  python .github/scripts/banner.py en        # solo uno
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SOURCE = os.path.join(ROOT, "assets", "banner-source.jpg")
FONTS = r"C:\Windows\Fonts"

CONTENT = {
    "es": {
        "hello": ("Hola ", ", soy"),
        "roles": ["Full Stack Developer", "Desarrollador Móvil", "Ingeniero de Sistemas"],
        "subtitle": None,  # la imagen original ya está en español
    },
    "en": {
        "hello": ("Hi ", ", I'm"),
        "roles": ["Full Stack Developer", "Mobile Developer", "Systems Engineer"],
        "subtitle": "+9 years · Web, mobile & infrastructure",
    },
}

BG = (10, 25, 48)
GREEN = (0x64, 0xFF, 0xDA)
ROLE_COLOR = (0x88, 0x92, 0xB0)
SUBTITLE_COLOR = (204, 216, 242)
SS = 4  # se dibuja a 4x y se reduce, para bordes suaves

# Posiciones medidas sobre la imagen original (1200x630)
HELLO_X, HELLO_CAP_TOP, HELLO_BOX = 81, 132, (70, 112, 420, 172)
ROLE_X, ROLE_CAP_TOP, ROLE_BOX = 83, 295, (70, 282, 720, 348)
SUBTITLE_X, SUBTITLE_CAP_TOP, SUBTITLE_BOX = 83, 366, (70, 352, 720, 400)

# Tiempos de la animación (ms)
FRAME_MS = 50
TYPE_MS, DELETE_MS, HOLD_MS, GAP_MS = 70, 35, 2200, 300
WAVE_MS = 2500
WAVE_KEYS = [(0, 0), (.10, 14), (.20, -8), (.30, 14), (.40, -4), (.50, 10), (.60, 0), (1, 0)]


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), int(size * SS))


MONO = font("consola.ttf", 27)
EMOJI = font("seguiemj.ttf", 30)
SUBTITLE_FONT = font("segoeui.ttf", 26.5)


def fit_role_font():
    # Tamaño con el que "Full Stack Developer" ocupa lo mismo que en la imagen original (83..486 px)
    for size in range(30, 60):
        f = font("seguisb.ttf", size)
        left, _, right, _ = f.getbbox("Full Stack Developer", anchor="ls")
        if (right - left) / SS >= 486 - 83:
            return f
    raise RuntimeError("No se encontró un tamaño para el rol")


ROLE_FONT = fit_role_font()


def baseline(f, cap_top, box_top):
    """Línea base para que la parte de arriba de las mayúsculas quede en cap_top."""
    return cap_top * SS - f.getbbox("H", anchor="ls")[1] - box_top * SS


def canvas(box, mode="RGB"):
    x0, y0, x1, y1 = box
    color = BG + (255,) if mode == "RGBA" else BG
    return Image.new(mode, ((x1 - x0) * SS, (y1 - y0) * SS), color)


def shrink(img, box):
    return img.convert("RGB").resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS)


def hand_image():
    left, top, right, bottom = EMOJI.getbbox("👋")
    hand = Image.new("RGBA", (right - left, bottom - top))
    ImageDraw.Draw(hand).text((-left, -top), "👋", font=EMOJI, embedded_color=True)
    return hand


HAND = hand_image()


def wave_angle(t):
    for (t0, a0), (t1, a1) in zip(WAVE_KEYS, WAVE_KEYS[1:]):
        if t <= t1:
            p = (t - t0) / (t1 - t0)
            return a0 + (a1 - a0) * p * p * (3 - 2 * p)
    return 0


def render_hello(texts, angle):
    before, after = texts
    img = canvas(HELLO_BOX, "RGBA")
    d = ImageDraw.Draw(img)
    base = baseline(MONO, HELLO_CAP_TOP, HELLO_BOX[1])
    x = (HELLO_X - HELLO_BOX[0]) * SS - MONO.getbbox("H", anchor="ls")[0]
    d.text((x, base), before, font=MONO, fill=GREEN, anchor="ls")
    hand_x = x + MONO.getlength(before)
    hw, hh = HAND.size
    hand = HAND.rotate(-angle, resample=Image.BICUBIC, center=(hw * .7, hh * .7))
    img.alpha_composite(hand, (int(hand_x), int(base - hh + 6 * SS)))
    d.text((hand_x + hw + 2 * SS, base), after, font=MONO, fill=GREEN, anchor="ls")
    return shrink(img, HELLO_BOX)


def render_role(text, cursor):
    img = canvas(ROLE_BOX)
    d = ImageDraw.Draw(img)
    base = baseline(ROLE_FONT, ROLE_CAP_TOP, ROLE_BOX[1])
    x = (ROLE_X - ROLE_BOX[0]) * SS - ROLE_FONT.getbbox("F", anchor="ls")[0]
    if text:
        d.text((x, base), text, font=ROLE_FONT, fill=ROLE_COLOR, anchor="ls")
    if cursor:
        cx = x + ROLE_FONT.getlength(text) + 6 * SS
        top = base + ROLE_FONT.getbbox("H", anchor="ls")[1]
        d.rectangle([cx, top, cx + 3 * SS, base + 2 * SS], fill=ROLE_COLOR)
    return shrink(img, ROLE_BOX)


def render_subtitle(text):
    img = canvas(SUBTITLE_BOX)
    base = baseline(SUBTITLE_FONT, SUBTITLE_CAP_TOP, SUBTITLE_BOX[1])
    x = (SUBTITLE_X - SUBTITLE_BOX[0]) * SS - SUBTITLE_FONT.getbbox("+", anchor="ls")[0]
    ImageDraw.Draw(img).text((x, base), text, font=SUBTITLE_FONT, fill=SUBTITLE_COLOR, anchor="ls")
    return shrink(img, SUBTITLE_BOX)


def role_timeline(roles):
    """Lista de (texto visible, duración en ms) para escribir y borrar cada rol."""
    steps = []
    for role in roles:
        steps += [(role[:n], TYPE_MS) for n in range(1, len(role) + 1)]
        steps.append((role, HOLD_MS))
        steps += [(role[:n], DELETE_MS) for n in range(len(role) - 1, -1, -1)]
        steps.append(("", GAP_MS))
    return steps


def role_at(steps, ms):
    """Texto y si se ve el cursor (parpadea mientras el rol está completo)."""
    elapsed = 0
    for text, duration in steps:
        if ms < elapsed + duration:
            holding = duration == HOLD_MS
            return text, not holding or int((ms - elapsed) / 500) % 2 == 0
        elapsed += duration
    return "", True


def build(lang):
    content = CONTENT[lang]
    src = Image.open(SOURCE).convert("RGB")
    if content["subtitle"]:
        src.paste(render_subtitle(content["subtitle"]), SUBTITLE_BOX[:2])

    # Paleta común: 200 colores para la foto y 56 para lo animado (si no, la mano pierde los amarillos).
    # La foto se trama una sola vez, así queda idéntica en todos los cuadros.
    sample = src.copy()
    sample.paste(render_hello(content["hello"], 0), HELLO_BOX[:2])
    sample.paste(render_role(content["roles"][0], True), ROLE_BOX[:2])
    photo_palette = src.quantize(colors=200, method=Image.MEDIANCUT).getpalette()[:200 * 3]
    height = HELLO_BOX[3] - HELLO_BOX[1]
    animated = Image.new("RGB", (HELLO_BOX[2] - HELLO_BOX[0], 2 * height))
    animated.paste(render_hello(content["hello"], 0), (0, 0))
    animated.paste(render_hello(content["hello"], 14), (0, height))
    animated_palette = animated.quantize(colors=56, method=Image.MEDIANCUT).getpalette()[:56 * 3]
    palette = Image.new("P", (1, 1))
    palette.putpalette(photo_palette + animated_palette)
    base = sample.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG)

    steps = role_timeline(content["roles"])
    total = sum(duration for _, duration in steps)
    frames = []
    for ms in range(0, total, FRAME_MS):
        text, cursor = role_at(steps, ms)
        frame = base.copy()
        hello = render_hello(content["hello"], wave_angle((ms % WAVE_MS) / WAVE_MS))
        frame.paste(hello.quantize(palette=palette, dither=Image.Dither.NONE), HELLO_BOX[:2])
        frame.paste(render_role(text, cursor).quantize(palette=palette, dither=Image.Dither.NONE), ROLE_BOX[:2])
        frames.append(frame)

    out = os.path.join(ROOT, "assets", f"banner-{lang}.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=FRAME_MS, loop=0, optimize=True)
    print(f"{os.path.relpath(out, ROOT)}: {len(frames)} cuadros, {total / 1000:.1f} s")


def main():
    langs = sys.argv[1:] or list(CONTENT)
    for lang in langs:
        if lang not in CONTENT:
            sys.exit(f"Idioma desconocido: {lang} (opciones: {', '.join(CONTENT)})")
        build(lang)


if __name__ == "__main__":
    main()
