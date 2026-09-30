# Fonts shipped with preview_cards.py

The cards draw Latin text, labels and numbers with these three faces, so a card looks the same on every
machine. Chinese text comes from the machine's own fonts, because a Chinese face is tens of megabytes.

| file | face | used for | licence |
|---|---|---|---|
| `Inter-latin-var.woff` | Inter, variable weight 100–900, Latin subset | body text | SIL OFL 1.1, `OFL-Inter.txt` |
| `Fraunces-latin-var.woff` | Fraunces, variable weight 100–900, Latin subset | Latin in the cover line, drawn at weight 700 | SIL OFL 1.1, `OFL-Fraunces.txt` |
| `SpaceMono-latin-400.woff` | Space Mono Regular, Latin subset | labels, character counts, page numbers | SIL OFL 1.1, `OFL-SpaceMono.txt` |

Where they come from: the Fontsource packages `@fontsource-variable/inter` 5.2.8, `@fontsource-variable/fraunces`
5.2.9 and `@fontsource/space-mono` 5.2.9. Space Mono is that package's `space-mono-latin-400-normal.woff`,
unchanged. Inter and Fraunces were published only as WOFF2, which Pillow cannot read, so their
`*-latin-wght-normal.woff2` files were re-saved as WOFF 1.0 with fontTools. The glyph outlines are unchanged,
only the container is different.

| file | sha256 |
|---|---|
| source `inter-latin-wght-normal.woff2` | `3100e775e8616cd2611beecfa23a4263d7037586789b43f035236a2e6fbd4c62` |
| source `fraunces-latin-wght-normal.woff2` | `7f9d191d999336d3b9790afa72e1358e50a13b06d4f289341e92a311967a80f9` |
| `Inter-latin-var.woff` | `344886797e5c55a0b95b56395376cfbd3acdef2cbb5786cd4a0d1c638f63dc4c` |
| `Fraunces-latin-var.woff` | `687afe450a979929b80e6167363c56ec4e3870216b052c6b5b38930d664f01ad` |
| `SpaceMono-latin-400.woff` | `d9d02a663d01b5d0a75eea2dce0ac220c0eb94aa0144f1191d0e7faff759716c` |

The Latin subsets have no arrows, check marks or box-drawing characters. When a card needs one of those,
`preview_cards.py` draws that character with the next font that has it, as it already does for Chinese.
