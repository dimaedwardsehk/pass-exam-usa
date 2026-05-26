# CDL Master Prep PWA redesign

Static PWA build ready to publish under `/pass-exam-usa/cdl/` on GitHub Pages.

## Local test

```bash
npx http-server -p 4321 --silent
# open http://localhost:4321/pass-exam-usa/cdl/ if serving from a parent folder,
# or http://localhost:4321/ when serving this dist folder directly.
```

## Deploy

Copy every file in this folder into the repository path served as `/pass-exam-usa/cdl/`.
All app assets use relative URLs; manifest `start_url`/`scope` target `/pass-exam-usa/cdl/`.
