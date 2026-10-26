# Vendored browser libraries

Committed rather than fetched from a CDN. A local tool that cannot draw a
diagram without outbound internet is useless in exactly the environment this is
meant for: a company network that stops the page reaching a CDN.

| File | Package | Version | Licence |
|---|---|---|---|
| `cytoscape.min.js` | cytoscape | 3.34.1 | MIT |
| `dagre.min.js` | dagre | 0.8.5 | MIT |
| `cytoscape-dagre.js` | cytoscape-dagre | 3.0.0 | MIT |
| `elk.bundled.js` | elkjs | 0.12.0 | EPL-2.0 |
| `maxgraph.min.js`, `maxgraph.css` | @maxgraph/core | 0.25.0 | Apache-2.0 |

The first three are MIT; elkjs (the Eclipse Layout Kernel compiled to
JavaScript) is under the Eclipse Public License 2.0, which permits
redistribution of the unmodified build. It lays out the layered drawings:
containers as containers, edges routed around nodes and boundaries, labels
placed by the layout. Dagre remains as the fallback when it is absent. Each license's full text
is in `LICENSES/` at the repository's root and listed in
`THIRD_PARTY_NOTICES.md`, and travels inside the package; the copyright
notices are kept in the minified files too.

To update, install the package and copy its `dist/` build in. Nothing here is
modified from upstream.

maxGraph draws the canvas, the diagram drawn by hand (`canvas/`); the views
written as a query stay on Cytoscape. It ships only as ES modules, so its
bundle is made once, here, rather than in the app, which keeps its no-build
rule: `npm pack @maxgraph/core@0.25.0`, then esbuild 0.25.0 over an entry of
`export * from './package/lib/esm/index.js'` with `--bundle --minify
--format=iife --global-name=maxgraph --target=es2017`, and a banner carrying
its copyright and license line, since minifying drops the modules' own.
`maxgraph.css` is the package's `css/common.css`. The version is pinned: it
is before 1.0 and its API moved between releases, so every call to it goes
through one module of the canvas's, `canvas/engine.js`, which loads it the
first time a canvas draws, never with the page.
