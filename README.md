# Wheel Stock — GitHub Pages Automatic Catalogue Dashboard

## What this repository does

The PDFs in `catalogues/` are the source of the wheel catalogue. A GitHub
Actions workflow automatically runs the PDF processor whenever you push a
change to `main`. It generates the searchable dashboard in `site/` and deploys
that folder to GitHub Pages.

## The only folder you normally use

`catalogues/`

Add new PDF catalogues there. Then commit the change. The workflow rebuilds the
dashboard automatically.

## Do not manually edit

- `site/` — generated output
- `generator/build_database.py` — automatic PDF processor
- `.github/workflows/deploy.yml` — automatic build/deploy workflow

## First-time GitHub setup

1. Create a public GitHub repository.
2. Upload the contents of this folder.
3. Make sure `.github/workflows/deploy.yml` is present.
4. In GitHub: Settings → Pages → Build and deployment → Source → GitHub Actions.
5. Open Actions and wait for "Build and publish wheel dashboard" to turn green.
6. Settings → Pages will show the live site URL.

## Adding a catalogue later

Put the new PDF in:

`catalogues/NEW_CATALOGUE.pdf`

Commit/push it. GitHub Actions rebuilds the site.

## Notes

- Numeric stock is displayed; non-numeric stock values are not displayed as a number.
- Product source file and catalogue page are retained where available.
- Wheel images are extracted during the build and stored under `site/wheel_dashboard_assets/`.
