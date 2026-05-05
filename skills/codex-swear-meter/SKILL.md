---
name: codex-swear-meter
description: Audit local Codex conversation logs for user frustration, swearing, expletives, swear-adjacent phrases, tone spikes, and model-timeline charts. Use when the user asks to analyze Codex logs/history for swear rate, frustration rate, dissatisfaction signals, negative turns, per-week timeline charts, dominant model color mapping, or a shareable/open-source Codex log tone audit.
---

# Codex Swear Meter

## Purpose

Generate a local, privacy-preserving chart of how often direct user messages in Codex logs contain explicit swears or swear-adjacent frustration. Adapt the lexicon to the current user's language instead of assuming one person's habits generalize. The chart title should personalize to the local account name by default, or use `--owner-name` when the user gives a preferred display name.

## Workflow

1. Choose a project/output folder. For open-source or repeatable work, create a dedicated project folder instead of writing into `$HOME`.
2. Copy the bundled lexicons before tuning them:
   - `assets/negative_terms.json`
   - `assets/swear_index_terms.json`
3. Run the bundled script:

```bash
python3 ~/.codex/skills/codex-swear-meter/scripts/codex_swear_meter.py audit --codex-home ~/.codex --lexicon <project>/config/negative_terms.json --spice-lexicon <project>/config/swear_index_terms.json --out-dir <project>/outputs
```

If the user only wants a quick first pass, omit `--lexicon` and `--spice-lexicon`; the script will use the skill defaults.

If the local account name is not a good display name, add `--owner-name "Name"` to make the title `Name's Codex Swear Meter`. Pass an empty owner name only when the user wants the generic `Codex Swear Meter` title.

4. Inspect the first pass:
   - `outputs/spice_term_counts.csv`: actual counted terms
   - `outputs/spice_messages.csv`: matched snippets for review
   - `outputs/candidate_phrases.csv`: phrase candidates from the user's own messages
   - `outputs/model_timeline_weekly.csv`: dominant model by week
5. Tune the copied swear-index lexicon to the user:
   - Add phrase-level terms that clearly express their own frustration style.
   - Keep literal swears and swear-adjacent phrases in the chart metric.
   - Avoid broad technical words such as `bug`, `issue`, `problem`, `error`, `wrong`, or `failed` unless paired with a stronger emotional phrase.
   - Prefer narrow phrases such as `what the hell`, `this is awful`, `this sucks`, `come on`, `wasting my time`, `this is a mess`, or `made it worse` over generic single-word negativity.
   - Treat reset/operation phrases such as `start again`, `delete this`, `redo`, and `try again` as review leads, not chart-metric terms, unless the same message also contains a stronger frustration phrase.
6. Re-run the audit after tuning.
7. Open `outputs/spice-timeline.html` and visually verify desktop and mobile:
   - no label overlap
   - no horizontal overflow
   - title/subtitle fit
   - dominant-model legend maps colors to names
   - top terms are data-backed from the user's own counted terms

## Corpus Reading And Subagents

Use subagents as corpus readers when the corpus is large, the user's slang is unfamiliar, candidate phrases are noisy, or the user asks for a high-confidence reusable tuning pass.

Do not enable `--include-subagents` for this. That flag changes the analyzed corpus by including spawned agent prompts; leave it off unless the user explicitly wants subagent prompts counted.

Recommended split:

- Precision reader: review `spice_messages.csv` and `spice_term_counts.csv`; identify false-positive terms and whether each should be included, narrowed, excluded from the chart metric, or left as a review lead.
- Recall reader: review `user_messages.jsonl` and `candidate_phrases.csv`; propose missed phrase-level frustration terms with evidence and false-positive risk.
- Skill/chart QA reader: review `SKILL.md`, `references/adaptation.md`, and the generated HTML; check that examples, model legends, and labels are data-backed and understandable to a new user.

The coordinator should merge only terms with current-corpus evidence and should keep a short include/narrow/exclude decision ledger in the project notes or README when preparing an open-source artifact.

## Interpretation Rules

- Treat matches as review leads, not a psychological diagnosis.
- The main chart should use `swear_index_message_rate`: the percentage of extracted direct user messages that contain at least one explicit swear or included narrow frustration phrase.
- Keep broader dissatisfaction outputs in CSVs for review, but do not quietly mix them into the visible swear meter.
- Use `swear_index_excluded_terms` in the spice lexicon for ambiguous terms that should still appear in review outputs but should not count in the chart by themselves.
- If the dominant model list has `unknown`, explain that the session logs were readable but `state_5.sqlite` lacked model metadata for those threads.
- Do not publish raw logs, message snippets, or CSVs unless the user explicitly asks. Screenshots may still reveal private usage patterns; ask before sharing.

## Adaptation Reference

Read `references/adaptation.md` when tuning the lexicon for a new user, deciding what examples to show, or preparing an open-source-friendly explanation.
