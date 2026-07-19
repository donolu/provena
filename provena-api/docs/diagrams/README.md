# Diagrams

Source diagrams for the Provena docs. Each diagram is authored in **draw.io**; export a PNG (or SVG) into this directory using the exact filename referenced by the docs, so the `![...](./diagrams/<name>.png)` embeds render on GitHub.

| Referenced by | Export as | Contents |
|---|---|---|
| `DATABASE_SCHEMA.md` | `provena-erd.png` | Entity-relationship diagram across all apps |
| `USER_JOURNEYS.md` | `journey-checkout.png` | Buyer checkout / money path |
| `USER_JOURNEYS.md` | `journey-order-lifecycle.png` | Order → fulfilment → payout lifecycle |
| `USER_JOURNEYS.md` | `journey-returns-refund.png` | Returns and admin item-refund attribution |
| `UIUX_BRIEF.md` | `sitemap.png` | Navigation map / sitemap by actor |

## Editing

Open the `.drawio` source in [draw.io](https://app.diagrams.net) (or the drawio tooling), edit, then **File → Export as → PNG** (transparent background, 2x scale) into this folder using the filename above. Keep the `.drawio` source committed alongside the exported image so the diagram stays editable.

> Diagrams are exported images, so they can drift from the models/flows. When you change a model or a journey, re-export the affected diagram in the same PR.
