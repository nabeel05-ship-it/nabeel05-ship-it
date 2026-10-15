"""Render a minimal weekly contribution chart: one bar per week of the last year.

Usage: GITHUB_TOKEN=... python3 scripts/contributions.py <github-login> <output.svg>
"""
import datetime as dt
import json
import math
import os
import sys
import urllib.request

SANS = "'Segoe UI', -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"

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


def render(total, weeks):
    W, H = 1000, 280
    BASE = 220
    left, right = 40, 960
    n = len(weeks)
    step = (right - left) / n
    bw = step * 0.62
    totals = [sum(c for _, c in w) for w in weeks]
    peak = max(totals, default=0)
    active, longest, best = stats(weeks)

    bars, months, seen = [], [], set()
    for i, (w, t) in enumerate(zip(weeks, totals)):
        x = left + i * step + (step - bw) / 2
        if t:
            h = 6 + 124 * math.sqrt(t / peak)
            d = 0.3 + i * 0.012
            bars.append(f'<rect x="{x:.1f}" y="{BASE - h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="{bw / 2:.1f}" fill="url(#bar)">'
                        f'<title>{w[0][0]}: {t} contributions</title>'
                        f'<animate attributeName="height" values="0;0;{h:.1f}" keyTimes="0;{d / (d + 0.6):.3f};1" dur="{d + 0.6:.2f}s" fill="freeze"/>'
                        f'<animate attributeName="y" values="{BASE};{BASE};{BASE - h:.1f}" keyTimes="0;{d / (d + 0.6):.3f};1" dur="{d + 0.6:.2f}s" fill="freeze"/></rect>')
        else:
            bars.append(f'<rect x="{x:.1f}" y="{BASE - 3:.1f}" width="{bw:.1f}" height="3" rx="1.5" fill="#1e293b"/>')
        first = dt.date.fromisoformat(w[0][0])
        if (first.year, first.month) not in seen and first.day <= 7 and i < n - 1:
            seen.add((first.year, first.month))
            months.append(f'<text x="{x:.0f}" y="{BASE + 26}" font-size="11" fill="#64748b">{first.strftime("%b")}</text>')

    stat_items = [(total, "contributions"), (active, "active days"), (f"{longest}d", "longest streak")]
    stat_svg = "".join(
        f'<text x="{960 - (2 - k) * 130}" y="46" text-anchor="end" font-size="20" font-weight="700" fill="#f1f5f9">{v}</text>'
        f'<text x="{960 - (2 - k) * 130}" y="64" text-anchor="end" font-size="11" fill="#64748b">{lbl}</text>'
        for k, (v, lbl) in enumerate(stat_items))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{total} contributions in the last year, {active} active days, longest streak {longest} days">
<defs>
  <linearGradient id="bar" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#2563eb"/><stop offset="1" stop-color="#a78bfa"/></linearGradient>
</defs>
<g font-family="{SANS}">
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="#0b1120" stroke="#1e293b"/>
  <text x="40" y="46" font-size="16" font-weight="600" fill="#f1f5f9">Weekly contributions</text>
  <text x="40" y="66" font-size="12" fill="#64748b">Last 12 months · updated {dt.date.today().strftime("%d %b %Y")}</text>
  {stat_svg}
  <line x1="{left}" y1="{BASE + 0.5}" x2="{right}" y2="{BASE + 0.5}" stroke="#1e293b"/>
  {''.join(bars)}
  {''.join(months)}
</g>
</svg>'''


if __name__ == "__main__":
    login, out = sys.argv[1], sys.argv[2]
    total, weeks = fetch(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w") as f:
        f.write(render(total, weeks))
    print(f"wrote {out}: {total} contributions over {len(weeks)} weeks")
