# khlaifiabilel.github.io

Personal portfolio for Bilel Khlaifia — AI / Machine Learning Engineer.

Live at **https://khlaifiabilel.github.io**

## Stack

Static HTML, CSS and vanilla JavaScript. No build step, no framework, no
dependencies, no webfonts, no analytics. GitHub Pages serves the files directly,
so a `git push` is the whole deploy.

```
index.html          all page content
styles.css          monochrome design system, light + dark
script.js           theme toggle, active nav, live star counts
blog/               long-form technical research notes and their figures
resume/             downloadable PDF resume
assets/favicon.svg  monogram favicon
assets/og.png       social preview (1200x630)
assets/og-source.svg  square render source for og.png
.nojekyll           serve files as-is, skip Jekyll
robots.txt          crawler policy
sitemap.xml         single-page sitemap
```

## Local preview

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Editing

**Content** lives entirely in `index.html`, in labelled sections:

| Section | Anchor |
| --- | --- |
| Hero | `#top` |
| What I work on | `#focus` |
| Selected work | `#work` |
| Technical blog | `#blog` |
| Experience | `#experience` |
| Research & teaching | `#research` |
| Technical | `#skills` |
| Contact | `#contact` |

**Location** is at `<span class="v" id="location">` in the hero.

**Colours** are CSS custom properties at the top of `styles.css` — `:root` for
light, `[data-theme="dark"]` for dark. The palette is intentionally pure
monochrome; changing `--fg` and `--bg` restyles the whole site.

### Adding a repository card

Add an `<article>` to `#repos` in `index.html`. The `data-repo` attribute must
match the GitHub repository name so the live star count binds to it:

```html
<article class="card repo" data-repo="my-repo">
  <div class="repo-top">
    <h4><a href="https://github.com/khlaifiabilel/my-repo" target="_blank" rel="noopener">my-repo</a></h4>
    <span class="stars" data-stars>0</span>
  </div>
  <p>One-sentence description.</p>
  <ul class="chips" role="list"><li>Python</li><li>MIT</li></ul>
</article>
```

The number you type in `data-stars` is the fallback shown before the API
responds, and the value that stands if a visitor blocks the request. Keep it
roughly accurate.

### Regenerating the social image

`assets/og.png` is rendered from `assets/og-source.svg`. That source is a 1200x1200
square because macOS `qlmanage` pads SVGs to a square canvas; the content sits in
the centre 630px band so the crop lands correctly.

```bash
cd assets
qlmanage -t -s 1200 -o . og-source.svg
mv og-source.svg.png og.png
sips -c 630 1200 og.png --out og.png
```

## Behaviour notes

- **Theme** follows the OS by default and remembers an explicit choice in
  `localStorage`. Clearing storage returns it to OS-following.
- **Star counts** are fetched once from the public GitHub API and cached in
  `sessionStorage` for six hours. The API allows 60 unauthenticated requests per
  hour per IP; on failure the page silently keeps the hardcoded numbers.
- **Progressive enhancement** — with JavaScript disabled the page renders fully;
  only the toggle, nav highlighting and live stars are lost.
- **Print** styles are included, so the page prints as a clean CV.

## Accessibility

Semantic landmarks, a skip link, visible focus rings, `aria-pressed` on the
toggle, and `prefers-reduced-motion` support. Contrast is maximal by design.

## Licence

Code is MIT. Written content, CV text and imagery are © Bilel Khlaifia.
