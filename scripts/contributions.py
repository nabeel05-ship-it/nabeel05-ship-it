"""Render a minimal weekly contribution chart (light and dark variants).

Usage: GITHUB_TOKEN=... python3 scripts/contributions.py <github-login> <output-dir>
"""
import datetime as dt
import json
import math
import os
import sys
import urllib.request

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

# Matches GitHub's own light/dark foreground, muted and border colours.
THEMES = {
    "light": {"bar": "#1f2328", "muted": "#59636e", "rule": "#d1d9e0"},
    "dark": {"bar": "#f0f6fc", "muted": "#9198a1", "rule": "#3d444d"},
}

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
    return sum(1 for c in days if c), longest


def render(total, weeks, theme):
    c = THEMES[theme]
    W, H = 1000, 200
    BASE = 160
    left, right = 0, 1000
    n = len(weeks)
    step = (right - left) / n
    bw = step * 0.55
    totals = [sum(n_ for _, n_ in w) for w in weeks]
    peak = max(totals, default=0)
    active, longest = stats(weeks)

    bars, months, seen = [], [], set()
    for i, (w, t) in enumerate(zip(weeks, totals)):
        x = left + i * step + (step - bw) / 2
        if t:
            h = 4 + 106 * math.sqrt(t / peak)
            bars.append(f'<rect x="{x:.1f}" y="{BASE - h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="2" fill="{c["bar"]}">'
                        f'<title>Week of {w[0][0]}: {t} contributions</title></rect>')
        else:
            bars.append(f'<rect x="{x:.1f}" y="{BASE - 2:.1f}" width="{bw:.1f}" height="2" rx="1" fill="{c["rule"]}"/>')
        first = dt.date.fromisoformat(w[0][0])
        if (first.year, first.month) not in seen and first.day <= 7 and i < n - 1:
            seen.add((first.year, first.month))
            months.append(f'<text x="{x:.0f}" y="{BASE + 24}" font-size="12" fill="{c["muted"]}">{first.strftime("%b")}</text>')

    summary = f"{total} contributions in the last year · {active} active days · longest streak {longest} days"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{summary}">
<g font-family="{SANS}">
  <text x="0" y="18" font-size="14" fill="{c["muted"]}">{summary}</text>
  {''.join(bars)}
  {''.join(months)}
</g>
</svg>'''


if __name__ == "__main__":
    login, out_dir = sys.argv[1], sys.argv[2]
    total, weeks = fetch(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out_dir, f"contributions-{theme}.svg"), "w") as f:
            f.write(render(total, weeks, theme))
    print(f"wrote {out_dir}: {total} contributions over {len(weeks)} weeks")
