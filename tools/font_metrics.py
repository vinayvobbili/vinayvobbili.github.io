#!/usr/bin/env python3
"""Text widths of the site's Space Grotesk, so the diagram generator can size boxes without a browser.

`WIDTHS` holds each printable ASCII character's advance width (per 1000 em) for the 400 and 700
weights; characters the font lacks (arrows, subscripts) fall back to an average width. The table is
generated from assets/fonts/space-grotesk-*.woff2:

    uv run --with fonttools --with brotli python tools/font_metrics.py --regen    # rewrite the table below
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "assets" / "fonts"
FALLBACK = {400: 560, 700: 600}

# BEGIN GENERATED
WIDTHS: dict[int, dict[str, int]] = {
    400: {' ': 257, '!': 253, '"': 425, '#': 628, '$': 613, '%': 772, '&': 604, "'": 251, '(': 379, ')': 377, '*': 520, '+': 620, ',': 251, '-': 455, '.': 253, '/': 370, '0': 641, '1': 418, '2': 603, '3': 604, '4': 625, '5': 599, '6': 612, '7': 564, '8': 623, '9': 612, ':': 253, ';': 253, '<': 620, '=': 620, '>': 620, '?': 580, '@': 1026, 'A': 630, 'B': 661, 'C': 642, 'D': 663, 'E': 563, 'F': 540, 'G': 660, 'H': 656, 'I': 244, 'J': 594, 'K': 610, 'L': 546, 'M': 865, 'N': 664, 'O': 669, 'P': 601, 'Q': 669, 'R': 631, 'S': 613, 'T': 588, 'U': 666, 'V': 619, 'W': 875, 'X': 638, 'Y': 610, 'Z': 577, '[': 335, '\\': 370, ']': 335, '^': 620, '_': 620, '`': 280, 'a': 575, 'b': 644, 'c': 598, 'd': 644, 'e': 592, 'f': 442, 'g': 642, 'h': 613, 'i': 245, 'j': 247, 'k': 538, 'l': 245, 'm': 860, 'n': 613, 'o': 618, 'p': 644, 'q': 644, 'r': 377, 's': 527, 't': 460, 'u': 612, 'v': 539, 'w': 801, 'x': 593, 'y': 612, 'z': 521, '{': 432, '|': 240, '}': 432, '~': 620},
    700: {' ': 254, '!': 298, '"': 514, '#': 636, '$': 606, '%': 758, '&': 591, "'": 294, '(': 398, ')': 390, '*': 540, '+': 620, ',': 294, '-': 432, '.': 298, '/': 388, '0': 648, '1': 452, '2': 594, '3': 608, '4': 636, '5': 600, '6': 618, '7': 554, '8': 600, '9': 618, ':': 298, ';': 298, '<': 620, '=': 620, '>': 620, '?': 578, '@': 1014, 'A': 634, 'B': 664, 'C': 644, 'D': 666, 'E': 554, 'F': 534, 'G': 662, 'H': 656, 'I': 264, 'J': 610, 'K': 626, 'L': 542, 'M': 882, 'N': 670, 'O': 676, 'P': 604, 'Q': 676, 'R': 632, 'S': 606, 'T': 588, 'U': 672, 'V': 618, 'W': 898, 'X': 644, 'Y': 624, 'Z': 576, '[': 358, '\\': 388, ']': 358, '^': 620, '_': 620, '`': 296, 'a': 578, 'b': 638, 'c': 586, 'd': 638, 'e': 577, 'f': 436, 'g': 638, 'h': 616, 'i': 266, 'j': 268, 'k': 564, 'l': 266, 'm': 854, 'n': 616, 'o': 612, 'p': 638, 'q': 638, 'r': 396, 's': 524, 't': 456, 'u': 616, 'v': 548, 'w': 784, 'x': 592, 'y': 616, 'z': 518, '{': 466, '|': 258, '}': 466, '~': 620},
}
# END GENERATED


def text_width(text: str, size: float, weight: int = 700) -> float:
    """Rendered width of one line of text, in px, at the given font size."""
    table = WIDTHS.get(weight) or WIDTHS[700]
    return sum(table.get(ch, FALLBACK.get(weight, 600)) for ch in text) * size / 1000


def measure() -> dict[int, dict[str, int]]:
    """Advance widths read from the font files (needs fontTools)."""
    from fontTools.ttLib import TTFont
    out: dict[int, dict[str, int]] = {}
    for w in (400, 700):
        font = TTFont(FONTS / f"space-grotesk-{w}.woff2")
        cmap, hmtx, upm = font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm
        out[w] = {chr(c): round(hmtx[cmap[c]][0] * 1000 / upm) for c in range(32, 127) if c in cmap}
    return out


def render(table: dict[int, dict[str, int]]) -> str:
    rows = []
    for w, widths in table.items():
        body = ", ".join(f"{ch!r}: {v}" for ch, v in widths.items())
        rows.append(f"    {w}: {{{body}}},")
    return "WIDTHS: dict[int, dict[str, int]] = {\n" + "\n".join(rows) + "\n}"


def main(argv: list[str]) -> int:
    if "--regen" not in argv:
        print(__doc__)
        return 0
    path = Path(__file__)
    head, rest = path.read_text().split("# BEGIN GENERATED\n", 1)
    _, tail = rest.split("# END GENERATED\n", 1)
    path.write_text(head + "# BEGIN GENERATED\n" + render(measure()) + "\n# END GENERATED\n" + tail)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
