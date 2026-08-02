# Preseason Poll — Requirements

**Status:** Mechanism approved. Question format pending mobile testing.
**Author:** Landry Ndahayo
**Date:** 2026-08-02
**Last revised:** 2026-08-02
**Season:** 2026 (season_4)

---

## 1. Summary

The preseason poll collects each of the 12 league managers' expectations before
week 1 and locks them as a permanent record. At season end, those locked
predictions are scored against actual results to answer two questions: who read
the league best, and who was most delusional about their own team.

This revision expands the original scope from eight simple-choice questions to
include ordered placement predictions, which changed the collection mechanism
materially.

**Approved 2026-08-02:** the poll is a custom form on the dashboard writing to
DynamoDB (Option B, Section 3). Google Forms is not used. Section 2 records why
that constraint drove the decision and is retained as rationale rather than an
open question.

The primary respondent device is a phone, and the heaviest task is ordering
three divisions of four managers each. **The interaction pattern for that task
is not yet decided and will be settled by building the candidates and testing
them on a real phone, not by argument.** See Section 3.4 and OD-7.

---

## 2. Why Google Forms was ruled out

Retained as rationale. The decision in Section 3 rests on this finding.

**Google Forms has no ranking or drag-and-drop question type. This is a hard
limitation, not a difficulty.**

Verified against the live Forms API v1 discovery document on 2026-08-02. The
complete set of question types is:

| Type | Usable for ordering? |
|---|---|
| `choiceQuestion` (radio, checkbox, dropdown) | No |
| `textQuestion` | No |
| `scaleQuestion` | No |
| `dateQuestion` / `timeQuestion` | No |
| `ratingQuestion` | No |
| `fileUploadQuestion` | No |
| `rowQuestion` (grid row) | Partially, see below |

A string search of every schema in the discovery document returns zero matches
for `rank`, `drag`, `reorder`, `ordering`, `sortable`, and `preference`. The
capability does not exist in the product, so no amount of API work produces it.

The closest native approximation is `questionGroupItem` with a `grid`: rows are
teams, columns are finishing positions, and the respondent selects one radio per
row. For a four-team division that is a 4x4 grid, or 16 radio buttons, which is
tolerable. For full league placement it is a 12x12 grid, or **144 radio
buttons**, which is unusable on a phone and is the primary way people will open
this.

Two further grid problems compound it. The API cannot enforce "limit one
response per column," so nothing stops a respondent from ranking three teams
2nd. And a grid collects a position per team rather than an ordering, so
contradictory ballots must be detected and discarded at aggregation time rather
than prevented at entry.

---

## 3. Collection mechanism — APPROVED

**Decision, 2026-08-02: Option B. Custom form on the dashboard, writing to
DynamoDB.**

The respondent never leaves the dashboard. One URL goes to the group chat, the
respondent picks their identity, answers, and submits. Submission POSTs to a new
route on the already-deployed API and persists to the existing
`fantasy-dashboard-data` table.

Options A and B are retained below as the record of what was weighed.

### 3.1 Google Forms submission was investigated and rejected

An intermediate design was considered: keep the custom form on the dashboard for
the interface, but have it submit *into* a Google Form so responses land in a
Google Sheet.

**This is not possible.** Verified against the live Forms v1 discovery document:
`forms.responses` exposes only `get` and `list`. **There is no `create`,
`insert`, or `batchCreate` method.** The API reads responses and builds forms;
it cannot write a response. Google does not permit injecting ballots into a
form's response set.

The known workaround is to POST directly to a form's undocumented
`/formResponse` endpoint using scraped `entry.<id>` field names. **Rejected.**
It is an internal endpoint with no compatibility guarantee, it fails silently
rather than erroring, and the failure would surface during the one week twelve
people are actually submitting. Not an acceptable dependency for the critical
path.

### 3.2 Google Sheets as a direct write target was also rejected

Writing straight to a Sheet via `sheets.spreadsheets.values.append` *is*
supported and would work. It was rejected for the submission path on two
grounds:

1. **It puts a live external dependency in the submit path.** The Lambda would
   hold a Google OAuth refresh token, which expires, can be revoked, and needs
   re-consent. If it lapses, **submissions fail** — during the exact window the
   poll is open. DynamoDB has no external dependency; the Lambda already holds
   an IAM policy for the table.
2. **The available scopes are too broad.** `values.append` requires `drive`,
   `drive.file`, or `spreadsheets`. Even the narrowest grants more than
   "append to this one sheet," which is disproportionate for a league poll.

### 3.3 Sheet export deferred, not cancelled

A Sheet remains useful as a private working view for the commissioner. It is
implemented as a **separate, manually-run export script reading from DynamoDB**,
never as part of the submit path. If the export breaks, it is re-run; no ballot
is ever at risk. It runs from the commissioner's machine with existing
credentials, so no Google token is deployed to a Lambda.

**Out of scope for v1** (Section 3.5). The commissioner's need to inspect
ballots is met in v1 by a CLI flag. The Sheet is added only if that proves
insufficient, since league-facing results are served by the results page rather
than a spreadsheet.

### 3.4 Open: the ordering interaction pattern

Mechanism is settled; **the interaction for ordering a division is not.** This
is the highest-usage, highest-risk interaction in the poll: three separate
four-manager orderings, on a phone, by respondents with no patience for a
fiddly interface.

Candidates, all viable now that the form is custom:

| Pattern | Taps to order one division | Notes |
|---|---|---|
| Drag to reorder | 1-3 drags | Most direct. Touch drag is the least reliable interaction on mobile and needs a touch-capable library; HTML5 native DnD does not fire touch events. |
| Up/down buttons per row | 1-6 taps | Large, unambiguous targets. No drag. Tedious for a full reversal. |
| Tap-in-order selection | Exactly 4 taps | Respondent taps managers 1st through 4th; list builds as they go. No dragging, no ambiguity, and progress is self-evident. |
| Single dropdown, 24 orderings | 1 tap | Every option is a complete valid ordering, so an invalid ballot is impossible. Native phone dropdown. Requires reading option strings rather than manipulating a list. |
| 4x4 grid | 4 taps | Familiar, but wide on a narrow screen and permits contradictory answers. |

A four-manager division has only **24 possible complete orderings**, which is
what makes the single-dropdown option viable at all. It does not generalize:
twelve managers have 479,001,600 permutations, so any full-league ordering
question needs a different pattern (see OD-8).

**This will be decided by testing, not discussion.** Section 10 sequences a
prototype of the leading candidates, deployed to a real URL, opened on an actual
phone, and judged on tap count and whether ordering three divisions feels like a
chore. Recorded as OD-7.

### 3.5 Version scope

Defined because "v1" was previously used without definition.

**v1 — collection.** Everything required for twelve managers to submit ballots
and for the commissioner to read them.

In scope: poll page at a single shareable URL; identity picker; the approved
question set; submit to DynamoDB; resubmit pre-loading prior answers; the
server-enforced lock; a CLI that prints every ballot.

Out of scope: Sheet export; public results page; end-of-season scoring;
`season_4` configuration in `seasons.yaml`.

Done when: a link posted to the group chat results in twelve ballots submitted
from phones, and the commissioner can read them.

**v2 — results page.** The league-facing aggregated view on the dashboard.
Published once at lock. Static thereafter by design: locked ballots do not
change, so a daily refresh would render identical numbers for four months.

**v3 — scoring.** Predictions against actual results. This is the component that
genuinely warrants a daily refresh, since accuracy shifts as real standings
move. Two leaderboards: accuracy of each manager's read on the league, and the
gap between self-prediction and actual finish.

Only the FR-21 schema commitment is in v1 scope, so v3 is a comparison rather
than a migration.

### Option A — Google Forms with grid questions

Keep the existing architecture. Replace the three division-winner dropdowns with
three 4x4 grids. Drop full league placement, or accept a 144-radio-button grid.

**Effort:** roughly 2 hours. The form-generation script already exists and needs
only new question builders.

**Pros:** ships today; zero new infrastructure; Google owns submission
reliability, spam handling, and mobile rendering.

**Cons:** full league placement is effectively unavailable, which is a stated
requirement; contradictory rankings are possible and must be discarded after the
fact; resubmitting still starts from a blank form because pre-filled links
cannot restore prior answers; the respondent leaves the dashboard.

### Option B — Custom form on the dashboard (APPROVED)

Build the poll as a dashboard page with real drag-to-reorder lists. Submissions
POST to a new API endpoint and persist to the existing DynamoDB table.

**Effort:** roughly 1 to 2 days across frontend, a new Lambda route, and the
aggregation rewrite.

**Pros:**
- Delivers ordered placement as specified, for both divisions and the full
  league, with an interface built for the purpose.
- Contradictory ballots become structurally impossible. A reorderable list has
  exactly one item per position by construction, so there is nothing to
  validate and nothing to discard.
- **Resubmitting can pre-load prior answers.** This is the single biggest
  respondent-experience gain and it is provably impossible in Google Forms.
  Someone changing one pick in week 1 no longer re-answers ten questions.
- The experience matches the flow already agreed: one link, pick your name,
  answer, done, never leaving the dashboard.
- Locking the poll becomes a server-side check rather than a Google setting.

**Cons:**
- Activates the API write path, which is currently dormant.
- We own submission reliability, input validation, and abuse handling.
- No Google Sheets fallback view of raw responses.
- Requires a `sam deploy`, which is a manual step outside the existing GitHub
  Actions workflow.

### Rationale for the approved decision

**Option B.** The determining factor is that Option A cannot satisfy the
requirement as stated, so choosing it means cutting full league placement rather
than building it. Given that the infrastructure already exists in dormant form,
that the resubmit experience improves substantially, and that invalid ballots
stop being possible rather than being cleaned up afterward, the additional day
of work is proportionate.

Three points reduce the apparent risk:

1. **DynamoDB, API Gateway, and the Lambda already exist and are deployed.** The
   table is on-demand billing, the API responds today, and CORS preflight is
   already handled in `dashboard_api/app.py`. This adds one route, not a stack.
2. **The dormant `VITE_USE_LAMBDA_API` flag does not need flipping.** That flag
   gates how existing pages source their data. A poll-specific service can call
   the endpoint directly, so the rest of the dashboard is untouched and the
   migration stays paused.
3. **Cost is immaterial.** Twelve managers submitting a handful of times each is
   a few hundred write units against on-demand pricing, which rounds to zero.

Everything below assumes Option B, which is now approved. Section 9 is retained
only as a record of the rejected fallback.

---

## 4. Data foundation

All question options derive from files already in the repository, so a team
rename is a data edit rather than a code change.

| Input | Source | Provides |
|---|---|---|
| Managers | `team_identity_mapping.csv` | roster_id, manager name, team name |
| Divisions | `pipeline/standings_data.json` | division names and membership |
| 2025 results | `pipeline/playoff_bracket.json` | playoff seeds 1-12 |

### 2025 reference data

Divisions (3 divisions, 4 teams each):

| Division | Managers |
|---|---|
| Chicago | Chris, Will, Tyler, Kyle |
| Wisconsin | Brevin, Don, Matt, Jake |
| American | Johnny, Landry, Grant, Zach |

2025 final seeding. Records are out of 28 because the league scores two results
per week, a head-to-head result plus a beat-the-median result, across a
14-week season.

| Seed | Manager | Record | Made playoffs | Note |
|---|---|---|---|---|
| 1 | Johnny | 22-6 | Yes | American winner |
| 2 | Brevin | 21-7 | Yes | Wisconsin winner |
| 3 | Chris | 11-17 | Yes | Chicago winner |
| 4 | Landry | 19-9 | Yes | Wild card |
| 5 | Don | 16-12 | Yes | Wild card |
| 6 | Grant | 16-12 | Yes | Wild card |
| 7 | Matt | 13-15 | No | |
| 8 | Jake | 12-16 | No | |
| 9 | Zach | 11-17 | No | |
| 10 | Will | 10-18 | No | |
| 11 | Tyler | 9-19 | No | |
| 12 | Kyle | 8-20 | No | |

**Data caveat requiring a decision.** Local data was captured 2026-12-16 at week
14 of 14 with the playoff bracket unresolved, so the regular season is complete
but **the 2025 champion and the 2025 toilet bowl loser are not recorded in this
repository.** Seeding is solid and every question below depends only on seeding.
If any question should reference the actual 2025 champion, that result must be
supplied or re-pulled first. See open decision OD-4.

One consequence of the auto-bid worth knowing, because it shapes how people will
answer Q7: Chris won the Chicago division at 11-17 and took the 3 seed, while
Matt missed the playoffs at 13-15. Chris is the structurally obvious answer to
"which playoff team misses this year."

---

## 5. Functional requirements

### Identity and access

**FR-1.** The poll is reachable from a single URL, identical for every
respondent, safe to paste into the group chat.

**FR-2.** On arrival the respondent selects their own identity from the 12
managers, displayed as manager name and team name. Selection is required before
any question is shown.

**FR-3.** The system does not collect email addresses and does not require any
account or sign-in.

**FR-4.** Identity is stored as `roster_id`, the stable key used throughout the
repository, rather than a display name that changes between seasons.

**FR-5.** Selected identity persists in browser local storage so a respondent
returning on the same device skips the picker. The choice remains changeable.

**FR-6 (accepted limitation).** A respondent can select an identity that is not
theirs. This is accepted rather than solved. Mitigations: every ballot is
published attributed, the commissioner can view all ballots individually, and
submissions are timestamped. Requiring sign-in was explicitly rejected.

### Submission and revision

**FR-7.** A respondent may submit more than once. Only the most recent
submission per `roster_id` counts.

**FR-8.** On return before the lock date, the form pre-loads the respondent's
previous answers so a single pick can be changed without re-answering
everything. *This requirement is unachievable under Option A.*

**FR-9.** Every submission is persisted with a server-assigned UTC timestamp.
Superseded submissions are retained rather than overwritten, giving a full
revision history.

**FR-10.** After the lock date the poll rejects new submissions server-side and
displays a read-only state. Client-side enforcement alone is insufficient.

**FR-11.** All ordering questions are complete by construction, so partial or
contradictory orderings cannot be submitted.

### Questions

**FR-12.** The poll consists of the questions specified in Section 6, in that
order.

**FR-13.** Every question option set is generated from the data sources in
Section 4. No option list is hardcoded.

**FR-14.** Manager-selection questions display manager name as the primary label
because respondents recognize managers more reliably than team names, which
change between and during seasons. Team name is displayed as secondary context.

**FR-15.** Questions restricted to a subset of the league, Q7 through Q9,
derive that subset from 2025 seeding rather than a maintained list.

### Storage and aggregation

**FR-16.** Ballots persist to the existing `fantasy-dashboard-data` table using
the established `PK`/`SK` pattern, with no new table.

**FR-17.** Aggregation produces `api-preseason-poll.json` in
`dashboard/frontend/public/`, matching the existing `api-*.json` convention.

**FR-18.** Aggregation is idempotent and re-runnable at any time.

**FR-19.** Every published tally carries its denominator. A count without the
number of ballots it came from is not published.

**FR-20.** Ordering questions are aggregated by average predicted position,
reported alongside the count of ballots contributing to it.

### Scoring, end of season

**FR-21.** The stored ballot shape supports end-of-season scoring without
migration. Scoring itself is out of scope for this phase; the schema commitment
is not.

**FR-22.** Two scored outcomes are the eventual deliverable: accuracy of each
manager's read on the league, and the gap between each manager's self-prediction
and their actual finish.

---

## 6. Question specification

| # | Question | Type | Options | Required |
|---|---|---|---|---|
| Q1 | Who are you? | Identity picker | 12 managers | Yes |
| Q2 | Order the Chicago division, 1st to 4th | Ordering, pattern per OD-7 | Chris, Will, Tyler, Kyle | Yes |
| Q3 | Order the Wisconsin division, 1st to 4th | Ordering, pattern per OD-7 | Brevin, Don, Matt, Jake | Yes |
| Q4 | Order the American division, 1st to 4th | Ordering, pattern per OD-7 | Johnny, Landry, Grant, Zach | Yes |
| Q5 | Order the entire league, 1st to 12th | **Not asked.** Derived per OD-8 | All 12 | n/a |
| Q6 | Who are the four real contenders? | Multi-select, exactly 4 | All 12 | Yes |
| Q7 | Who wins the league? | Single select | All 12 | Yes |
| Q8 | Who takes the loser punishment? | Single select | All 12 | Yes |
| Q9 | Which team goes first to worst? | Single select | 2025 seeds 1-4 | Yes |
| Q10 | Which team goes worst to first? | Single select | 2025 seeds 9-12 | Yes |
| Q11 | Which 2025 playoff team misses this year? | Single select | 2025 seeds 1-6 | Yes |
| Q12 | Which 2025 non-playoff team makes it? | Single select | 2025 seeds 7-12 | Yes |
| Q13 | One bold prediction | Free text | — | No |

### Notes on specific questions

**Q2 through Q4, division ordering.** The interaction pattern is open (OD-7),
but two things are fixed regardless of which pattern wins. Whatever is submitted
has exactly one manager per position by construction, so invalid orderings are
unreachable rather than filtered later. And where the pattern involves a
pre-populated starting order, that default is **2025 division finish**, so the
respondent expresses change from last season rather than building from a blank
list. A useful side effect: an unedited ballot is detectable, since it exactly
matches last year.

**Q5, full league ordering, is no longer asked.** Twelve managers have
479,001,600 possible orderings, so no single-question pattern captures it, and a
twelve-item ordering exercise on a phone is precisely the fatigue NFR-2 exists to
prevent. It is derived instead: the three division orderings from Q2 through Q4
already rank all twelve managers, and Q6 through Q8 supply the cross-division
tiebreak. Deriving it also eliminates the inconsistency problem that an
independent Q5 would have created, where a respondent could rank Chris first in
Chicago and then place him below Will league-wide. See OD-8, which supersedes
OD-2.

**Q6, contenders.** Exactly four, enforced at entry. The submit action stays
disabled until precisely four are selected, which is the requirement that
Google Forms cannot express. This removes the ballot-weighting logic built in
commit `abc1a3b`, since every ballot now carries four picks by construction.

**Q9 and Q10, first to worst and worst to first.** Q9 offers 2025 seeds 1
through 4, being Johnny, Brevin, Chris, and Landry. Q10 offers seeds 9 through
12, being Zach, Will, Tyler, and Kyle. Cutoff at four is a proposal, not a
derived constant. See OD-3.

**Q11 and Q12 overlap with Q9 and Q10.** This is worth naming explicitly. Q10,
"worst to first," and Q12, "non-playoff team that makes it," ask nearly the same
thing at different thresholds: Q10 asks for a dramatic rise, Q12 asks for any
rise past sixth. Q9 and Q11 pair the same way. Four questions covering two
relationships risks respondent fatigue on a form already carrying five ordering
exercises. Recommendation is to keep Q11 and Q12, which are crisply verifiable
against final standings, and cut Q9 and Q10. See OD-1.

---

## 7. Non-functional requirements

**NFR-1.** Mobile is the primary target, not a supported secondary. The full
flow is usable one-handed on a phone, in portrait, without zooming. Any pattern
that only works well with a mouse is disqualified regardless of how it reads on
a desktop.

**NFR-2.** The ordering interaction is selected by testing candidates on a real
phone rather than by reasoning about them (OD-7). Selection criteria, in
priority order:

1. **No ambiguity about current state.** The respondent can tell at a glance
   what order they have selected.
2. **No invalid state reachable.** Whatever the interaction, a submitted
   ordering has exactly one manager per position by construction.
3. **Tap or gesture count** to order one four-manager division.
4. **Reliability under real conditions:** a moving thumb, a scrolling page, a
   mid-sized phone.
5. **Fatigue across repetition.** The pattern is used three times in a row. A
   pattern that is pleasant once and tiresome by the third division fails.

**NFR-2a.** If drag is selected, it must be touch-capable, since HTML5 native
drag-and-drop does not fire touch events, and it must be paired with per-row
up/down controls. Dragging an item across a list taller than the viewport
requires drag-while-scrolling, which is unreliable on touch; the buttons are the
dependable fallback and match the original "drag up or down" description.

**NFR-3.** Time to complete is under four minutes for a respondent who knows
their answers. Ordering all three divisions accounts for no more than half of
that.

**NFR-4.** Answers survive accidental navigation away before submit, via local
draft state.

**NFR-5.** Submission failure surfaces a clear retry rather than silently
losing a ballot.

**NFR-6.** Incremental running cost stays effectively zero.

---

## 8. Open decisions

| ID | Decision | Options | Recommendation |
|---|---|---|---|
| OD-1 | Keep all four transition questions, Q9 through Q12? | All four / cut Q9+Q10 / cut Q11+Q12 | Cut Q9 and Q10. Q11 and Q12 are cleanly verifiable and cover the same ground. |
| ~~OD-2~~ | ~~Reconcile Q5 against Q2 through Q4?~~ | Superseded by OD-8 | Moot. Deriving league order from the division answers makes the two structurally incapable of disagreeing. |
| OD-3 | Candidate pool size for Q9 and Q10 if retained | Top and bottom 3 / 4 / 6 | Four, if retained at all. |
| OD-4 | Does any question need the actual 2025 champion? | Yes, re-pull / no, seeding suffices | No. Every question above depends only on seeding. |
| OD-5 | Lock date | Week 1 kickoff / before rookie draft / other | Week 1 kickoff. Latest point that still precedes real information. |
| OD-6 | Publish results before the lock, or only after? | Live / after lock | After lock. Live results let late respondents anchor on the consensus. |
| OD-7 | Ordering interaction pattern | Drag / up-down buttons / tap-in-order / 24-option dropdown / grid | **Decide by phone testing, not discussion.** Prototype the leading candidates and open them on a real device. |
| OD-8 | Full 12-team league ordering | Derive from division answers / ask top 3 + bottom 3 / drop | Derive it. The three division orderings already rank all twelve, so no extra question is needed and the result cannot contradict their division picks. |

### Closed decisions

| ID | Decision | Resolution | Date |
|---|---|---|---|
| OD-M1 | Collection mechanism | Custom dashboard form writing to DynamoDB (Option B) | 2026-08-02 |
| OD-M2 | Submit into a Google Form so responses land in a Sheet | Not possible. `forms.responses` has no create method; the `/formResponse` workaround was rejected as an unguaranteed internal endpoint on the critical path. | 2026-08-02 |
| OD-M3 | Write directly to a Google Sheet | Rejected. Puts an expiring OAuth token in the submit path and requires disproportionately broad Drive scopes. | 2026-08-02 |
| OD-M4 | Sheet as commissioner working view | Deferred past v1. Manual export script reading from DynamoDB, never in the submit path. v1 inspection is served by a CLI flag. | 2026-08-02 |

---

## 9. What Option A would have meant

**Not applicable.** Option B was approved 2026-08-02. Retained as the record of
the rejected fallback.

- Q5, full league placement, is cut. A 12x12 grid is not viable on mobile.
- Q2 through Q4 become 4x4 grids; contradictory ballots become possible and
  must be discarded during aggregation, with the discard count published.
- FR-8, pre-loading prior answers, is dropped as unachievable.
- Q6's exactly-four rule reverts to a request in the question title, and the
  ballot-weighting logic from `abc1a3b` is retained.
- FR-10, the server-side lock, becomes a `setPublishSettings` call.
- Effort drops from days to hours.

---

## 10. Sequencing

### Immediate next step: ordering prototype (OD-7)

Mechanism is approved, so the one thing blocking the build is the ordering
interaction. Resolving it by testing costs a few hours and de-risks the most
used interaction in the poll.

1. Build the leading candidates as a throwaway prototype page: one real
   division, four real managers, no submit path.
2. Deploy to a real URL. Testing mobile interaction in a desktop browser's
   responsive mode is not a substitute; touch behaviour differs.
3. Open on an actual phone and order all three divisions with each pattern.
4. Judge against the NFR-2 criteria. Pick one. Record in OD-7.
5. Discard the prototype.

### Then, v1

6. Identity picker page and route.
7. Ballot schema, `POST /api/poll` and `GET /api/poll/{roster_id}` on the
   existing Lambda, then `sam deploy`.
8. Poll page using the pattern selected in step 4, with draft persistence and
   prior-answer pre-loading.
9. CLI to read all ballots.
10. Lock enforcement, per OD-5.

### Then, v2 and v3

11. Aggregation rewrite for the approved question set.
12. Results page, published at lock, per OD-6.
13. `season_4` in `pipeline/config/seasons.yaml`, currently absent.
14. Scoring against final standings. December.

Optional, any time after v1: Sheet export script (OD-M4).

---

## 11. Approval

| Item | Approver | Status | Date |
|---|---|---|---|
| Collection mechanism, Section 3 | Landry | **Approved** | 2026-08-02 |
| Version scope, Section 3.5 | Landry | **Approved** | 2026-08-02 |
| Ordering interaction, OD-7 | Landry | Pending phone testing | |
| Question set, Section 6 | Landry | Pending | |
| Open decisions OD-1 through OD-6, OD-8 | Landry | Pending | |
