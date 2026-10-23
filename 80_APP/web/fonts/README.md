# Fonts

Self-hosted, because the page runs under `default-src 'self'` and a font
fetched from Google would never arrive. Latin subsets in woff2 only, copied
from Fontsource 5.3.0 (`@fontsource/geist`, `@fontsource/geist-mono`,
`@fontsource/libre-franklin`). All three are under the SIL Open Font
License 1.1.

| Family | Weights | Used for |
|---|---|---|
| Geist | 400, 500, 600, 700 | the interface: labels, body, buttons, the rail |
| Libre Franklin | 700, 800 | the name of a thing: a page's title, a view's name, an entity's name in the inspector, the numbers on the home page |
| Geist Mono | 400, 500 | code only: the YAML editor, the Source panel, finding codes |

Each face's license is in `LICENSES/` at the repository's root. To add a weight, install the package in `80_APP/tools` and copy the
file from its `files/` folder; `styles.css` declares each face.
