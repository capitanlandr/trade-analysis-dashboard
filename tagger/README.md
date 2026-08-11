# tagger

Turn a **Moxfield deck** into a **Moxfield-import-ready CSV** where every card
carries its **Scryfall Tagger functional tags** — the card's own oracle tags
*plus* every inherited (ancestor) oracle tag.

```
tagger https://moxfield.com/decks/FStnnI53C0ej6tMd5eEPAg
```

That writes `Twincasters_Refocused.csv`. In Moxfield: **More → Import → Deck**
(or a collection), upload the CSV, and each card lands with its tags already
attached — so you can immediately filter/group the deck by `token-doubler`,
`ramp`, `card-advantage`, `removal`, etc.

## What "functional tags" means

Scryfall Tagger has two tag families:

| Tag family | Tagger type | Example | Included? |
|---|---|---|---|
| **Functional / oracle** | `ORACLE_CARD_TAG` | `rhystic`, `ward`, `token-doubler` | ✅ yes |
| Artwork / illustration | `ILLUSTRATION_TAG` | `merfolk`, `character` | ❌ no (use `--include-art`) |

For each card, `tagger` collects:
1. the card's **own** functional tags, and
2. all **inherited** tags from each tag's `ancestorTags` chain.

Example — *Adrix and Nev, Twincasters* (`mkc/198` == `c21/336`, oracle tags are
printing-independent) produces:

```
cycle cycle-c21-face-commander face-commander hate hate-target
multi-character-card rhystic synergy-token tax token-doubler
token-increaser triggered-ability ward
```

## Install

Pure Python 3 standard library — **no pip dependencies** on networks where
Moxfield's Cloudflare check passes with a browser User-Agent (e.g. corporate
networks / dev desktops).

```bash
# dev desktop / Mac
install -m 0755 tagger ~/.local/bin/tagger   # ~/.local/bin is already on PATH
tagger --help
```

**Residential / restricted networks:** Moxfield may return a Cloudflare JS
challenge (HTTP 403). Install the optional `cloudscraper` package to bypass it —
`tagger` uses it automatically for the Moxfield fetch when present:

```bash
pip3 install --user cloudscraper
```

Scryfall Tagger and the Scryfall REST API work over plain HTTPS everywhere, so
only the Moxfield fetch may need cloudscraper.

## Usage

```
tagger <moxfield-deck-url-or-id> [options]
```

| Option | Default | Description |
|---|---|---|
| `-o, --output PATH` | `<deck-name>.csv` | output CSV path |
| `--boards a,b,c` | `commanders,mainboard,companions,signatureSpells` | which boards to include |
| `--all-boards` | off | include every board (adds maybeboard, sideboard, attractions, stickers) |
| `--include-art` | off | also emit artwork/illustration tags |
| `--tag-format {slug,name}` | `slug` | `slug` = hyphenated (`token-doubler`); `name` = display (`token doubler`) |
| `--sep {space,comma}` | `space` | delimiter between tags inside the Tags column |
| `--delay SEC` | `0.1` | pause between Tagger requests (politeness) |
| `-q, --quiet` | off | suppress per-card progress on stderr |

### Examples

```bash
tagger FStnnI53C0ej6tMd5eEPAg                      # bare deck id works too
tagger <url> -o mydeck.csv                         # explicit output
tagger <url> --all-boards                          # include maybeboard/sideboard
tagger <url> --tag-format name --sep comma         # "token doubler, ward, ..."
tagger <url> --include-art                          # add artwork tags
```

## Output format

Standard Moxfield deck-CSV columns:

```
Count,Tradelist Count,Name,Edition,Condition,Language,Foil,Tags,
Last Modified,Collector Number,Alter,Proxy,Purchase Price
```

Only `Count`, `Name`, `Edition` (set code), `Collector Number`, and `Tags`
are populated; the rest are left blank/default. Tags are **space-separated
slugs** by default (Moxfield's native round-trip format).

> **Tip:** if a Moxfield import ever splits/ignores multi-word tags, re-run with
> `--tag-format slug` (the default) so tags stay single tokens, or try
> `--sep comma`.

## How it works

1. **Moxfield** — `GET https://api.moxfield.com/v2/decks/all/<id>` (a browser
   `User-Agent` is required to pass Cloudflare; on residential IPs it falls back
   to `cloudscraper` if installed) → gives each card's set code + collector
   number.
2. **Scryfall Tagger** — scrape a CSRF token + session cookie from
   `tagger.scryfall.com`, then POST the `FetchCard` GraphQL query per card.
3. **Fallback** — if a specific printing isn't in Tagger's DB, resolve a
   printing via the Scryfall REST API (`/cards/named`) and retry. Oracle tags
   are shared across printings, so the result is identical.
4. **Robustness** — transient Tagger throttling is retried with exponential
   backoff, and any card that still fails a burst is retried in follow-up
   sweeps before the CSV is written. A card is only left untagged if Tagger
   genuinely returns no functional tags for it (e.g. basic lands).

## Notes & limits

- Multi-face cards are queried on their front face (functional tags generally
  cover the whole card).
- Tag data is community-maintained on Scryfall Tagger and can change over time.
- This uses Tagger's unofficial GraphQL endpoint the website itself calls; be
  polite with `--delay` on very large decks.
