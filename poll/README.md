# Preseason Poll

Our version of the NFLPA Top 100: the league votes on the league before the
season starts, and the results get published on the dashboard with every pick
attributed by name.

Google Forms handles collection. These scripts handle everything either side of
it, so no question or dropdown is ever built by hand.

## How identity works without collecting email

The form's first question is a required 12-option dropdown of the league's
managers. That dropdown **is** the identity. Each manager gets a personal
pre-filled link that arrives with their own name already selected, so in
practice they never touch it.

This was chosen over the alternatives deliberately:

| Approach | Why not |
|---|---|
| Collect email addresses | Explicitly not wanted, and it forces a Google sign-in |
| Require sign-in | Same sign-in friction, and it fails for anyone without a Google account |
| Rely on Forms cookies | Cookies do not survive a different device or a cleared browser |

The tradeoff is honest: someone **can** submit as another manager by changing
the dropdown. In a 12-person league where every ballot is published next to a
name, that is socially self-policing, and `--show-ballots` makes it visible.

## Changing your picks

Resubmit. `fetch_responses.py` keeps only the most recent submission per
manager, by `lastSubmittedTime`, and reports how many were superseded.

One thing to be clear about with the league: **a pre-filled link does not
restore previous answers.** Resubmitting starts from a blank form, so every
question has to be answered again. The form description says so.

## Setup (one time)

The Forms API must be enabled on the Cloud project that owns
`../credentials.json` (project `gmail-api-cleaner`):

```
https://console.cloud.google.com/apis/library/forms.googleapis.com?project=gmail-api-cleaner
```

The existing `token.pickle` next to those credentials is Gmail-scoped and is
not touched. These scripts write their own `poll/token.json` with
`forms.body` and `forms.responses.readonly`.

```bash
python3 -m venv poll/.venv
poll/.venv/bin/pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Usage

```bash
# Preview the form structure. No API call, no auth.
poll/.venv/bin/python poll/create_form.py --dry-run

# Create it. Opens a browser once for consent.
poll/.venv/bin/python poll/create_form.py

# Pull responses and publish results. Re-run whenever picks come in.
poll/.venv/bin/python poll/fetch_responses.py
poll/.venv/bin/python poll/fetch_responses.py --show-ballots   # see who picked what
poll/.venv/bin/python poll/fetch_responses.py --dry-run        # tally without writing

# Verify the aggregation logic offline, no network needed.
poll/.venv/bin/python poll/test_aggregate.py
```

`create_form.py` refuses to run twice without `--force`, since a second form
would orphan the responses already collected against the first form id.

## The questions

Generated from `../team_identity_mapping.csv` and the real division structure in
`../pipeline/standings_data.json`, so a team rename is a CSV edit rather than
twelve dropdown edits.

1. **Who are you?** — required, pre-filled
2. **Where do you finish?** — 1st through 12th
3. **How would you describe your own team?** — title favorite through full teardown
4. **Who are the real contenders?** — checkbox, pick 4
5. **Who wins the league?**
6. **Who wins the Chicago / Wisconsin / American division?** — three questions,
   each limited to that division's four teams so an impossible ballot cannot be cast
7. **Who goes to the toilet bowl?**
8. **One bold prediction** — optional free text

## Contender weighting

Forms API v1 has no response validation for choice questions, so "pick exactly
4" cannot be enforced server-side; it is a request in the question title.
Aggregation therefore scales each ballot to the 4-pick target: a voter who
checks eight teams contributes 0.5 per pick, one who checks four contributes
1.0. Every ballot carries identical total weight.

Both numbers are published. `contenders.weighted` is the fair comparison;
`contenders.raw_mentions` is the unadjusted count.

## Files

| File | Tracked | Notes |
|---|---|---|
| `poll_common.py` | yes | auth, league loading, question keys |
| `create_form.py` | yes | builds the form |
| `fetch_responses.py` | yes | dedupe, aggregate, publish |
| `test_aggregate.py` | yes | offline logic checks |
| `form_metadata.json` | yes | form id, URLs, questionId map — no secrets, and `fetch_responses.py` needs it |
| `token.json` | **no** | live OAuth refresh token |
| `prefill_links.csv` | **no** | personal links, one per manager |
| `responses_raw.json` | **no** | raw ballots |

Output goes to `dashboard/frontend/public/api-preseason-poll.json`, matching the
`api-*.json` convention the frontend already reads.

## Two settings the API cannot set

After creating the form, in the form editor under Settings → Responses:

1. Confirm **Collect email addresses** is Off.
2. Optionally turn on **Allow response editing** (the latest-wins dedupe handles
   resubmits either way).
