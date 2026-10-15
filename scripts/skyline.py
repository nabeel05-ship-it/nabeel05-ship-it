"""Render the "Build Lab Skyline": one building per week of GitHub contributions.

Usage: GITHUB_TOKEN=... python3 scripts/skyline.py <github-login> <output.svg>
"""
import datetime as dt
import json
import math
import os
import sys
import urllib.request

SANS = "'Segoe UI', -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
LIT = ["#38bdf8", "#818cf8", "#c084fc", "#f472b6"]  # window colours, low -> high activity

QUERY = """query($login: String!) { user(login: $login) { contributionsCollection {
  contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } } } }"""


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        cal = json.load(r)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["totalContributions"], [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in cal["weeks"]]


def stats(weeks):
    days = [c for w in weeks for _, c in w]
    longest = run = 0
    for c in days:
        run = run + 1 if c else 0
        longest = max(longest, run)
    return sum(1 for c in days if c), longest, max(days, default=0)


def rnd(i, j):
    """Deterministic pseudo-random in [0, 1) so the image is stable between runs."""
    return (math.sin(i * 12.9898 + j * 78.233) * 43758.5453) % 1


def render(total, weeks):
    W, H = 1000, 400
    GROUND = 340
    n = len(weeks)
    left, right = 46, 954
    step = (right - left) / n
    bw = step - 3
    totals = [sum(c for _, c in w) for w in weeks]
    peak = max(totals, default=0)
    active, longest, best = stats(weeks)

    sky = []
    for k in range(60):
        x, y = rnd(k, 1) * W, 20 + rnd(k, 2) * 200
        sky.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{0.6 + rnd(k, 3):.1f}" fill="#e0f2fe">'
                   f'<animate attributeName="opacity" values="0.15;0.9;0.15" dur="{2 + rnd(k, 4) * 3:.1f}s" begin="-{rnd(k, 5) * 4:.1f}s" repeatCount="indefinite"/></circle>')

    bldg, months, seen = [], [], set()
    peak_x = peak_top = None
    for i, (w, t) in enumerate(zip(weeks, totals)):
        x = left + i * step
        h = 26 + (150 * math.sqrt(t / peak) if peak else 0)
        top = GROUND - h
        d = i * 0.035  # left-to-right rise
        grow = (f'<animate attributeName="height" values="0;0;{h:.1f}" keyTimes="0;{d / (d + 0.9):.3f};1" dur="{d + 0.9:.2f}s" fill="freeze"/>'
                f'<animate attributeName="y" values="{GROUND};{GROUND};{top:.1f}" keyTimes="0;{d / (d + 0.9):.3f};1" dur="{d + 0.9:.2f}s" fill="freeze"/>')
        edge = LIT[min(3, int(3.99 * t / peak))] if t else "#334155"
        if not t and rnd(i, 99) < 0.3:  # rooftop antennas give quiet weeks some silhouette
            bldg.append(f'<line x1="{x + bw / 2:.1f}" y1="{top:.1f}" x2="{x + bw / 2:.1f}" y2="{top - 8:.1f}" stroke="#334155" stroke-width="1.5" opacity="0">'
                        f'<animate attributeName="opacity" to="1" begin="{d + 0.8:.2f}s" dur="0.3s" fill="freeze"/></line>')
        bldg.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{h:.1f}" fill="url(#tower)">{grow}</rect>')
        bldg.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw:.1f}" height="2" fill="{edge}" opacity="0">'
                    f'<animate attributeName="opacity" to="1" begin="{d + 0.8:.2f}s" dur="0.3s" fill="freeze"/></rect>')
        # windows: lit share follows that week's activity
        share = t / peak if peak else 0
        rows = int((h - 12) // 9)
        for r in range(rows):
            for col in range(2):
                wx, wy = x + 3 + col * (bw / 2 - 1), GROUND - 10 - r * 9
                on = t and rnd(i, r * 2 + col) < 0.25 + 0.75 * share
                if on:
                    c = LIT[min(3, int(rnd(r, i) * 4 * max(share, 0.3)))]
                    tw = (f'<animate attributeName="opacity" values="0.95;0.35;0.95" dur="{2 + rnd(i, r) * 3:.1f}s" begin="{d + 1.5 + rnd(r, col):.2f}s" repeatCount="indefinite"/>'
                          if rnd(i + 7, r + col) < 0.15 else "")
                    bldg.append(f'<rect x="{wx:.1f}" y="{wy:.1f}" width="{bw / 2 - 4:.1f}" height="4" rx="0.8" fill="{c}" opacity="0">'
                                f'<set attributeName="opacity" to="0.95" begin="{d + 0.9:.2f}s" fill="freeze"/>{tw}</rect>')
                elif rows < 40:
                    bldg.append(f'<rect x="{wx:.1f}" y="{wy:.1f}" width="{bw / 2 - 4:.1f}" height="4" rx="0.8" fill="#1e293b"/>')
        if t == peak and peak and peak_x is None:
            peak_x, peak_top = x + bw / 2, top
        first = dt.date.fromisoformat(w[0][0])
        if (first.year, first.month) not in seen and first.day <= 7 and i < n - 1:
            seen.add((first.year, first.month))
            months.append(f'<text x="{x:.0f}" y="{GROUND + 22}" font-size="11" fill="#64748b">{first.strftime("%b")}</text>')

    beacon = ""
    if peak_x is not None:
        beacon = (f'<line x1="{peak_x:.1f}" y1="{peak_top:.1f}" x2="{peak_x:.1f}" y2="{peak_top - 16:.1f}" stroke="#f472b6" stroke-width="1.5"/>'
                  f'<circle cx="{peak_x:.1f}" cy="{peak_top - 18:.1f}" r="3.5" fill="#f472b6"><animate attributeName="opacity" values="1;0.2;1" dur="1.2s" repeatCount="indefinite"/></circle>'
                  f'<circle cx="{peak_x:.1f}" cy="{peak_top - 18:.1f}" r="4" fill="none" stroke="#f472b6"><animate attributeName="r" values="4;16" dur="1.8s" repeatCount="indefinite"/><animate attributeName="opacity" values="0.8;0" dur="1.8s" repeatCount="indefinite"/></circle>'
                  f'<text x="{min(max(peak_x, 80), 920):.0f}" y="{peak_top - 30:.1f}" text-anchor="middle" font-family="{MONO}" font-size="11" fill="#f9a8d4">peak week · {peak}</text>')

    trail = "M-60 210 C 200 120, 420 60, 620 90 S 900 40, 1080 -30"
    sparks = "".join(
        f'<circle r="{3.2 - k * 0.45:.2f}" fill="{LIT[min(3, k)]}" opacity="{0.85 - k * 0.12:.2f}">'
        f'<animateMotion dur="9s" begin="{1.8 + k * 0.07:.2f}s" repeatCount="indefinite" path="{trail}" keyPoints="0;1;1" keyTimes="0;0.55;1" calcMode="linear"/></circle>'
        for k in range(6))
    rocket = (f'<g>{sparks}<g><path d="M-9 -4 L6 -4 L13 0 L6 4 L-9 4 Z" fill="#f8fafc"/><circle cx="3" cy="0" r="1.8" fill="#38bdf8"/>'
              f'<path d="M-9 -4 L-13 -8 L-5 -4 Z M-9 4 L-13 8 L-5 4 Z" fill="#f472b6"/>'
              f'<animateMotion dur="9s" begin="1.6s" repeatCount="indefinite" rotate="auto" path="{trail}" keyPoints="0;1;1" keyTimes="0;0.55;1" calcMode="linear"/></g></g>')

    stat_items = [(f"{total}", "CONTRIBUTIONS", "#38bdf8"), (f"{active}", "ACTIVE DAYS", "#a78bfa"),
                  (f"{longest}d", "LONGEST STREAK", "#f472b6"), (f"{best}", "BEST DAY", "#4ade80")]
    stat_svg = "".join(
        f'<text x="{520 + k * 120}" y="52" font-size="24" font-weight="800" fill="{c}">{v}</text>'
        f'<text x="{520 + k * 120}" y="70" font-size="9.5" font-weight="700" letter-spacing="1.2" fill="#64748b">{lbl}</text>'
        for k, (v, lbl, c) in enumerate(stat_items))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Build Lab Skyline: {total} contributions in the last year, {active} active days, longest streak {longest} days, best day {best}">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#020617"/><stop offset="0.7" stop-color="#0f0a2e"/><stop offset="1" stop-color="#1e1b4b"/></linearGradient>
  <linearGradient id="tower" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1e293b"/><stop offset="1" stop-color="#0b1120"/></linearGradient>
  <linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#38bdf8"/><stop offset="0.5" stop-color="#a78bfa"/><stop offset="1" stop-color="#f472b6"/></linearGradient>
  <radialGradient id="moon" cx="0.4" cy="0.4"><stop offset="0" stop-color="#f5f3ff"/><stop offset="1" stop-color="#c4b5fd"/></radialGradient>
  <radialGradient id="haze" cx="0.5" cy="1" r="0.7"><stop offset="0" stop-color="#7c3aed" stop-opacity="0.35"/><stop offset="1" stop-color="#7c3aed" stop-opacity="0"/></radialGradient>
  <clipPath id="cl"><rect width="{W}" height="{H}" rx="22"/></clipPath>
</defs>
<g clip-path="url(#cl)" font-family="{SANS}">
  <rect width="{W}" height="{H}" fill="url(#sky)"/>
  <rect y="{GROUND - 200}" width="{W}" height="200" fill="url(#haze)"/>
  {''.join(sky)}
  <circle cx="330" cy="170" r="22" fill="url(#moon)" opacity="0.9"/><circle cx="340" cy="164" r="20" fill="#0f0a2e" opacity="0.85"/>
  {rocket}
  <text x="40" y="44" font-family="{MONO}" font-size="13" font-weight="700" letter-spacing="3" fill="#a78bfa">BUILD LAB SKYLINE</text>
  <text x="40" y="66" font-size="13" fill="#94a3b8">One building per week · lit windows = contributions</text>
  {stat_svg}
  {''.join(bldg)}
  {beacon}
  <rect x="0" y="{GROUND}" width="{W}" height="2" fill="url(#g)"/>
  <rect x="0" y="{GROUND + 2}" width="{W}" height="{H - GROUND}" fill="#020617"/>
  {''.join(months)}
  <text x="{W - 40}" y="{H - 18}" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="#475569">updated {dt.date.today().isoformat()}</text>
</g>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="21" fill="none" stroke="url(#g)" stroke-opacity="0.6" stroke-width="2"/>
</svg>'''


if __name__ == "__main__":
    login, out = sys.argv[1], sys.argv[2]
    total, weeks = fetch(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w") as f:
        f.write(render(total, weeks))
    print(f"wrote {out}: {total} contributions over {len(weeks)} weeks")
