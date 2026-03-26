"""
build_stage.py
==============
Always builds in campaign mode — this is the preview/staging site.
Copies src/campaign/index.html to docs/index.html with ticker injected.
"""
import re, shutil
from pathlib import Path
from datetime import datetime

CAMPAIGN_SRC = Path("src/campaign/index.html")
DOCS_DIR     = Path("docs")

TICKER_SNIPPET = """  <script src="/components/news-ticker.js" defer></script>
  <style>.ticker-wrap{position:sticky;top:60px;z-index:99;}</style>"""

SIGNUP_HTML = """
<section id="signup" style="background:#F2EAD3;padding:3.5rem 2rem;">
  <div style="max-width:600px;margin:0 auto;text-align:center;">
    <p style="font-size:.68rem;font-weight:700;letter-spacing:.25em;text-transform:uppercase;color:#C06830;margin-bottom:.5rem;">Stay Informed</p>
    <h2 style="font-family:'Playfair Display',serif;font-size:1.8rem;color:#2C4A3E;margin-bottom:.75rem;">Township Updates in Your Inbox</h2>
    <p style="font-size:.95rem;color:#666;margin-bottom:1.5rem;line-height:1.7;">Every two weeks — the latest Nipissing Township news and a summary of the most recent council meeting.</p>
    <form style="display:flex;gap:.75rem;justify-content:center;flex-wrap:wrap;">
      <input type="email" placeholder="your@email.com"
        style="flex:1;min-width:220px;max-width:320px;padding:.75rem 1rem;border:2px solid rgba(44,74,62,.2);border-radius:6px;font-size:.95rem;font-family:inherit;background:#fff;"
        disabled>
      <button type="button"
        style="background:#C06830;color:#fff;border:none;border-radius:6px;padding:.75rem 1.75rem;font-size:.85rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;cursor:not-allowed;opacity:.7;font-family:inherit;">
        Subscribe
      </button>
    </form>
    <p style="margin-top:.75rem;font-size:.8rem;color:#999;">[Stage preview — signup disabled]</p>
  </div>
</section>"""

STAGE_BANNER = """
<div style="position:fixed;bottom:0;left:0;right:0;z-index:9999;background:#C06830;color:#fff;text-align:center;padding:.5rem;font-size:.8rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">
  ⚠ Stage Preview — <a href="https://chriswjohnston.ca" style="color:#fff;text-decoration:underline;">View Live Site</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/chriswjohnston/chriswjohnston-stage/actions" style="color:#fff;text-decoration:underline;">Promote to Production →</a>
</div>"""

TICKER_BAR = '\n<div class="ticker-wrap"><news-ticker src="https://chriswjohnston.ca/news.json" count="5" speed="45"></news-ticker></div>\n'

def build():
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "components").mkdir(exist_ok=True)

    # Copy ticker component from live site (fetched at build time)
    try:
        import requests
        r = requests.get("https://chriswjohnston.ca/components/news-ticker.js", timeout=10)
        if r.status_code == 200:
            (DOCS_DIR / "components" / "news-ticker.js").write_text(r.text)
            print("  ✓ news-ticker.js fetched from live site")
    except Exception as e:
        print(f"  ⚠ Could not fetch ticker: {e}")

    html = CAMPAIGN_SRC.read_text(encoding="utf-8")

    # Inject ticker script
    html = html.replace("</head>", TICKER_SNIPPET + "\n</head>", 1)

    # Inject ticker bar after nav
    html = re.sub(r'(</nav>)', r'\1' + TICKER_BAR, html, count=1)

    # Add news link to nav
    html = html.replace(
        '<li><a href="#contact">Contact</a></li>',
        '<li><a href="#contact">Contact</a></li>\n    <li><a href="https://chriswjohnston.ca/news/">News</a></li>', 1
    )

    # Inject signup (disabled in stage)
    html = html.replace('<section id="contact">', SIGNUP_HTML + '\n<section id="contact">', 1)

    # Inject stage banner before </body>
    html = html.replace("</body>", STAGE_BANNER + "\n</body>", 1)

    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"  ✓ docs/index.html (campaign mode)")
    print(f"\n✓ Stage build complete — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    print("=" * 50)
    print("Stage Builder")
    print("=" * 50)
    build()
