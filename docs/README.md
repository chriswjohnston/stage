# chriswjohnston-stage

Campaign website for Chris Johnston — Nipissing Township Council 2026.

## Structure

- `src/campaign/index.html` — Main campaign homepage (source)
- `projects.html` — Fiscal responsibility / project accountability page
- `facilities.html` — Community services & recreation page  
- `communication.html` — Communication & technology page
- `communication-plan.html` — Full 13-point communication plan
- `governance.html` — Community governance page
- `build_stage.py` — Builds docs/ from src/ with stage banner injected
- `docs/` — Built output served by GitHub Pages (stage.chriswjohnston.ca)

## Deploy

**Stage:** Push to `main` — GitHub Actions runs `build_stage.py` automatically.

**Production:** Run the "Promote to Production" workflow manually from GitHub Actions.

## Notes

- `facilities.html` is in repo root — copy from existing repo, do not replace with placeholder
- `docs/components/news-ticker.js` is fetched from live site at build time
