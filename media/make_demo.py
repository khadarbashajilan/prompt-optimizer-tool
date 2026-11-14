"""Record the real CLI into media/demo.gif (no screenshots, no mock output).

Runs the command you give it, captures its actual coloured output, and
renders it as a terminal-style GIF: the command is typed, then the output
appears. Needs Pillow (`uv run --with pillow python media/make_demo.py`).

    # needs your provider key exported, e.g. GEMINI_API_KEY
    uv run --with pillow python media/make_demo.py \
        'plint "write code in python to fetch api data"'
    uv run --with pillow python media/make_demo.py --out /tmp/x.gif 'plint list'
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
SIZE, PAD, COLS = 15, 18, 80
BG, FG = (24, 24, 32), (220, 220, 230)
ANSI16 = [(0, 0, 0), (205, 49, 49), (13, 188, 121), (229, 229, 16), (36, 114, 200),
          (188, 63, 188), (17, 168, 205), (229, 229, 229), (102, 102, 102), (241, 76, 76),
          (35, 209, 139), (245, 245, 67), (59, 142, 234), (214, 112, 214), (41, 184, 219),
          (255, 255, 255)]
CSI = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])")


def color256(n: int) -> tuple[int, int, int]:
    if n < 16:
        return ANSI16[n]
    if n < 232:
        n -= 16
        return tuple(0 if c == 0 else 55 + 40 * c for c in (n // 36, n // 6 % 6, n % 6))
    v = 8 + 10 * (n - 232)
    return (v, v, v)


def parse(text: str) -> list[list[tuple[str, tuple, bool]]]:
    """ANSI text -> lines of (char, colour, bold). Cursor codes are dropped."""
    lines: list[list] = [[]]
    fg, bold, pos = FG, False, 0
    text = text.replace("\r\n", "\n")
    for m in CSI.finditer(text):
        _emit(text[pos:m.start()], lines, fg, bold)
        pos = m.end()
        if m.group(2) != "m":
            continue
        codes = [int(c) if c else 0 for c in m.group(1).split(";")]
        i = 0
        while i < len(codes):
            c = codes[i]
            if c == 0:
                fg, bold = FG, False
            elif c == 1:
                bold = True
            elif c == 22:
                bold = False
            elif 30 <= c <= 37:
                fg = ANSI16[c - 30]
            elif 90 <= c <= 97:
                fg = ANSI16[c - 82]
            elif c == 39:
                fg = FG
            elif c == 38 and codes[i + 1:i + 2] == [5]:
                fg = color256(codes[i + 2]); i += 2
            elif c == 38 and codes[i + 1:i + 2] == [2]:
                fg = tuple(codes[i + 2:i + 5]); i += 4
            i += 1
    _emit(text[pos:], lines, fg, bold)
    return lines


def _emit(chunk: str, lines: list, fg: tuple, bold: bool) -> None:
    for ch in chunk:
        if ch == "\n":
            lines.append([])
        elif ch == "\r":
            lines[-1].clear()  # spinner redraw: keep only the last paint
        elif ch >= " ":
            lines[-1].append((ch, fg, bold))


def render(lines: list, height: int, fonts, cw: int, ch: int) -> Image.Image:
    img = Image.new("RGB", (COLS * cw + 2 * PAD, height * ch + 2 * PAD), BG)
    d = ImageDraw.Draw(img)
    for y, line in enumerate(lines[-height:]):
        for x, (c, fg, bold) in enumerate(line[:COLS]):
            d.text((PAD + x * cw, PAD + y * ch), c, fill=fg, font=fonts[bold])
    return img


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", help="shell command to record, e.g. 'plint list'")
    ap.add_argument("--out", default="media/demo.gif")
    ap.add_argument("--rows", type=int, default=44)
    args = ap.parse_args()

    env = {**os.environ, "FORCE_COLOR": "1", "COLUMNS": str(COLS), "TERM": "xterm-256color"}
    done = subprocess.run(args.command, shell=True, env=env, capture_output=True, text=True)
    output = done.stdout + done.stderr

    fonts = (ImageFont.truetype(FONT, SIZE), ImageFont.truetype(FONT, SIZE))
    cw = int(fonts[0].getlength("M")); ch = SIZE + 5
    prompt = parse(f"\x1b[32m$\x1b[0m {args.command}")[0]
    body = parse(output)
    rows = min(args.rows, len(body) + 3)
    frames, times = [], []

    step = max(1, len(prompt) // 22)
    for n in range(2, len(prompt) + step, step):
        frames.append(render([prompt[:n]], rows, fonts, cw, ch)); times.append(60)
    times[-1] = 500
    # reveal output a few lines at a time, always showing the final screen last
    for n in range(0, len(body), 6):
        frames.append(render([prompt, []] + body[:n], rows, fonts, cw, ch)); times.append(90)
    frames.append(render([prompt, []] + body, rows, fonts, cw, ch)); times.append(4000)

    frames[0].save(args.out, save_all=True, append_images=frames[1:], duration=times, loop=0, optimize=True)
    print(f"Wrote {args.out}: {len(frames)} frames, {Path(args.out).stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
