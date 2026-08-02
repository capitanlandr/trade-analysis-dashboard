# Preseason Poll — Requirements

**Status:** Draft, pending approval
**Author:** Landry Ndahayo
**Date:** 2026-08-02
**Season:** 2026 (season_4)

---

## 1. Summary

The preseason poll collects each of the 12 league managers' expectations before
week 1 and locks them as a permanent record. At season end, those locked
predictions are scored against actual results to answer two questions: who read
the league best, and who was most delusional about their own team.

This revision expands the original scope from eight simple-choice questions to
include ordered placement predictions (division finish and full league finish),
which changes the collection mechanism materially. The change is not
incremental. It requires a decision documented in Section 3 before any
implementation begins.

---

## 2. The blocking constraint

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

## 3. Decision required: collection mechanism

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

### Option B — Custom form on the dashboard (recommended)

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

### Recommendation

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

Everything below assumes Option B. Section 9 records what changes under Option A.

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
| Q2 | Order the Chicago division, 1st to 4th | Reorder | Chris, Will, Tyler, Kyle | Yes |
| Q3 | Order the Wisconsin division, 1st to 4th | Reorder | Brevin, Don, Matt, Jake | Yes |
| Q4 | Order the American division, 1st to 4th | Reorder | Johnny, Landry, Grant, Zach | Yes |
| Q5 | Order the entire league, 1st to 12th | Reorder | All 12 | Yes |
| Q6 | Who are the four real contenders? | Multi-select, exactly 4 | All 12 | Yes |
| Q7 | Who wins the league? | Single select | All 12 | Yes |
| Q8 | Who takes the loser punishment? | Single select | All 12 | Yes |
| Q9 | Which team goes first to worst? | Single select | 2025 seeds 1-4 | Yes |
| Q10 | Which team goes worst to first? | Single select | 2025 seeds 9-12 | Yes |
| Q11 | Which 2025 playoff team misses this year? | Single select | 2025 seeds 1-6 | Yes |
| Q12 | Which 2025 non-playoff team makes it? | Single select | 2025 seeds 7-12 | Yes |
| Q13 | One bold prediction | Free text | — | No |

### Notes on specific questions

**Q2 through Q5, ordering.** Each renders as a reorderable list, pre-populated
in a neutral default order. Default order should be 2025 finish, so the
respondent expresses change from last season rather than building from nothing,
which also makes an unedited ballot detectable.

**Q5 relationship to Q2 through Q4.** Full league placement and division
placement can disagree: someone may rank Chris first in Chicago in Q2 and place
him below Will in Q5. Resolution options are to auto-sync them, to warn, or to
allow the inconsistency. See OD-2.

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

**NFR-1.** The full flow is usable one-handed on a phone. Reordering must work
by touch. HTML5 native drag-and-drop does not fire touch events, so a
touch-capable library is required.

**NFR-2.** Every reorderable list also offers explicit up and down controls per
row. Dragging item 12 to position 1 on a screen showing six items requires
drag-while-scrolling, which is unreliable on mobile. Buttons are the dependable
path and match the original description of dragging up or down.

**NFR-3.** Time to complete is under four minutes for a respondent who knows
their answers.

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
| OD-2 | Reconcile Q5 against Q2 through Q4? | Auto-sync / warn only / allow | Warn only. Auto-sync fights the respondent; silent inconsistency corrupts scoring. |
| OD-3 | Candidate pool size for Q9 and Q10 if retained | Top and bottom 3 / 4 / 6 | Four, if retained at all. |
| OD-4 | Does any question need the actual 2025 champion? | Yes, re-pull / no, seeding suffices | No. Every question above depends only on seeding. |
| OD-5 | Lock date | Week 1 kickoff / before rookie draft / other | Week 1 kickoff. Latest point that still precedes real information. |
| OD-6 | Publish results before the lock, or only after? | Live / after lock | After lock. Live results let late respondents anchor on the consensus. |

---

## 9. What changes under Option A

Recorded so the fallback is a known quantity rather than a re-design.

- Q5, full league placement, is cut. A 12x12 grid is not viable on mobile.
- Q2 through Q4 become 4x4 grids; contradictory ballots become possible and
  must be discarded during aggregation, with the discard count published.
- FR-8, pre-loading prior answers, is dropped as unachievable.
- Q6's exactly-four rule reverts to a request in the question title, and the
  ballot-weighting logic from `abc1a3b` is retained.
- FR-10, the server-side lock, becomes a `setPublishSettings` call.
- Effort drops from days to hours.

---

## 10. Sequencing, on approval

1. Confirm Option A or B, and close OD-1 through OD-6.
2. Build the identity picker page and route. Shared by either option.
3. Option B only: `POST /api/poll` route, ballot schema, `sam deploy`.
4. Option B only: poll page with touch reordering and draft persistence.
5. Rewrite aggregation for the revised question set.
6. Results page, gated on OD-6.
7. Configure season_4 in `pipeline/config/seasons.yaml`, currently absent.
8. Lock script, scheduled per OD-5.

Scoring against final results is deliberately excluded from this phase. Only
the schema commitment in FR-21 is in scope now.

---

## 11. Approval

| Item | Approver | Status |
|---|---|---|
| Collection mechanism, Section 3 | Landry | Pending |
| Question set, Section 6 | Landry | Pending |
| Open decisions, Section 8 | Landry | Pending |
