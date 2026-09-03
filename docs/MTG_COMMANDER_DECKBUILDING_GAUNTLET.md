# MTG Commander Deckbuilding Gauntlet

This is the reusable harness for building a Commander deck from a commander, a stated gameplay goal, and a bracket target. It extends the [MTG Deck Review Methodology](MTG_DECK_REVIEW_METHODOLOGY.md) from analysis into deck construction.

The harness is designed to answer two different questions for every card:

1. **Does this card help the deck do what it is supposed to do?**
2. **Does it belong in this version of the deck, given the intended bracket, theme, speed, and experience?**

The result is not “the objectively best Commander deck.” It is a reproducible deck that is optimized for a declared objective function rather than for raw EDHREC popularity.

## 1. Required inputs

Before selecting cards, declare the following:

```yaml
commander: "Commander name"
bracket: 2
deck_size: 100
land_target: 38
theme_constraints:
  - "Example: prioritize Wizards and Wizard-producing cards"
  - "Example: avoid generic non-Wizard spellslinger upgrades when possible"
gameplay_goal: "Describe how the deck should win"
acceptable_speed: "Example: generally no win before turn eight"
must_have_roles:
  - payoffs
  - plan_enablers
  - enhancers
  - card_advantage
  - card_selection
  - removal
  - ramp
```

The commander and bracket are not enough by themselves. The deck builder's explanation of why a card is appealing is part of the input. For example, a free mana rock may be rejected because it is not a Wizard, while a slower Wizard token maker may be preferred because it advances the commander transformation plan.

## 2. Decide whether the build is top-down or bottom-up

### Top-down build

Use top-down construction when the commander has a specific build-around ability. The commander is the primary engine, and the deck is built backwards from the ability:

```text
Commander ability
→ required resource or game state
→ enablers
→ payoffs
→ enhancers
→ protection, draw, removal, and mana
```

Kuja is a top-down example. The relevant chain is Wizard bodies and 0/1 Wizard tokens, then noncreature-spell casting, then opponent-facing damage triggers, then damage and trigger doublers.

### Bottom-up build

Use bottom-up construction when the commander is mostly a value accessory, a color identity provider, or a modest engine inside a broader archetype. First define the archetype and its normal shell, then choose the commander that improves it.

### Hybrid rule

Most decks should be hybrid. Build the central engine top-down, then use bottom-up standards for the support shell. The support shell still has to serve the deck's stated identity; generic staples are candidates, not automatic inclusions.

## 3. Read the commander as a rules engine

The Oracle-text pass should produce a short engine specification:

| Question | Output |
|---|---|
| What does the commander reward? | Casts, tokens, attacks, sacrifice, draw, life loss, etc. |
| What must be on the battlefield first? | Bodies, card types, creature types, counters, lands, or colors |
| What does the commander create? | Mana, tokens, cards, damage, recursion, or selection |
| What causes the commander to fail? | Removal, timing, colors, combat dependence, graveyard hate |
| What is the natural win condition? | Incremental damage, combat, combo, inevitability, or a large turn |
| What is the cheapest meaningful setup? | The earliest proactive sequence worth measuring |

Resolve every ambiguous detail from Oracle text and type lines. Never infer token type, creature type, MDFC status, or front/back-face behavior from a name alone.

## 4. Build the role map before choosing cards

Assign the deck's role definitions before searching for candidates.

### Payoffs

Cards that convert the commander resource into victory. For Kuja, this includes creatures or effects that deal damage when noncreature spells are cast.

### Plan enablers

Cards that establish the engine: relevant Wizards, exact Wizard-token makers, or effects that substantially increase noncreature-spell volume. Cost reduction can be an enabler even when the card is not a Wizard, but it should be distinguished from a Wizard/token enabler.

### Enhancers

Cards that multiply the engine: damage doublers, damage increasers, trigger doublers, or similar amplifiers.

### Card advantage

Cards that create a net resource gain, such as drawing two after spending one card or recurring a card while also producing another resource.

### Card selection

Cards that improve the quality or timing of cards without necessarily increasing net card count: looting, rummaging, draw-one/discard-one, scrying, and impulse draw.

### Removal

Cards that answer opposing permanents or boards. Keep targeted removal, mass removal, and flexible modal removal as separate subroles.

### Ramp

Cards that increase available mana, including mana rocks, rituals, Treasures, land acceleration, and the owner's accepted cost-reduction category. Track ongoing mana separately from one-shot rituals and conditional acceleration.

## 5. Use a declared goal function

Every candidate receives a score based on the deck's goal function. A practical model is:

```text
Candidate Score =
  wC × Commander Synergy
  + wP × Plan Contribution
  + wR × Role Value
  + wE × Efficiency
  + wQ × Reliability
  + wI × Interaction Value
  + wH × EDHREC Prior
  - wB × Bracket Tension
  - wT × Theme Violation
  - wD × Downside
  - wX × Redundancy Cost
```

The weights are not universal. For a Kuja Bracket 2 deck, the priorities would normally be:

1. Commander and Wizard/token-plan synergy
2. Observable contribution to the noncreature-spell damage engine
3. Reliable mana and card flow
4. Bracket fit and disruptability
5. General EDHREC popularity

EDHREC popularity is a useful prior: it tells us that a card has worked in many decks. It is not a command to include the card. A popular Rakdos card that ignores Wizards, tokens, or the intended pace can score below a less popular on-theme card.

### Scoring rubric

Use a simple 0–5 score for each factor and record the reason, not just the number:

| Factor | 0 | 3 | 5 |
|---|---|---|---|
| Commander synergy | Unrelated | Helpful in some games | Directly advances the commander engine |
| Plan contribution | No plan role | Indirect support | Creates the required resource or payoff |
| Role value | Fills no need | Replaces an existing role | Fills a missing or overloaded role |
| Efficiency | Too expensive or conditional | Acceptable | Efficient at the deck's intended pace |
| Reliability | Often dead | Context-dependent | Useful in most game states |
| Interaction value | None | Narrow | Flexible, relevant interaction |
| EDHREC prior | Uncommon | Established | Very popular in the identity |
| Bracket tension | Strongly inappropriate | Borderline | Naturally fits the bracket |
| Theme violation | Breaks the deck identity | Tolerable exception | Fully on theme |

The numerical score should support judgment, not conceal it. If two cards are close, prefer the one that better expresses the deck's identity.

## 6. Search and evidence workflow

Use multiple searches with different purposes:

1. **Commander identity search** for popular cards:
   `f:commander id:<color-identity> sort:edhrec`
2. **Oracle searches** for the commander mechanic:
   - Exact phrases from the commander text
   - Relevant token text
   - Creature types and card types
   - Trigger, draw, sacrifice, mana, or damage effects
3. **Functional-tag searches** for candidate expansion:
   - Scryfall Tagger functional tags
   - `o:` searches for mechanical patterns
4. **Oracle verification** for every card that affects a category count or a key curve decision.

Record which source contributed what:

- Moxfield: current deck contents and custom intent tags
- EDHREC: popularity prior and common identity shell
- Scryfall: legality, identity, printing, Oracle text, type lines, and searchable mechanics
- Scryfall Tagger: community-maintained functional tags and inherited tag relationships
- Human judgment: theme, bracket, role overlap, play-pattern quality, and acceptable risk

## 7. Lands get full card-by-card treatment

Lands are not filler and should receive the same rationale as spells. For every land, record:

- Color sources and which early spells it supports
- Whether it enters tapped and the tempo cost
- Basic land types and fetchability
- Utility effect and how often it matters
- Whether it is an MDFC and the opportunity cost of the spell side
- Whether it supports the commander tribe or plan
- Whether it is conditional, such as Coffers, Nykthos, or a creature-count land

The default land audit is:

```text
Total cards = 100
Commander = 1
Library = 99
Land target = declared number, including MDFCs when the owner says they count
Color-source test = can the deck cast its important early spells on time?
Tapped-land test = are the tempo costs acceptable?
Utility test = does each nonbasic earn its slot?
```

For the Kuja deck, the declared target is 38 lands including MDFCs. War Room was attractive because it both satisfies the land target and adds repeatable card advantage from a land slot.

## 8. Run the gauntlet tests

The build is not complete when it reaches 100 cards. It must pass these tests.

### A. Role coverage

Count cards using the owner's definitions, then count them again using conservative Oracle-supported definitions. Explain overlaps instead of hiding them. A card may be both a payoff and an enabler, or both card advantage and ramp.

### B. Curve and proactive opening

Define a proactive two-mana play precisely. Then calculate the probability of seeing at least one by card nine:

```text
P(at least one) = 1 - C(N - K, n) / C(N, n)
```

Use `N = 99`, `n = 9`, and `K` equal to the verified number of qualifying cards. State whether mulligans, the commander, MDFCs, and reactive cards are included.

### C. Commander deployment sequence

Write the intended early sequence in plain language. For Kuja, test sequences such as:

```text
Turn 2: proactive setup
Turn 3: Wizard or Wizard-token development
Turn 4: cast Kuja with enough Wizard infrastructure
Turn 5+: cast multiple noncreature spells and convert triggers into damage
```

If a card does not improve a realistic sequence, its synergy score should fall even if it is popular.

### D. Recovery test

Ask what happens after the commander or one payoff is removed. A healthy deck should still have alternate Wizards, token makers, card flow, and at least one path to rebuild.

### E. Interaction test

Check whether the deck can answer creatures, artifacts, enchantments, graveyards, and opposing win attempts at the intended table. Do not inflate the answer count by treating every removal spell as a counterspell or protection effect.

### F. Bracket test

For Bracket 2, reject or flag cards that create fast-mana openings, deterministic early combos, generic optimization without theme value, or wins that do not give the table time to respond. A card can be legal and still be a poor fit for the intended Bracket 2 experience.

## 9. Produce the reviewable output

The final deliverable should contain all of the following:

### Deck thesis

One paragraph describing what the deck does, what it values, and how it wins.

### Role counts

Show both raw counts and overlap notes:

```text
Payoffs: 12
Plan enablers: 14
Enhancers: 7
Card advantage: 15
Card selection: 5
Removal: 15
Ramp: 17
Lands including MDFCs: 38
```

These numbers are examples from an intermediate Kuja snapshot and must be recalculated after every deck change.

### Card-by-card table

Every nonland card should have:

| Card | Mana value | Primary role | Secondary roles | Why included | Why not a stronger generic card? |
|---|---:|---|---|---|---|

### Land-by-land table

Every land should have:

| Land | Colors/types | Plan support | Tempo cost | Why this land earns its slot |
|---|---|---|---|---|

### Cuts

Rank cuts by replaceability, not by raw card strength. The first cuts should usually be cards that are narrow, redundant, conditional, off-plan, or poor at the intended curve.

### Future upgrade paths

Separate upgrades by philosophy:

- **More consistency:** better selection, more reliable colored sources, redundant enablers
- **More power:** stronger rituals, faster mana, more efficient tutors or engines
- **More theme:** additional Wizards, exact token makers, tribal support
- **More interaction:** flexible answers, protection, graveyard hate, stack interaction
- **Higher bracket:** cards intentionally excluded from the current experience

Every upgrade should name the gameplay change it causes, not merely say that the card is stronger.

## 10. Preserve decisions as first-class data

The most valuable output is not only the final list. It is the explanation of why the list is this list.

For each disputed card, record:

```yaml
card: "Example card"
mechanical_truth: "What Oracle text actually does"
owner_preference: "Why the builder likes or dislikes it"
goal_function_effect: "Which score factors it improves or harms"
bracket_effect: "How it changes the expected gameplay"
decision: "Keep / cut / test / reserve for upgrade"
replacement_logic: "What role a replacement must preserve"
```

This prevents future reviews from reverting to generic staple recommendations that conflict with the deck's intended identity.

## 11. Definition of success

A completed build passes when:

- The commander thesis is explicit.
- The construction direction—top-down, bottom-up, or hybrid—is justified.
- Oracle text and type lines have been checked for key cards.
- Every card, including every land, has a rationale.
- Role counts are verified and overlaps are explained.
- The mana base meets the declared land and color-source targets.
- The deck passes the opening-hand, commander-sequence, recovery, interaction, and bracket tests.
- Popular cards omitted from the deck have a stated reason.
- Cuts and future upgrades are ranked by the declared goal function.
- The final list can be exported in the requested Moxfield syntax.

The harness is complete only when the deck is explainable, testable, and faithful to the builder's desired experience—not merely when it contains 100 legal cards.
