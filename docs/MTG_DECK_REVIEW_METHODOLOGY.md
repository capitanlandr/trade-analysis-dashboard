# MTG Commander Deck Review Methodology

This document records the process and mental model developed while reviewing the Kuja, Genome Sorcerer // Trance Kuja, Fate Defied Commander deck. It is intended to make future deck reviews repeatable while preserving the deck builder's actual goals, constraints, and vocabulary.

## 1. Establish the authoritative inputs

Use three layers of information, in this order:

1. **The current Moxfield deck** is authoritative for the cards currently played. Pull it from the public Moxfield deck URL with the local `tagger/tagger` CLI.
2. **The owner's Moxfield-style text list** is authoritative for custom tags and deck intent. Preserve its syntax exactly:
   - `#!Tag` means a global tag used across decks, such as staples, ramp, land, or card advantage.
   - `#Tag` means a tag specific to this deck.
3. **Scryfall Oracle text, type lines, and functional tags** are verification and discovery data. They help explain what a card actually does, but they do not replace the owner's strategic labels.

The current export workflow is:

```bash
./tagger/tagger 'https://moxfield.com/decks/<DECK_ID>' -o current.csv
```

The CLI fetches the Moxfield deck, resolves each printing through Scryfall, queries Scryfall Tagger for functional `ORACLE_CARD_TAG` tags, includes inherited ancestor tags, retries transient failures, and produces a Moxfield-import-ready CSV.

For an individual ambiguous card, verify the Oracle text and type line through Scryfall's public card API or card page. This is especially important for double-faced cards, Adventures, MDFCs, reskins, token creators, and cards whose strategic role is not obvious from a functional tag.

## 2. Normalize before comparing

Compare cards by their actual game identity, not only by the printed name in the deck text.

Important normalization rules:

- Treat MDFCs as lands when evaluating a 38-land target, while also considering the spell side.
- Treat reskins as the underlying card when checking functionality. In this deck, `S.H.I.E.L.D. Spy Satellite (MSC) 285` is a reskinned `Fellwar Stone`; the name difference is not a functional discrepancy.
- Preserve the user's display name when producing their Moxfield-style text file unless the import requires the canonical name.
- Count Commander separately from the 99-card library for probability calculations.
- Distinguish unique-card counts from copies. A list may contain 100 cards but fewer unique names because of basic lands.

## 3. Interpret the deck's strategic mental model

The deck is not merely a generic Rakdos spellslinger deck. Its structure is a layered Wizard/noncreature-spell engine:

```text
Wizard bodies and 0/1 Wizard tokens
              │
              ▼
     Enable Kuja's transformation
              │
              ▼
 Cast noncreature spells repeatedly
              │
              ▼
   Trigger multiple damage payoffs
              │
              ▼
   Apply doublers and finish incrementally
```

The plan is built around six practical categories:

### Plan enablers

Enablers establish the infrastructure that lets Kuja's plan function. The most important enablers are:

- Cards that create the exact 0/1 black Wizard tokens whose triggered ability deals damage whenever a noncreature spell is cast.
- Wizard creatures that increase the relevant Wizard count and help unlock the commander's back side.
- Noncreature spells that create Wizards, such as Transpose, Vivi's Persistence, and Lindblum's Adventure.
- Cost reduction or spell-volume effects that allow several noncreature spells to be cast in one turn. These can be tagged as plan enablers even when they are not Wizards; this is a different kind of enabler from a Wizard/token enabler.

Do not automatically classify every noncreature spell as an enabler. A generic Arcane Signet is primarily ramp. A noncreature spell becomes a plan enabler when it creates the relevant token, is a Wizard-related permanent, or materially increases the number or efficiency of noncreature spells being cast.

### Plan payoffs

Payoffs are the bodies or effects that turn noncreature-spell volume into a win condition. The clearest examples have text like:

> Whenever you cast a noncreature spell, this deals damage to each opponent.

Payoffs tend to be visible, incremental, and disruptable. They should be tracked separately from generic burn or removal because the deck wants the opponent-facing damage trigger itself.

### Enhancers

The deck builder uses “enhancers” for doublers and multipliers:

- Damage multipliers such as City on Fire, Dictate of the Twin Gods, and Fiery Emancipation.
- Damage increasers such as Artist's Talent.
- Trigger doublers such as Harmonic Prodigy and Roaming Throne.

Enhancers are not “answers” in the interaction sense. In this deck's vocabulary, “answers” should not be used as a substitute for enhancers.

### Card advantage versus card selection

The distinction is intentional:

- **Card advantage** means a card produces more resources than it consumes—for example, sacrificing one resource to draw two, or drawing two after discarding one.
- **Card selection** means the hand or top of library is improved without necessarily increasing card count—for example, draw one/discard one, rummage, loot, or impulse selection.

Scryfall's `card-advantage` tag is broad and often means that a card lets the player see more cards. It should therefore be reviewed against the Oracle text rather than copied blindly.

Examples from this deck:

- Big Score, Unexpected Windfall, Village Rites, Deadly Dispute, Sign in Blood, and Plumb the Forbidden are strong card-advantage candidates.
- Faithless Looting, Artist's Talent's rummage ability, Thrill of Possibility, and Transpose are primarily selection or filtering effects.
- Some cards can carry both labels when they provide selection plus a net resource increase.

### Ramp

Ramp includes more than mana rocks:

- Conventional mana rocks: Arcane Signet, Fellwar Stone, Mind Stone, Sol Ring, and Talisman of Indulgence.
- Rituals: Dark Ritual, Cabal Ritual, Desperate Ritual, and Seething Song.
- Treasure production: Big Score, Unexpected Windfall, Deadly Dispute, Pirate's Pillage, and Warren Soultrader.
- Cost reduction: Artist's Talent and Longshot. These are tagged as global `#!Ramp` in the owner's taxonomy even though they are not mana producers.

When reviewing density, distinguish reliable ongoing mana from one-shot rituals, conditional mana, Treasures, and cost reduction. They all accelerate the deck, but they do not have the same mulligan or late-game value.

### Removal and broader answers

For this deck, removal is permanent interaction:

- Targeted removal: creature, artifact, enchantment, or other single-target answers.
- Mass removal: sweepers or multi-removal effects.

Protection and counterspells should be tracked separately from removal. Deflecting Swat, Lightning Greaves, Redirect Lightning, and Tibalt's Trickery protect the engine or interact on the stack; they are not the same category as Blasphemous Act, Toxic Deluge, or Infernal Grasp.

## 4. Compare custom tags to Scryfall mechanically

Perform the comparison in two directions.

### Validate existing labels

Ask whether Oracle text supports the owner's tag. Examples:

- `#!Ramp` should be supported by mana production, Treasure creation, ritual mana, or meaningful cost reduction.
- `#!Card Advantage` should normally represent a net increase in resources, not merely looking at extra cards.
- `#!Targeted Disruption - counterspell` should be reserved for actual counter magic.
- `#!Targeted Disruption - Artifact` should include effects such as destroy target artifact.
- `#!Plan - Enhancer` should represent a multiplier, damage increase, or trigger doubler.
- `#Plan - Enabler` should be tied to Wizards, the exact 0/1 Wizard tokens, or increased noncreature-spell volume.
- `#Plan - Payoff` should represent a meaningful noncreature-spell damage engine or comparable win-condition body.

### Find omitted secondary labels

Then inspect Scryfall tags for useful labels missing from Moxfield. Prioritize omissions that affect deck decisions rather than obscure implementation tags. In this deck, useful additions included:

- Big Score and Unexpected Windfall as both card advantage and Treasure ramp.
- Tibalt's Trickery as `#!Targeted Disruption - counterspell`.
- Untimely Malfunction as `#!Targeted Disruption - Artifact`.
- Descent into Avernus as Treasure ramp and a damage effect that benefits from doublers.
- Sorceress's Schemes as recursion plus a ritual-like red mana effect.
- War Room as repeatable land-based card advantage.

Do not force Scryfall's entire functional vocabulary into Moxfield. Tags such as `group-slug`, `type-errata`, `virtual-vanilla`, or `cast-trigger-you` may be mechanically true but strategically unhelpful.

## 5. Evaluate Bracket 2 deliberately

Bracket 2 is an experience target, not merely a card legality checklist. The official description emphasizes straightforward, unoptimized decks; incremental, telegraphed, disruptable wins; proactive gameplay; and games that generally reach around eight turns.

Therefore, evaluate a candidate card on both power and identity:

- A card can be powerful but appropriate if it is on-theme, visible, and gives opponents time to respond.
- A card can be legal but inappropriate if it creates explosive fast-mana starts, generic tutors, deterministic early combos, or a highly optimized engine.
- Prefer Wizard and Wizard-token redundancy when it preserves the deck's identity, even if a generic non-Wizard card is technically stronger.

Examples:

- **Storm-Kiln Artist** is an excellent spellslinger card, but excluding it is defensible because it is not a Wizard and would make the deck more explosive.
- **Chaos Warp** is a popular Rakdos staple, but it is not mandatory when the deck already has sufficient Rakdos removal and the builder prefers more thematic cards.
- **Feed the Swarm** answers enchantments but is sorcery speed; it may be less desirable when the deck values holding up interaction or casting multiple proactive spells.
- **Jeska's Will, Demonic Tutor, Vampiric Tutor, Ancient Tomb, Mana Vault, Chrome Mox, Mox Diamond, Lotus Petal, and The One Ring** should be screened against the current Game Changers list before considering them for a Bracket 2 build.

## 6. Use probability to test consistency

For a question such as “How often do I see a proactive two-mana play by the first nine cards?” use the hypergeometric distribution:

```text
P(at least one hit) = 1 - C(N - K, n) / C(N, n)
```

Where:

- `N` is the library size, normally 99 in Commander after excluding the commander.
- `K` is the number of cards satisfying the definition.
- `n` is the number of cards seen, normally 9 for an opening seven plus two draw steps.

The definition of “hit” must be stated before counting. For the Kuja deck, a proactive two-mana play excludes reactive removal and counterspells, but includes a two-mana Wizard, engine, equipment, draw spell, or ramp piece that advances the plan. With 16 qualifying cards, the result was approximately 81.0% for at least one hit by card nine, 44.6% for at least two, and 72.1% in the opening seven alone. These figures do not include mulligan decisions.

## 7. Preserve the reasoning behind specific deck choices

The deck builder's explanations are part of the data, not incidental commentary. They explain why a mechanically stronger card may be rejected and why a less efficient card should remain.

### Mysidian Elder stays

Mysidian Elder is a three-mana Wizard that creates a 0/1 Wizard token. It therefore represents two Wizard bodies for the commander's transformation plan, not merely a three-mana one-damage payoff. It can be followed by Kuja on turn four, and its token remains a noncreature-spell damage engine.

### Longshot stays

Longshot is a four-mana payoff that deals two damage to each opponent for every noncreature spell and reduces the cost of noncreature spells by {1}. It is one of the deck's strongest payoff bodies because it is simultaneously a payoff and a spell-volume enabler. Its `#Plan - Enabler` label should be understood as cost-reduction/spell-volume support, not as a claim that Longshot is a Wizard-token enabler.

### Descent into Avernus stays

Descent into Avernus gives opponents Treasures, but it also deals escalating damage to every player. In a deck with multiple damage doublers, that symmetrical drawback is part of a deliberate secondary win condition rather than an automatic reason to cut the card.

### Mox Amber was removed

Mox Amber is attractive because it is free to cast and can accelerate early turns. It was ultimately removed because it is conditional before a legendary creature is established and does not contribute to the Wizard/token identity. This is a power-down and consistency decision, not a claim that Mox Amber is weak in optimized decks.

### Rockslide Sorcerer was removed

Rockslide Sorcerer deals damage to any target when an instant, sorcery, or Wizard is cast, but it costs four mana and is primarily a single-target damage/removal engine. The deck prefers cards that create more Wizard bodies, deal damage to each opponent, or multiply existing triggers. Mysidian Elder therefore fits the deck's architecture better even though Rockslide Sorcerer has more targeting flexibility.

### Flashback became War Room

Flashback is a narrow recursion effect, and the deck already contains several recursion engines. War Room both helps reach the 38-land target—including MDFCs—and provides repeatable card draw from a land slot. This is the preferred kind of exchange: reduce a redundant narrow spell while improving mana stability and late-game resources.

## 8. Current review workflow checklist

For a future deck review:

1. Pull the current Moxfield deck and record total cards, main deck, commander, unique cards, and lands including MDFCs.
2. Load the owner's tagged text list without stripping `#!` versus `#`.
3. Normalize reskins, MDFCs, Adventures, and split names.
4. Verify ambiguous Oracle text and creature/token types.
5. Count payoffs, plan enablers, enhancers, card advantage, card selection, removal, and ramp.
6. Separate broad mechanical Scryfall tags from the owner's strategic categories.
7. Identify omitted tags only when they improve a real deckbuilding or mulligan decision.
8. Apply the Bracket 2 lens: theme, visibility, disruptability, speed, and generic optimization.
9. Use hypergeometric calculations only after defining the hit category precisely.
10. Recommend swaps, not automatic additions, while protecting the 38-land target and the Wizard/token engine.
11. Preserve the reasoning for accepting or rejecting each recommendation.
12. If a text export is requested, write Moxfield syntax exactly and verify that every card line is tagged or intentionally untagged.
