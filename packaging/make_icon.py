"""Generate the SNOMNIMAN application icon (``packaging/snomniman.ico``).

A one-off asset-generation script, not part of the application or the build
itself - run manually whenever the icon needs regenerating. Draws a simple,
recognizable mark (a probe tip meeting a near-field wave) rather than
depending on an external design tool, since no icon asset existed before this
packaging milestone (deployment-strategy.md Section 2.4).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

BACKGROUND = (17, 19, 23, 255)  # matches gui/app.py's pg background "#111317"
TIP = (200, 200, 200, 255)  # matches gui/app.py's pg foreground "#c8c8c8"
WAVE = (79, 209, 197, 255)  # a teal accent evocative of optical near-field work


def _draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = round(size * 0.06)
    radius = round(size * 0.18)
    draw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, fill=BACKGROUND)

    cx = size / 2
    apex_y = size * 0.22
    base_y = size * 0.52
    half_width = size * 0.11
    draw.polygon(
        [(cx, apex_y), (cx - half_width, base_y), (cx + half_width, base_y)],
        fill=TIP,
    )

    center = (cx, base_y)
    max_radius = size * 0.34
    n_arcs = 3
    width = max(1, round(size * 0.035))
    for i in range(n_arcs):
        r = max_radius * (i + 1) / n_arcs
        bbox = [center[0] - r, center[1] - r, center[0] + r, center[1] + r]
        draw.arc(bbox, start=20, end=160, fill=WAVE, width=width)

    return img


def main() -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [_draw(s) for s in sizes]
    out = Path(__file__).parent / "snomniman.ico"
    images[-1].save(out, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
