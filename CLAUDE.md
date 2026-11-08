# SP Time Calculator

Single-page web app in `SP Time Calculator/` (index.html, manifest, service worker, icons),
served by GitHub Pages at https://daboneman911.github.io/sptime/SP%20Time%20Calculator/

## Workflow rules

- After EVERY change, commit and push to `main` immediately. Do not ask for confirmation.
- When you change cached app files, bump `CACHE` in `SP Time Calculator/sw.js` (e.g. `sp-time-v2`)
  so installed home-screen copies pick up the update.
