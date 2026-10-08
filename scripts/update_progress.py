#!/usr/bin/env python3
"""Update README progress, streak and assets/progress.svg.

Reads:
  - CHECKLIST.md          ("- [x]" and "- [ ]" lines)
  - daily-log/YYYY-MM-DD.md  (one file = one day on your streak)
Writes:
  - the block between <!-- PROGRESS:START --> and <!-- PROGRESS:END --> in README.md
  - assets/progress.svg

Run locally:  python3 scripts/update_progress.py
The GitHub Action in .github/workflows/progress.yml runs it for you on every push.
"""
import datetime as dt
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
START, END = "<!-- PROGRESS:START -->", "<!-- PROGRESS:END -->"


def today():
    try:
        from zoneinfo import ZoneInfo

        return dt.datetime.now(ZoneInfo("Australia/Sydney")).date()
    except Exception:
        return dt.date.today()


def checklist_stats():
    text = (ROOT / "CHECKLIST.md").read_text(encoding="utf-8")
    sections = {}
    current = "Top"
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = [0, 0]
        m = re.match(r"\s*- \[([ xX])\]", line)
        if m and current in sections:
            sections[current][1] += 1
            if m.group(1).lower() == "x":
                sections[current][0] += 1
    done = sum(v[0] for v in sections.values())
    total = sum(v[1] for v in sections.values())
    return done, total, sections


def log_dates():
    dates = set()
    for p in (ROOT / "daily-log").glob("*.md"):
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})\.md", p.name)
        if m:
            try:
                dates.add(dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
            except ValueError:
                pass
    return dates


def streaks(dates, now):
    cur = 0
    d = now if now in dates else now - dt.timedelta(days=1)
    while d in dates:
        cur += 1
        d -= dt.timedelta(days=1)
    longest = run = 0
    prev = None
    for d in sorted(dates):
        run = run + 1 if prev and (d - prev).days == 1 else 1
        longest = max(longest, run)
        prev = d
    return cur, longest


def strip(dates, now, n=14):
    days = [now - dt.timedelta(days=i) for i in range(n - 1, -1, -1)]
    return "".join("\U0001F7E9" if d in dates else "⬜" for d in days)


def progress_svg(done, total):
    pct = round(100 * done / total) if total else 0
    w = 600
    fill = round(w * pct / 100)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} 56" width="{w}" height="56" role="img" aria-label="Checklist progress {pct}%">
  <rect width="{w}" height="56" rx="8" fill="#0d1117" stroke="#2a323d"/>
  <rect x="12" y="30" width="{w - 24}" height="10" rx="5" fill="#1e2530"/>
  <rect x="12" y="30" width="{max(0, round((w - 24) * pct / 100))}" height="10" rx="5" fill="#4ade80"/>
  <text x="12" y="20" font-family="Consolas, monospace" font-size="13" fill="#8b96a5">Checklist progress</text>
  <text x="{w - 12}" y="20" font-family="Consolas, monospace" font-size="13" fill="#4ade80" text-anchor="end">{done} / {total} ({pct}%)</text>
</svg>
"""


def main():
    now = today()
    done, total, sections = checklist_stats()
    dates = log_dates()
    cur, longest = streaks(dates, now)
    pct = round(100 * done / total) if total else 0

    rows = [
        "| | |",
        "|---|---|",
        f"| Checklist | **{done} / {total}** ({pct}%) |",
        f"| Current streak | **{cur}** day{'s' if cur != 1 else ''} |",
        f"| Longest streak | {longest} day{'s' if longest != 1 else ''} |",
        f"| Days logged | {len(dates)} |",
        f"| Last 14 days | {strip(dates, now)} |",
        f"| As of | {now.isoformat()} |",
    ]
    for name, (d, t) in sections.items():
        if t:
            rows.append(f"| {name} | {d} / {t} |")
    block = START + "\n" + "\n".join(rows) + "\n\n![Checklist progress](assets/progress.svg)\n" + END

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print("README.md is missing the PROGRESS markers", file=sys.stderr)
        return 1
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    readme.write_text(new, encoding="utf-8")
    (ROOT / "assets" / "progress.svg").write_text(progress_svg(done, total), encoding="utf-8")
    print(f"checklist {done}/{total} ({pct}%), streak {cur} (longest {longest}), days logged {len(dates)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
