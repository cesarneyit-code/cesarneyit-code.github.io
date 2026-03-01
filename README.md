# Academic Homepage (GitHub Pages)

This folder is a first bilingual (`ES/EN`) version of your academic webpage.

## Files
- `index.html`: structure and sections.
- `styles.css`: visual design and responsive layout.
- `script.js`: language switcher (`ES/EN`), mobile menu, dynamic year.
- `assets/cesar-galindo-profile.svg`: current profile image placeholder.
- `.nojekyll`: disables Jekyll processing.

## Quick customization
1. Open `index.html` and update links:
   - `CV`
   - `Google Scholar`
   - `ORCID`
   - `Uniandes profile`
2. Open `script.js` and update all placeholder text in both languages.
3. Replace profile image:
   - Keep the same path and overwrite `assets/cesar-galindo-profile.svg`, or
   - Add `assets/cesar-galindo-profile.jpg` and update the image `src` in `index.html`.
4. Optional: add `cv.pdf` inside `docs/` and update the CV button URL.

## Publish in GitHub Pages
1. Push this repository to GitHub.
2. In GitHub: `Settings` -> `Pages`.
3. Under `Build and deployment`:
   - `Source`: `Deploy from a branch`
   - Branch: `main` (or your default branch)
   - Folder: `/docs`
4. Save and wait for deployment.

## DNS setup for GitHub Pages
For root domain `cesargalindo.com`, set these `A` records:
- `185.199.108.153`
- `185.199.109.153`
- `185.199.110.153`
- `185.199.111.153`

For `www`, set:
- `CNAME` -> `cesargalindo.com`

Then in GitHub `Settings` -> `Pages`, add custom domain `cesargalindo.com`, create a `CNAME` file in `docs/`, and enable `Enforce HTTPS` after DNS is active.
