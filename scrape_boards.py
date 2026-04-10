#!/usr/bin/env python3
"""
scrape_boards.py
================
Scrapes Township of Nipissing board and committee meeting documents
(Recreation Committee, Museum Board, Cemetery Committee) from the
Township website and builds a structured archive alongside the
council meeting archive.

Run via GitHub Actions on the council.chriswjohnston.ca repo.
"""

import re
import json
import time
import os
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# ── CONFIG ────────────────────────────────────────────────────────────────────

BOARDS = [
    {
        "id": "recreation",
        "name": "Recreation Committee",
        "url": "https://nipissingtownship.com/services/recreation/",
        "bylaw": "2023-09",
        "bylaw_url": "https://nipissingtownship.com/wp-content/uploads/2023/01/Recreation-Committee-By-Law.pdf",
        "description": "Responsible for management and conduct of recreational programming and the Community Centre at 2381 Highway 654.",
    },
    {
        "id": "museum",
        "name": "Museum Board",
        "url": "https://nipissingtownship.com/services/museum-services-and-information/",
        "bylaw": "2023-10",
        "bylaw_url": "https://nipissingtownship.com/wp-content/uploads/2023/01/By-Law-2023-10-Museum-Board.pdf",
        "description": "Board of management for the Nipissing Township Museum, preserving and displaying the history of the Township and surrounding area.",
    },
    {
        "id": "cemetery",
        "name": "Cemetery Committee",
        "url": "https://nipissingtownship.com/services/cemetery/",
        "bylaw": "2023-11",
        "bylaw_url": None,
        "description": "Administration of the Nipissing Union Cemetery, Commanda Cemetery and St. John's Alsace Cemetery.",
    },
]

OUTPUT_DIR = Path("boards")
HEADERS = {"User-Agent": "council-archive-bot/1.0 (chriswjohnston.ca civic tool)"}
AI_API = "https://api.anthropic.com/v1/messages"
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── SCRAPING ──────────────────────────────────────────────────────────────────

def scrape_board_page(board: dict) -> list[dict]:
    """Scrape meeting dates, agendas, and minutes from a board/committee page."""
    print(f"  Scraping {board['name']}...")
    r = requests.get(board["url"], headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    content = (
        soup.find("div", class_="entry-content")
        or soup.find("main")
        or soup.find("article")
        or soup.body
    )

    meetings = []
    current_year = None

    # Find all links — build a map of anchor text → href
    links_map: dict[str, str] = {}
    for a in content.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        links_map[text] = a["href"]

    # Parse text line by line looking for meeting entries
    full_text = content.get_text(separator="\n")
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]

    date_pattern = re.compile(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2}),?\s+(\d{4})"
    )
    year_pattern = re.compile(r"^\*?\*?(\d{4})\s*(Meeting Dates|Agendas|Minutes)?\*?\*?$")

    # Also scrape raw links to find PDF URLs
    all_links = {a.get_text(strip=True): a["href"] for a in content.find_all("a", href=True)}

    for line in lines:
        # Detect year heading
        ym = year_pattern.match(line)
        if ym:
            current_year = int(ym.group(1))
            continue

        # Detect meeting entry
        dm = date_pattern.search(line)
        if dm and current_year:
            month, day, year = dm.group(1), dm.group(2), dm.group(3)
            date_str = f"{year}-{datetime.strptime(month, '%B').month:02d}-{int(day):02d}"
            display_date = f"{month} {day}, {year}"

            # Check if cancelled
            cancelled = "CANCELLED" in line.upper() or "CANCELED" in line.upper()

            # Find PDF links for this meeting — match by date string
            agenda_url = None
            minutes_url = None
            package_url = None

            # Search all links for ones containing this date pattern
            date_variants = [
                f"{month[:3].lower()}-{int(day):02d}-{year}",  # jan-19-2026
                f"{month.lower()}-{int(day):02d}-{year}",      # january-19-2026
                f"{month[:3].lower()}{int(day):02d}{year}",    # jan192026
                f"{year}-{datetime.strptime(month, '%B').month:02d}-{int(day):02d}",  # 2026-01-19
                f"{month.lower()}-{year}",                      # january-2026 (month-level match)
            ]

            for link_text, link_href in all_links.items():
                lower_href = link_href.lower()
                is_date_match = any(v in lower_href for v in date_variants)
                if not is_date_match:
                    continue
                if "agenda" in lower_href and "package" not in lower_href:
                    agenda_url = link_href
                elif "minutes" in lower_href or "minute" in lower_href:
                    minutes_url = link_href
                elif "package" in lower_href or "pkg" in lower_href:
                    package_url = link_href

            meetings.append({
                "date": date_str,
                "display_date": display_date,
                "year": int(year),
                "cancelled": cancelled,
                "agenda_url": agenda_url,
                "minutes_url": minutes_url,
                "package_url": package_url,
                "board_id": board["id"],
                "board_name": board["name"],
                "summary": None,
            })

    # Deduplicate by date
    seen = set()
    unique = []
    for m in meetings:
        if m["date"] not in seen:
            seen.add(m["date"])
            unique.append(m)

    unique.sort(key=lambda x: x["date"], reverse=True)
    print(f"    Found {len(unique)} meetings ({sum(1 for m in unique if m['minutes_url'])} with minutes)")
    return unique


# ── AI SUMMARIES ──────────────────────────────────────────────────────────────

def fetch_pdf_text(url: str, max_chars: int = 6000) -> str | None:
    """Fetch and return text content from a PDF URL."""
    if not url:
        return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None
        # Very basic: extract readable text from PDF bytes
        # For real use, deploy with PyPDF2 or pdfplumber in GitHub Actions
        content = r.content
        # Extract ASCII text portions
        text = content.decode("latin-1", errors="ignore")
        # Remove binary noise
        text = re.sub(r"[^\x20-\x7E\n\r\t]", " ", text)
        text = re.sub(r"\s{3,}", "\n", text)
        return text[:max_chars]
    except Exception:
        return None


def generate_summary(meeting: dict) -> str | None:
    """Call Claude API to summarize a meeting's minutes."""
    if not ANTHROPIC_KEY or not meeting.get("minutes_url"):
        return None

    pdf_text = fetch_pdf_text(meeting["minutes_url"])
    if not pdf_text or len(pdf_text) < 200:
        return None

    try:
        resp = requests.post(
            AI_API,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 300,
                "messages": [{
                    "role": "user",
                    "content": (
                        f"This is the minutes of a {meeting['board_name']} meeting "
                        f"held on {meeting['display_date']} for the Township of Nipissing, Ontario.\n\n"
                        f"Minutes text:\n{pdf_text}\n\n"
                        "Write a 2-3 sentence plain-language summary of what was discussed and decided. "
                        "Focus on substantive matters — budgets, programs, facilities, decisions. "
                        "Skip procedural items (approval of minutes, adjournment). "
                        "Write as if for a resident who wants to know what happened."
                    )
                }],
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()["content"][0]["text"].strip()
    except Exception as e:
        print(f"    Summary error: {e}")
    return None


# ── OUTPUT ────────────────────────────────────────────────────────────────────

def build_board_index_html(board: dict, meetings: list[dict]) -> str:
    """Generate an HTML archive page for one board/committee."""
    years = sorted(set(m["year"] for m in meetings), reverse=True)

    by_year = {}
    for m in meetings:
        by_year.setdefault(m["year"], []).append(m)

    rows_html = ""
    for year in years:
        rows_html += f'<div class="year-group" id="year-{year}"><div class="year-label">{year}</div>\n'
        for m in by_year[year]:
            status_class = "cancelled" if m["cancelled"] else ("has-minutes" if m["minutes_url"] else "agenda-only")
            status_text = "Cancelled" if m["cancelled"] else ("Minutes Available" if m["minutes_url"] else "Agenda Only")

            links_html = ""
            if m.get("agenda_url"):
                links_html += f'<a href="{m["agenda_url"]}" target="_blank" class="doc-link agenda">Agenda</a>'
            if m.get("minutes_url"):
                links_html += f'<a href="{m["minutes_url"]}" target="_blank" class="doc-link minutes">Minutes</a>'
            if m.get("package_url"):
                links_html += f'<a href="{m["package_url"]}" target="_blank" class="doc-link package">Package</a>'

            summary_html = ""
            if m.get("summary"):
                summary_html = f'<div class="meeting-summary">{m["summary"]}</div>'

            rows_html += f"""<div class="meeting-row {status_class}">
  <div class="meeting-date">{m["display_date"]}</div>
  <div class="meeting-info">
    <span class="status-badge {status_class}">{status_text}</span>
    {summary_html}
  </div>
  <div class="meeting-links">{links_html}</div>
</div>\n"""
        rows_html += "</div>\n"

    total = len(meetings)
    with_minutes = sum(1 for m in meetings if m.get("minutes_url"))
    cancelled_count = sum(1 for m in meetings if m["cancelled"])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{board['name']} — Nipissing Township Archive</title>
<style>
  :root {{ --green: #1a4d2e; --gold: #b8922a; --bg: #f9f7f4; --white: #fff; --rule: #d8d0c8; --body: #3a3a3a; --muted: #6e6e6e; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--body); }}
  header {{ background: var(--green); color: #fff; padding: 1.5rem 2rem; }}
  header h1 {{ font-size: 1.4rem; font-weight: 700; margin-bottom: 0.25rem; }}
  header p {{ font-size: 0.88rem; color: rgba(255,255,255,0.7); }}
  .breadcrumb {{ font-size: 0.75rem; margin-bottom: 0.5rem; }}
  .breadcrumb a {{ color: rgba(255,255,255,0.6); text-decoration: none; }}
  .stats {{ display: flex; gap: 2rem; padding: 1rem 2rem; background: var(--white); border-bottom: 1px solid var(--rule); font-size: 0.82rem; }}
  .stat strong {{ font-size: 1.2rem; display: block; color: var(--green); font-weight: 700; }}
  .main {{ max-width: 960px; margin: 0 auto; padding: 1.5rem 2rem; }}
  .bylaw-notice {{ background: #e8f0eb; border: 1px solid #b8d4c2; border-left: 4px solid var(--green); border-radius: 6px; padding: 0.9rem 1.2rem; margin-bottom: 1.5rem; font-size: 0.84rem; }}
  .bylaw-notice a {{ color: var(--green); }}
  .year-group {{ margin-bottom: 2rem; }}
  .year-label {{ font-size: 0.7rem; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: var(--muted); padding: 0.5rem 0; border-bottom: 2px solid var(--rule); margin-bottom: 0.5rem; }}
  .meeting-row {{ display: grid; grid-template-columns: 130px 1fr auto; gap: 1rem; align-items: start; padding: 0.75rem 0; border-bottom: 1px solid var(--rule); }}
  .meeting-row:last-child {{ border-bottom: none; }}
  .meeting-date {{ font-size: 0.85rem; font-weight: 600; color: var(--body); padding-top: 2px; }}
  .meeting-row.cancelled .meeting-date {{ color: var(--muted); text-decoration: line-through; }}
  .status-badge {{ display: inline-block; font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; padding: 2px 7px; border-radius: 3px; margin-bottom: 4px; }}
  .status-badge.has-minutes {{ background: #e8f0eb; color: var(--green); }}
  .status-badge.agenda-only {{ background: #fdf6e3; color: var(--gold); }}
  .status-badge.cancelled {{ background: #f0f0f0; color: var(--muted); }}
  .meeting-summary {{ font-size: 0.83rem; line-height: 1.6; color: var(--body); margin-top: 4px; }}
  .meeting-links {{ display: flex; flex-direction: column; gap: 4px; min-width: 80px; }}
  .doc-link {{ font-size: 0.72rem; font-weight: 700; text-decoration: none; padding: 3px 8px; border-radius: 3px; text-align: center; }}
  .doc-link.agenda {{ background: var(--green); color: #fff; }}
  .doc-link.minutes {{ background: var(--gold); color: #fff; }}
  .doc-link.package {{ background: #555; color: #fff; }}
  @media (max-width: 600px) {{ .meeting-row {{ grid-template-columns: 1fr; }} .stats {{ flex-wrap: wrap; gap: 1rem; }} }}
</style>
</head>
<body>
<header>
  <div class="breadcrumb"><a href="/">← Council Archive</a> / Boards &amp; Committees</div>
  <h1>{board['name']}</h1>
  <p>{board['description']}</p>
</header>
<div class="stats">
  <div class="stat"><strong>{total}</strong>Meetings scheduled</div>
  <div class="stat"><strong>{with_minutes}</strong>Minutes available</div>
  <div class="stat"><strong>{cancelled_count}</strong>Cancelled</div>
  <div class="stat"><strong>{len(years)}</strong>Years covered</div>
</div>
<div class="main">
  <div class="bylaw-notice">
    Governed by <strong>By-Law {board['bylaw']}</strong> (2023).
    {"<a href='" + board['bylaw_url'] + "' target='_blank'>Read the governing by-law →</a>" if board['bylaw_url'] else ""}
    &nbsp;·&nbsp; Source: <a href="{board['url']}" target="_blank">Township of Nipissing website</a>
  </div>
  {rows_html}
</div>
</body>
</html>"""


def build_boards_index_html(boards_data: list[dict]) -> str:
    """Generate the main boards index page."""
    cards = ""
    for b in boards_data:
        meetings = b["meetings"]
        recent = next((m for m in meetings if m.get("minutes_url")), None)
        recent_text = f"Last minutes: {recent['display_date']}" if recent else "No minutes yet"
        cards += f"""<a class="board-card" href="{b['id']}/index.html">
  <div class="board-name">{b['name']}</div>
  <div class="board-meta">{len(meetings)} meetings · {recent_text}</div>
</a>\n"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Boards &amp; Committees — Nipissing Township</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #f9f7f4; color: #3a3a3a; max-width: 800px; margin: 0 auto; padding: 2rem; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; color: #1a4d2e; }}
  .intro {{ font-size: 0.9rem; color: #666; margin-bottom: 2rem; line-height: 1.65; }}
  .board-card {{ display: block; background: #fff; border: 1px solid #d8d0c8; border-left: 4px solid #1a4d2e; border-radius: 6px; padding: 1rem 1.25rem; margin-bottom: 0.75rem; text-decoration: none; transition: box-shadow 0.2s; }}
  .board-card:hover {{ box-shadow: 0 3px 12px rgba(0,0,0,0.1); }}
  .board-name {{ font-weight: 700; color: #1a4d2e; margin-bottom: 0.2rem; }}
  .board-meta {{ font-size: 0.8rem; color: #888; }}
  .back {{ font-size: 0.82rem; margin-bottom: 1.5rem; }} .back a {{ color: #1a4d2e; }}
</style>
</head>
<body>
<div class="back"><a href="/">← Back to Council Archive</a></div>
<h1>Boards &amp; Committees</h1>
<p class="intro">Meeting agendas and minutes for Township of Nipissing boards and committees. 
Documents sourced from the Township website. Updated automatically.</p>
{cards}
<p style="font-size:0.75rem;color:#aaa;margin-top:2rem;">Last updated: {datetime.now().strftime('%B %d, %Y')}</p>
</body>
</html>"""


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("Board & Committee Scraper")
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    OUTPUT_DIR.mkdir(exist_ok=True)
    boards_data = []

    for board in BOARDS:
        try:
            meetings = scrape_board_page(board)

            # Generate AI summaries for recent meetings without one
            if ANTHROPIC_KEY:
                for m in meetings[:6]:  # Only summarize most recent 6
                    if m.get("minutes_url") and not m.get("summary"):
                        print(f"    Summarizing {m['display_date']}...")
                        m["summary"] = generate_summary(m)
                        time.sleep(0.5)  # Rate limit

            # Save JSON
            board_dir = OUTPUT_DIR / board["id"]
            board_dir.mkdir(exist_ok=True)

            data = {
                "board": board,
                "meetings": meetings,
                "generated": datetime.now().isoformat(),
            }
            (board_dir / "data.json").write_text(json.dumps(data, indent=2))

            # Save HTML
            html = build_board_index_html(board, meetings)
            (board_dir / "index.html").write_text(html)

            boards_data.append({"id": board["id"], "name": board["name"], "meetings": meetings})
            print(f"  ✓ {board['name']}: {len(meetings)} meetings written")

        except Exception as e:
            print(f"  ✗ {board['name']}: {e}")

    # Write main index
    index_html = build_boards_index_html(boards_data)
    (OUTPUT_DIR / "index.html").write_text(index_html)
    print(f"\n✓ Boards index written")
    print(f"✓ Complete — {datetime.now().strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__":
    main()
