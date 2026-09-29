# First Material Probe

Two source-checked leads were saved separately from X research posts in `data/seed_materials.json` and the SQLite `materials` table. `SOURCE_CHECKED` means the first-party page was read, not that product claims were replicated.

| Lead | Discovery and original source | What can currently be said | Before drafting |
| --- | --- | --- | --- |
| Small local decision models | [HN item](https://news.ycombinator.com/item?id=49883844) -> [Jeff repository](https://github.com/firelex/jeff) | The project publicly describes small locally runnable classifier models. | Test the actual model on a relevant Chinese task, inspect license/weights, measure local hardware cost; do not repeat benchmark claims as fact. |
| Document conversion edge cases | [MarkItDown v0.1.8 release](https://github.com/microsoft/markitdown/releases/tag/v0.1.8) | Official notes describe OCR-plugin maintenance and encoding/format fixes. | Reproduce a concrete file conversion before claiming improvement; check any cloud-backed optional feature costs. |

This proves the local material workflow accepts first-party links, stores brief original observations and schedules rechecks. It does not yet prove either lead is worth publishing. Reddit is excluded from import while usage rights for this project are unresolved.

