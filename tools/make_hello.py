"""Generate the animated SVGs for the GitHub profile README.

    hello-<theme>.svg     "Hey folks, I'm Archie" types out once, then a hand waves
    laptop-<theme>.svg    a small laptop whose screen fills with code, clears, repeats
    terminal-<theme>.svg  a prompt that loops through commands and short replies

Pure SVG + CSS keyframes. No scripts, no external fonts or images, so they render
inside GitHub's image proxy with no third-party dependency. Characters sit on a fixed
grid, so the typing lines up whatever monospace font the viewer has.

Run from the repo root:  python3 tools/make_hello.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

HEADLINE = "Hey folks, I'm Archie"
WAVE = "\U0001F44B"  # waving hand
PROMPT = "archie@lab:~$"
PAIRS = [
    ("whoami", "builds secure networks, cloud and AI guardrails"),
    ("show bgp summary", "peers OPNsense and VyOS with Google Cloud over eBGP"),
    ("terraform plan", "keeps the cloud side as code, zero destroys"),
    ("triage --from grafana", "brings evidence, not verdicts"),
    ("drift-keel compliance audit", "audits devices against STIG, changes nothing"),
    ("git log --oneline -1", "agent drafts the change, a human approves it"),
]

THEMES = {
    "dark": {"head": "#E8EEF3", "prompt": "#1BA48D", "cmd": "#56A4DC", "out": "#9AA8B3", "cursor": "#56A4DC"},
    "light": {"head": "#17232B", "prompt": "#12806E", "cmd": "#2371A9", "out": "#5D6A74", "cursor": "#2371A9"},
}

MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace"
EMOJI = "'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif"
X0 = 4

# Headline image
HEAD_FS, HEAD_CW, HEAD_Y = 30, 18.0, 40
HEAD_START, HEAD_STEP = 0.3, 0.07
HELLO_W, HELLO_H = 460, 56

# Terminal image
LINE_FS, LINE_CW = 16, 9.6
CMD_Y, OUT_Y = 20, 48
TERM_W, TERM_H = 500, 58
LOOP_DELAY = 0.8
TYPE_STEP, OUT_PAUSE, HOLD, GAP = 0.075, 0.35, 2.6, 0.35

REDUCED = "@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}{show}{{opacity:1}}.cur{{display:none}}}}"
COMMON = "@keyframes show{to{opacity:1}}@keyframes hide{to{opacity:0}}@keyframes blink{0%{opacity:1}50%{opacity:0}}"


def pct(t: float, total: float) -> str:
    return f"{min(max(t / total * 100, 0), 100):.3f}%"


def window_keyframes(name: str, on: float, off: float, total: float) -> str:
    """Opacity 0 -> 1 at `on`, back to 0 at `off`, inside one loop of `total` seconds."""
    eps = 0.001
    return (
        f"@keyframes {name}{{0%,{pct(on - eps, total)}{{opacity:0}}"
        f"{pct(on, total)},{pct(off - eps, total)}{{opacity:1}}"
        f"{pct(off, total)},100%{{opacity:0}}}}"
    )


def svg(width: int, height: int, title: str, css: str, body: list[str]) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="t">'
        f'<title id="t">{escape(title)}</title><style>{css}</style>' + "".join(body) + "</svg>\n"
    )


def build_hello(theme: dict[str, str]) -> str:
    css, body = [], []
    done = HEAD_START + HEAD_STEP * len(HEADLINE)
    for i, ch in enumerate(HEADLINE):
        if ch == " ":
            continue
        css.append(f".h{i}{{animation:show 0.01s linear {HEAD_START + HEAD_STEP * i:.3f}s forwards}}")
        body.append(f'<text class="hc h{i}" x="{X0 + i * HEAD_CW:.1f}" y="{HEAD_Y}">{escape(ch)}</text>')

    # Cursor follows the typing, then leaves as the hand arrives.
    span = done + 0.5
    steps = "".join(
        f"{pct(HEAD_START + HEAD_STEP * i, span)}{{transform:translateX({i * HEAD_CW:.1f}px)}}"
        for i in range(len(HEADLINE) + 1)
    )
    css.append(f"@keyframes hmove{{0%{{transform:translateX(0)}}{steps}100%{{transform:translateX({len(HEADLINE) * HEAD_CW:.1f}px)}}}}")
    css.append(f".cur{{animation:hmove {span:.3f}s steps(1,end) forwards}}")
    css.append(f".cur rect{{animation:blink 0.9s steps(1,end) infinite, hide 0.01s linear {span:.3f}s forwards}}")
    body.append(f'<g class="cur"><rect x="{X0}" y="{HEAD_Y - 26}" width="3" height="32" fill="{theme["cursor"]}"/></g>')

    # Waving hand: appears after the name, waves, rests, waves again.
    hx = X0 + (len(HEADLINE) + 1) * HEAD_CW
    css.append(
        ".wave{opacity:0;transform-box:fill-box;transform-origin:70% 85%;"
        f"animation:show 0.01s linear {span:.3f}s forwards, wave 3s ease-in-out {span:.3f}s infinite}}"
        "@keyframes wave{0%{transform:rotate(0)}8%{transform:rotate(16deg)}16%{transform:rotate(-8deg)}"
        "24%{transform:rotate(16deg)}32%{transform:rotate(-4deg)}40%{transform:rotate(12deg)}"
        "50%,100%{transform:rotate(0)}}"
    )
    body.append(f'<text class="wave" x="{hx:.1f}" y="{HEAD_Y - 1}">{WAVE}</text>')

    base = (
        f"text{{white-space:pre}}"
        f".hc{{font-family:{MONO};font-size:{HEAD_FS}px;font-weight:700;fill:{theme['head']};opacity:0}}"
        f".wave{{font-family:{EMOJI};font-size:{HEAD_FS}px}}"
    )
    reduced = REDUCED.format(show=".hc,.wave")
    return svg(HELLO_W, HELLO_H, f"{HEADLINE} {WAVE}", base + COMMON + "".join(css) + reduced, body)


def build_terminal(theme: dict[str, str]) -> str:
    """Each command and reply pair is centred as a block, so short pairs sit in the middle too."""
    css, body = [], []
    widest = max(max(len(PROMPT) + 1 + len(c), len(o)) for c, o in PAIRS) * LINE_CW
    if widest > TERM_W - 2:
        raise ValueError(f"a line is {widest:.0f}px wide; keep it under {TERM_W - 2}px (about 50 characters)")

    starts, t = [], 0.0
    for cmd, _ in PAIRS:
        starts.append(t)
        t += len(cmd) * TYPE_STEP + OUT_PAUSE + HOLD + GAP
    total = t

    moves = []
    for k, (cmd, out) in enumerate(PAIRS):
        s = starts[k]
        typed = s + len(cmd) * TYPE_STEP
        end = typed + OUT_PAUSE + HOLD
        block = max(len(PROMPT) + 1 + len(cmd), len(out)) * LINE_CW
        bx = (TERM_W - block) / 2
        px = bx + (len(PROMPT) + 1) * LINE_CW

        name = f"p{k}"
        css.append(window_keyframes(name, s, end, total))
        css.append(f".{name}{{animation:{name} {total:.3f}s linear {LOOP_DELAY:.3f}s infinite}}")
        body.append(f'<text class="pc {name}" x="{bx:.1f}" y="{CMD_Y}">{escape(PROMPT)}</text>')

        for j, ch in enumerate(cmd):
            moves.append(f"{pct(s + j * TYPE_STEP, total)}{{transform:translateX({px + j * LINE_CW:.1f}px)}}")
            if ch == " ":
                continue
            name = f"c{k}_{j}"
            css.append(window_keyframes(name, s + (j + 1) * TYPE_STEP, end, total))
            css.append(f".{name}{{animation:{name} {total:.3f}s linear {LOOP_DELAY:.3f}s infinite}}")
            body.append(f'<text class="cc {name}" x="{px + j * LINE_CW:.1f}" y="{CMD_Y}">{escape(ch)}</text>')
        moves.append(f"{pct(typed, total)}{{transform:translateX({px + len(cmd) * LINE_CW:.1f}px)}}")

        name = f"o{k}"
        css.append(window_keyframes(name, typed + OUT_PAUSE, end, total))
        css.append(f".{name}{{animation:{name} {total:.3f}s linear {LOOP_DELAY:.3f}s infinite}}")
        body.append(f'<text class="oc {name}" x="{bx:.1f}" y="{OUT_Y}">{escape(out)}</text>')

    # The cursor is hidden in the gap between pairs and follows the typing inside each one.
    first_x = moves[0].split("translateX(")[1].split("px")[0]
    css.append("@keyframes cmove{0%{transform:translateX(" + first_x + "px)}" + "".join(moves) + "}")
    css.append(f".cur g{{animation:cmove {total:.3f}s steps(1,end) {LOOP_DELAY:.3f}s infinite}}")
    css.append(".cur rect{animation:blink 0.9s steps(1,end) infinite}")
    vis = "".join(
        f"{pct(starts[k], total)}{{opacity:1}}"
        f"{pct(starts[k] + len(c) * TYPE_STEP + OUT_PAUSE + HOLD, total)}{{opacity:0}}"
        for k, (c, _) in enumerate(PAIRS)
    )
    css.append("@keyframes cvis{0%{opacity:0}" + vis + "100%{opacity:0}}")
    css.append(f".cur{{opacity:0;animation:cvis {total:.3f}s steps(1,end) {LOOP_DELAY:.3f}s infinite}}")
    body.append(
        f'<g class="cur"><g><rect x="0" y="{CMD_Y - 13}" width="9" height="17" '
        f'fill="{theme["cursor"]}" opacity="0.85"/></g></g>'
    )

    base = (
        f"text{{font-family:{MONO};font-size:{LINE_FS}px;white-space:pre}}"
        f".pc{{fill:{theme['prompt']};opacity:0}}"
        f".cc{{fill:{theme['cmd']};opacity:0}}"
        f".oc{{fill:{theme['out']};opacity:0}}"
    )
    first = ",".join(f".c0_{j}" for j, ch in enumerate(PAIRS[0][0]) if ch != " ")
    reduced = REDUCED.format(show=f".p0,.o0,{first}")
    title = " ".join(f"$ {c}: {o}." for c, o in PAIRS)
    return svg(TERM_W, TERM_H, title, base + COMMON + "".join(css) + reduced, body)


LAPTOP_BODY = {"dark": ("#8B98A5", "#5F6B76"), "light": ("#4A5560", "#2F3840")}
# Code rows on the laptop screen: (indent, [(width, colour), ...])
CODE_ROWS = [
    (0, [(7, "#56A4DC"), (14, "#1BA48D")]),
    (4, [(10, "#9AA8B3"), (8, "#56A4DC")]),
    (4, [(17, "#1BA48D")]),
    (8, [(6, "#E3B341"), (11, "#9AA8B3")]),
    (4, [(9, "#56A4DC"), (6, "#1BA48D")]),
    (0, [(5, "#56A4DC")]),
]


def build_laptop(theme_name: str) -> str:
    body_fill, deck_fill = LAPTOP_BODY[theme_name]
    css, body = [], []
    # Lid and screen. The screen is dark in both themes, like an editor.
    body.append(f'<rect x="9" y="1" width="46" height="31" rx="2.5" fill="{body_fill}"/>')
    body.append('<rect x="11.5" y="3.5" width="41" height="26" rx="1" fill="#0D1117"/>')
    # Deck, keys and trackpad.
    body.append(f'<path d="M7 33 H57 L63 40.5 Q63 42 61.5 42 H2.5 Q1 42 1 40.5 Z" fill="{deck_fill}"/>')
    for r, (y, x0, n) in enumerate([(34.6, 10.5, 12), (36.6, 9.0, 13)]):
        for k in range(n):
            body.append(f'<rect x="{x0 + k * 3.6:.1f}" y="{y}" width="2.6" height="1.2" rx="0.3" fill="{body_fill}" opacity="0.7"/>')
    body.append(f'<rect x="27" y="38.8" width="10" height="1.8" rx="0.5" fill="{body_fill}" opacity="0.7"/>')

    # Code segments appear one after another, hold, then the screen clears.
    segs = []
    for row, (indent, parts) in enumerate(CODE_ROWS):
        x = 14 + indent
        for w, colour in parts:
            segs.append((x, 6 + row * 3.9, w, colour))
            x += w + 2
    step, hold = 0.32, 1.6
    total = len(segs) * step + hold + 0.5
    for i, (x, y, w, colour) in enumerate(segs):
        name = f"s{i}"
        css.append(window_keyframes(name, 0.3 + i * step, len(segs) * step + hold, total))
        css.append(f".{name}{{animation:{name} {total:.3f}s linear infinite}}")
        body.append(f'<rect class="seg {name}" x="{x}" y="{y:.1f}" width="{w}" height="2.2" rx="0.8" fill="{colour}"/>')
    # Blinking cursor in the corner of the screen.
    css.append(".cur{animation:blink 0.9s steps(1,end) infinite}")
    body.append('<rect class="cur" x="47" y="25" width="3" height="2.4" fill="#56A4DC"/>')

    base = ".seg{opacity:0}"
    reduced = REDUCED.format(show=".seg")
    return svg(64, 43, "A laptop typing code", base + COMMON + "".join(css) + reduced, body)


def main(out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, theme in THEMES.items():
        (out / f"hello-{name}.svg").write_text(build_hello(theme), encoding="utf-8")
        (out / f"terminal-{name}.svg").write_text(build_terminal(theme), encoding="utf-8")
        (out / f"laptop-{name}.svg").write_text(build_laptop(name), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "assets")
