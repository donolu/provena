# Diagrams

All Provena doc diagrams live in a single editable draw.io source with one **tab (page)** per diagram:

**`provena-diagrams.drawio`**

| Tab | Referenced by | Export as |
|---|---|---|
| Checkout money path | `USER_JOURNEYS.md` | `journey-checkout.png` |
| Order lifecycle | `USER_JOURNEYS.md` | `journey-order-lifecycle.png` |
| Returns and refund attribution | `USER_JOURNEYS.md` | `journey-returns-refund.png` |
| Entity-relationship | `DATABASE_SCHEMA.md` | `provena-erd.png` |
| Sitemap | `UIUX_BRIEF.md` | `sitemap.png` |

## Viewing and editing

Open `provena-diagrams.drawio` in [draw.io](https://app.diagrams.net) (File → Open, or drag it in) or the desktop app. The tabs along the bottom switch between diagrams. Edit freely; draw.io routes the edges.

## Exporting the PNGs the docs embed

The `.md` files embed `![...](./diagrams/<name>.png)`. To make those render on GitHub, export each tab once:

1. Select the tab.
2. **File → Export as → PNG…**, transparent background, 2x scale.
3. Save into this folder with the exact filename from the table above.

> The `.drawio` source is the source of truth; the PNGs are generated artefacts. When you change a model or a flow, edit the relevant tab and re-export its PNG in the same PR.
