# chriswjohnston-stage

Campaign website for Chris Johnston — Nipissing Township Council, October 2026.
**Stage environment** — previews changes before promoting to production.

---

## How It Works

```
src/campaign/index.html   ← Homepage source (edit here)
*.html (root)             ← Detail page sources (edit here)
shared.css                ← Design tokens + shared components (edit here)
         │
         ▼  build_stage.py  (runs on every push to main)
         │
docs/                     ← GENERATED OUTPUT — never edit directly
├── index.html            (homepage + ticker + signup + stage banner injected)
├── shared.css            (copied as-is)
├── projects.html         (+ stage banner injected)
├── facilities.html
├── communication.html
├── communication-plan.html
├── governance.html
├── finances.html
└── strategic-planning.html
```

GitHub Pages serves from `docs/`. The `docs/` folder is always overwritten on push — any manual edits there will be lost.

---

## Where to Edit

| What you want to change | File to edit |
|---|---|
| Homepage | `src/campaign/index.html` |
| Accountability cases | `projects.html` |
| Facilities page | `facilities.html` |
| Communication page | `communication.html` |
| Communication plan | `communication-plan.html` |
| Governance page | `governance.html` |
| Finances page | `finances.html` |
| Strategic planning | `strategic-planning.html` |
| Colours, fonts, tokens | `shared.css` |
| Build logic / injections | `build_stage.py` |

**Never edit anything in `docs/`.**

---

## Deploying

### To Stage (automatic)
Push to `main`. GitHub Actions runs `build_stage.py`, commits to `docs/`, and the stage site updates within ~60 seconds.

```bash
git add -A
git commit -m "your message"
git push origin main
```

Stage URL: **https://stage.chriswjohnston.ca**

### To Production (manual trigger)
1. Go to **Actions** tab in GitHub
2. Select **Promote to Production**
3. Click **Run workflow**

This force-pushes `docs/` to the `production` branch, which GitHub Pages serves as the live site.

Production URL: **https://chriswjohnston.ca**

---

## File Structure

```
chriswjohnston-stage/
├── .github/
│   └── workflows/
│       ├── build-stage.yml     # Runs on push to main
│       └── promote.yml         # Manual promote to production
├── src/
│   └── campaign/
│       └── index.html          # Homepage source
├── docs/                       # GENERATED — do not edit
├── projects.html
├── facilities.html
├── communication.html
├── communication-plan.html     # Linked from communication.html
├── governance.html
├── finances.html
├── strategic-planning.html
├── shared.css                  # Design system
├── build_stage.py              # Build script
└── README.md
```

---

## CSS Architecture

`shared.css` contains:
- Design tokens (all CSS variables)
- Reset
- Components used on **3+ pages**: buttons, section primitives, callout boxes, stat rows, tags, timeline, status helpers, animations

Page-specific styles live in each file's `<style>` block. If a component starts appearing on 3+ pages, move it to `shared.css`.

---

## Build Script Injections

`build_stage.py` adds the following to the stage build (not present in source files):

| Injection | Where |
|---|---|
| News ticker script + bar | After `</nav>` on homepage |
| News nav link | Homepage nav |
| Email signup section (disabled) | Before `#contact` on homepage |
| Stage preview banner | Before `</body>` on all pages |

The production promotion just pushes the already-built `docs/` — no additional processing.
