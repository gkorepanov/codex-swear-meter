---
name: codex-swear-meter
description: Audit local Codex conversation logs for user frustration, swearing, expletives, swear-adjacent phrases, positive satisfaction/courtesy signals, tone spikes, and model-timeline charts. Use when the user asks to analyze Codex logs/history for swear rate, frustration rate, satisfaction rate, gratitude/approval terms, dissatisfaction signals, negative turns, per-week timeline charts, dominant model color mapping, or a shareable/open-source Codex log tone audit.
---

# Codex Swear Meter

## Purpose

Generate a local, privacy-preserving chart of how often direct user messages in Codex logs contain explicit swears or swear-adjacent frustration, plus a visible positive index for gratitude/approval/satisfaction/courtesy signals. Adapt the lexicons to the current user's language instead of assuming one person's habits generalize. The chart title should personalize to the local account name by default, or use `--owner-name` when the user gives a preferred display name.

## Experience Contract

When a user kicks off this skill, the finished experience should be a personalized version of the same Codex Swear Meter chart:

- same chart structure: title, subtitle, logo, weekly message bars, swear-index line, positive-index line, dominant-model legend, and observed swear-index top terms
- personalized title from the local account name or the user's preferred name
- model colors and counts generated from that user's current Codex metadata
- top terms generated from that user's current counted matches, not copied from examples
- lexicon adapted from that user's own direct messages before the result is treated as final

The bundled lexicons are only a starting point. A serious skill run should inspect the user's extracted corpus, tune copied lexicons to high-precision direct frustration semantics, rerun the audit, and hand back the final HTML path plus a compact summary of what changed.

## Workflow

1. Choose a project/output folder. For open-source or repeatable work, create a dedicated project folder instead of writing into `$HOME`.
2. Copy the bundled lexicons before tuning them:
   - `assets/negative_terms.json`
   - `assets/swear_index_terms.json`
   - `assets/positive_terms.json`
3. Run the bundled script for a first pass:

```bash
python3 ~/.codex/skills/codex-swear-meter/scripts/codex_swear_meter.py audit --codex-home ~/.codex --lexicon <project>/config/negative_terms.json --spice-lexicon <project>/config/swear_index_terms.json --positive-lexicon <project>/config/positive_terms.json --out-dir <project>/outputs
```

If the user only wants a quick first pass, omit `--lexicon`, `--spice-lexicon`, and `--positive-lexicon`; the script will use the skill defaults.

If the local account name is not a good display name, add `--owner-name "Name"` to make the title `Name's Codex Swear Meter`. Pass an empty owner name only when the user wants the generic `Codex Swear Meter` title.

4. Before reusing an older chart, check freshness:

```bash
python3 ~/.codex/skills/codex-swear-meter/scripts/codex_swear_meter.py incremental --out-dir <project>/outputs
```

This compares `<project>/outputs/user_messages.jsonl` with the current raw logs, writes `<project>/outputs/incremental/new_user_messages.jsonl`, and analyzes only the new messages in `<project>/outputs/incremental/`. If `incremental_status.json` says `needs_refresh: true`, run `audit` again after reviewing the delta.

5. Inspect the first pass:
   - `outputs/spice_term_counts.csv`: actual counted terms
   - `outputs/spice_messages.csv`: matched snippets for review
   - `outputs/positive_term_counts.csv`: actual positive gratitude/approval terms
   - `outputs/positive_messages.csv`: matched positive snippets for review
   - `outputs/candidate_phrases.csv`: phrase candidates from the user's own messages
   - `outputs/model_timeline_weekly.csv`: dominant model by week
6. Tune the copied swear-index and positive lexicons to the user:
   - Add phrase-level terms that clearly express their own frustration style.
   - Keep literal swears and swear-adjacent phrases in the chart metric.
   - Avoid broad technical words such as `bug`, `issue`, `problem`, `error`, `wrong`, or `failed` unless paired with a stronger emotional phrase.
   - Prefer narrow phrases such as `what the hell`, `this is awful`, `this sucks`, `come on`, `wasting my time`, `this is a mess`, or `made it worse` over generic single-word negativity.
   - Treat reset/operation phrases such as `start again`, `delete this`, `redo`, and `try again` as review leads, not chart-metric terms, unless the same message also contains a stronger frustration phrase.
   - Keep positive courtesy (`please`, `пожалуйста`) separate from stronger approval (`круто`, `отлично`, `заебись`, `все работает`) when summarizing satisfaction.
   - Avoid broad positive words such as bare `работает`, `именно`, `right`, `fixed`, `done`, or `правильно` when they often appear in neutral instructions, quoted specs, or negative phrases like `не работает`; prefer phrase-level positive terms such as `все работает`, `спасибо, работает`, `работает супер`, `круто`, or `отлично`.
   - A trailing `*` in a term is a Unicode word-stem match, useful for Russian morphology such as `бля*`, `кончен*`, or `охуен*`.
7. Re-run the audit after tuning and use that rerun for the final chart.
8. Open `outputs/spice-timeline.html` and visually verify desktop and mobile:
   - no label overlap
   - no horizontal overflow
   - title/subtitle fit
   - dominant-model legend maps colors to names and total message counts
   - top terms are data-backed from the user's own counted terms
   - positive-index line renders and the mobile x-axis labels do not overlap
9. Final response should include the HTML path, the total direct-user-message count, the swear-index count and percentage, the positive count and percentage, the latest included timestamp, and what was tuned. Do not expose raw snippets unless the user asks.

## Corpus Reading And Subagents

Use subagents as corpus readers when the corpus is large, the user's slang is unfamiliar, candidate phrases are noisy, or the user asks for a high-confidence reusable tuning pass and explicitly permits subagent work.

Do not enable `--include-subagents` for this. That flag changes the analyzed corpus by including spawned agent prompts; leave it off unless the user explicitly wants subagent prompts counted.

Recommended split:

- Precision reader: review `spice_messages.csv` and `spice_term_counts.csv`; identify false-positive terms and whether each should be included, narrowed, excluded from the chart metric, or left as a review lead.
- Recall reader: review `user_messages.jsonl` and `candidate_phrases.csv`; propose missed phrase-level frustration terms with evidence and false-positive risk.
- Skill/chart QA reader: review `SKILL.md`, `references/adaptation.md`, and the generated HTML; check that examples, model legends, and labels are data-backed and understandable to a new user.

The coordinator should merge only terms with current-corpus evidence and should keep a short include/narrow/exclude decision ledger in the project notes or README when preparing an open-source artifact.

## Interpretation Rules

- Treat matches as review leads, not a psychological diagnosis.
- The main chart should use `swear_index_message_rate`: the percentage of extracted direct user messages that contain at least one explicit swear or included narrow frustration phrase.
- The right-rail `% Swear` column should use the same swear-index definition,
  but scoped to each displayed model family in the visible chart window:
  model-family swear-index messages divided by model-family direct user
  messages. Do not calculate it as model usage share.
- Model labels come from Codex's local session/thread metadata. If a recent
  message appears under an older model family, inspect `user_messages.jsonl`
  by `source_path`, `title`, and `model_label`; do not assume it is a subagent
  unless `is_subagent` is true.
- The shareable chart should only name public GPT model families. Fold
  unrecognized or private model labels into `Other`; do not expose internal
  model codenames in screenshots, README examples, or generated HTML.
- Keep broader dissatisfaction outputs in CSVs for review, but do not quietly mix them into the visible swear meter.
- The visible chart should include a separate positive-index line. Use `positive_index_message_rate`, currently equivalent to positive matched messages divided by all direct user messages. Keep it visually and semantically separate from the swear-index line.
- Keep positive satisfaction/courtesy outputs in separate positive CSVs; do not mix them into the visible swear meter line.
- Use `swear_index_excluded_terms` in the spice lexicon for ambiguous terms that should still appear in review outputs but should not count in the chart by themselves.
- If the dominant model list has `unknown`, explain that the session logs were readable but `state_5.sqlite` lacked model metadata for those threads.
- Do not publish raw logs, message snippets, or CSVs unless the user explicitly asks. Screenshots may still reveal private usage patterns; ask before sharing.

## Adaptation Reference

Read `references/adaptation.md` when tuning the lexicon for a new user, deciding what examples to show, or preparing an open-source-friendly explanation.
