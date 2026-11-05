"""Concept exploration for the SNOMNIMAN mark (round 3).

Design brief: preserve the *construction logic* of the reference mark, not a
letterform. Measured anatomy of the reference (Omniman_logo.png, 726x862):

- mass: a solid 726x424 stadium (corner radius = half its height)
- bar:  49 px wide (11.5% of the mass height), perfectly vertical, full height
- slit: exactly the bar's width, rounded ends, and it OVERSHOOTS the mass
  edges by ~14 px - the bar and the mass never touch; the slit is the bar's
  track rendered in negative, cutting clean through the silhouette.

Everything here is compass-and-ruler: circles, stadiums, quarter/half arcs,
one constant stroke weight per concept, one flat red. Outputs land in
``packaging/concepts/`` (1024 transparent + white-card + 64/32/16 previews).
Exploration only - nothing is wired into the build.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

RED = (192, 0, 0, 255)  # sampled from the reference
S = 1024
SS = 4  # supersample factor; drawn at 4096, downscaled with Lanczos
C = S * SS
OUT = Path(__file__).parent / "concepts"


def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("L", (C, C), 0)
    return img, ImageDraw.Draw(img)


def z(v: float) -> int:
    return round(v * SS)


def arc(d, cx, cy, r, start, end, w, fill=255):
    """Thick circular arc, stroke centered on radius r."""
    bbox = [z(cx - r - w / 2), z(cy - r - w / 2), z(cx + r + w / 2), z(cy + r + w / 2)]
    d.arc(bbox, start, end, fill=fill, width=z(w))


def dot(d, x, y, r, fill=255):
    d.ellipse([z(x - r), z(y - r), z(x + r), z(y + r)], fill=fill)


def rect(d, x0, y0, x1, y1, fill=255):
    d.rectangle([z(x0), z(y0), z(x1), z(y1)], fill=fill)


def stadium(d, x0, y0, x1, y1, fill=255):
    d.rounded_rectangle([z(x0), z(y0), z(x1), z(y1)], radius=z((y1 - y0) / 2), fill=fill)


def slit(d, cx, y0, y1, w):
    """The reference's cut: a rounded-end track, erased."""
    d.rounded_rectangle([z(cx - w / 2), z(y0), z(cx + w / 2), z(y1)], radius=z(w / 2), fill=0)


def finish(mask: Image.Image, name: str) -> None:
    OUT.mkdir(exist_ok=True)
    mask = mask.resize((S, S), Image.LANCZOS)
    mark = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mark = Image.composite(Image.new("RGBA", (S, S), RED), mark, mask)
    mark.save(OUT / f"{name}.png")
    white = Image.new("RGBA", (S, S), (255, 255, 255, 255))
    white.alpha_composite(mark)
    white.convert("RGB").save(OUT / f"{name}_white.png")
    for sz in (64, 32, 16):
        small = Image.new("RGBA", (sz, sz), (255, 255, 255, 255))
        small.alpha_composite(mark.resize((sz, sz), Image.LANCZOS))
        small.convert("RGB").save(OUT / f"{name}_{sz}.png")
    print(f"rendered {name}")


# ---------------------------------------------------------------------------
# Concept A - COMPASS CUT
# Two identical circles stacked tangent. The top circle keeps three quadrants
# (drops its lower-right); the bottom mirrors it (drops its upper-left). One
# stroke width; round caps at the two free ends. The needle passes BEHIND the
# form: visible only where it emerges above and below, plus one slit at the
# waist where the circles meet. (v1 ran the needle through the eyes - that
# made it a dollar sign; the needle must never be visible inside the loops.)
# ---------------------------------------------------------------------------
def concept_a() -> None:
    img, d = canvas()
    W = 170
    R = 190
    arc(d, 512, 322, R, 90, 360, W)   # top circle: omit SE quadrant
    arc(d, 512, 702, R, 270, 180, W)  # bottom circle: omit NW quadrant
    dot(d, 512 + R, 322, W / 2)       # top terminal (east point)
    dot(d, 512 - R, 702, W / 2)       # bottom terminal (west point)
    rect(d, 512 - 52, 16, 512 + 52, 140)           # needle tip, emerging above
    rect(d, 512 - 52, 884, 512 + 52, 1008)         # needle tip, emerging below
    slit(d, 512, 427 - 14, 597 + 14, 104)          # one cut at the waist
    finish(img, "concept_a")


# ---------------------------------------------------------------------------
# Concept B - STENCIL SPLIT
# A solid S built like a drafted stencil: three horizontal rails joined by two
# half-circle U-turns, one chunky stroke weight. Then the reference treatment
# verbatim: one continuous vertical slit severs the whole form at center; the
# bar is visible only above and below. The S and the bar never touch.
# ---------------------------------------------------------------------------
def concept_b() -> None:
    img, d = canvas()
    W = 190
    r = 137
    rect(d, 352, 238 - W / 2, 717, 238 + W / 2)    # top rail
    dot(d, 717, 238, W / 2)
    arc(d, 352, 375, r, 90, 270, W)                # left U-turn
    rect(d, 352, 512 - W / 2, 672, 512 + W / 2)    # middle rail
    arc(d, 672, 649, r, 270, 90, W)                # right U-turn
    rect(d, 287, 786 - W / 2, 672, 786 + W / 2)    # bottom rail
    dot(d, 287, 786, W / 2)
    rect(d, 512 - 52, 20, 512 + 52, 200)           # bar tip, above
    rect(d, 512 - 52, 824, 512 + 52, 1004)         # bar tip, below
    slit(d, 512, 129, 895, 104)                    # one continuous cut
    finish(img, "concept_b")


# ---------------------------------------------------------------------------
# Concept C - INTEGRAL
# The reference construction almost verbatim: one solid stadium mass, one
# straight vertical, one overshooting slit. The S lives entirely in the
# piercing element: its exposed ends hook in opposite directions (an integral
# sign), while the cut through the mass stays perfectly straight.
# ---------------------------------------------------------------------------
def concept_c() -> None:
    img, d = canvas()
    stadium(d, 122, 284, 902, 740)                 # the mass (780 x 456)
    bw = 72
    rect(d, 512 - bw / 2, 120, 512 + bw / 2, 904)  # trunk
    arc(d, 592, 120, 80, 180, 270, bw)             # top hook (curls east)
    rect(d, 592, 40 - bw / 2, 640, 40 + bw / 2)
    dot(d, 640, 40, bw / 2)
    arc(d, 432, 904, 80, 0, 90, bw)                # bottom hook (curls west)
    rect(d, 384, 984 - bw / 2, 432, 984 + bw / 2)
    dot(d, 384, 984, bw / 2)
    slit(d, 512, 284 - 14, 740 + 14, bw)           # the straight cut
    finish(img, "concept_c")


# ---------------------------------------------------------------------------
# Concept D - DEFLECTED BEAM
# The inverse of C: the mass and the straight verticals stay, and the S is
# the cut itself. A bar enters top-right, its track S-curves through the mass
# (the same two-circle construction as A, in negative), and exits bottom-left.
# 180-degree rotationally symmetric, like the reference. The straight entry/
# exit cuts butt flat against the S-track's terminals (whose tangents are
# exactly vertical there, by construction), so the track is seamless.
# ---------------------------------------------------------------------------
def concept_d() -> None:
    img, d = canvas()
    stadium(d, 122, 228, 902, 796)                 # the mass (780 x 568)
    cw = 80                                        # channel / bar width
    R = 110
    tc, bc = (512, 402), (512, 622)                # tangent circles
    ex, wx = 512 + R, 512 - R                      # entry / exit x
    rect(d, ex - cw / 2, 40, ex + cw / 2, 360)     # entry bar (drawn long)
    rect(d, wx - cw / 2, 664, wx + cw / 2, 984)    # exit bar (drawn long)
    # carve the white track: straight in, serpentine through, straight out
    rect(d, ex - cw / 2, 254, ex + cw / 2, 402, fill=0)   # entry cut
    dot(d, ex, 254, cw / 2, fill=0)                        # its rounded outer end
    arc(d, *tc, R, 90, 360, cw, fill=0)            # top loop of the S-track
    arc(d, *bc, R, 270, 180, cw, fill=0)           # bottom loop
    rect(d, wx - cw / 2, 622, wx + cw / 2, 770, fill=0)   # exit cut
    dot(d, wx, 770, cw / 2, fill=0)                        # its rounded outer end
    finish(img, "concept_d")


if __name__ == "__main__":
    concept_a()
    concept_b()
    concept_c()
    concept_d()
