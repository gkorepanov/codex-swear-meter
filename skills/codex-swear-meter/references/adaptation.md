# Adaptation Guide

## Goal

Build a user-specific swear meter from that user's own Codex logs. Do not copy another user's exact language unless it actually appears in the new corpus.

## What To Count

Count a message when it contains at least one explicit swear or a narrow swear-adjacent frustration phrase. Good chart-metric families:

- direct profanity: `fuck`, `fucking`, `shit`, `bullshit`, `wtf`, `ffs`
- Russian profanity/stems: `бля*`, `заеб*`, `пиздец`, `кончен*`, `идиот*`, `тупой`
- softened expletives: `what the hell`, `for god's sake`, `damn`, `crap`
- hot challenge phrases: `come on`, `are you kidding me`, `what are you doing`
- clear output rejection: `this is awful`, `not good enough`, `this is ridiculous`
- rework/frustration cost: `wasting my time`, `this is a mess`, `made it worse`
- escalation/boundary phrases: `unacceptable`, `delete this shit`, `kill it and start again`

Keep normal debugging terms out of the swear index. `bug`, `issue`, `problem`, `error`, `failed`, `wrong`, and `broken` are too broad for the visible chart unless the surrounding phrase is clearly emotional.

The lexicon supports a trailing `*` as a Unicode word-stem match. Use it for
Russian morphology and slang variants, for example `бля*`, `кончен*`,
`заеб*`, or `охуен*`. Prefer the shortest stem that stays precise; do not add a
stem if it catches ordinary words.

## Positive Analytics

Positive analytics are separate from the visible swear chart. Count direct
gratitude, politeness, approval, and satisfaction markers, such as `thanks`,
`please`, `спасибо`, `пожалуйста`, `круто`, `отлично`, `заебись`,
`все работает`, `работает супер`, or `то что надо`.

Treat `please` and `пожалуйста` as courtesy, not proof of satisfaction. When
summarizing whether the user was happy, distinguish stronger approval/satisfaction
from polite request markers.

The shareable chart should show positive analytics as a separate positive-index
line, not as part of the swear-index line. The positive index is the share of
direct user messages with at least one positive lexicon hit. Avoid broad bare
terms such as `работает`, `именно`, `right`, `fixed`, `done`, or `правильно`
when they mostly match neutral instructions, quotes, or negative phrases like
`не работает`; prefer phrase-level positive terms with clear approval context.

## Ambiguous Term Adjudication

For each candidate, review a small evidence sample before adding it. Include a term only when it is a direct swear or a high-precision frustration phrase in this user's own direct turns. Prefer phrase-level terms over broad words.

Use this rubric:

- Include: repeated direct-corpus evidence, clear anger/frustration/rejection, low chance of matching ordinary work.
- Narrow: emotional only inside a longer phrase, such as `what the hell is this` rather than bare `hell`, or `this is a mess` rather than bare `a mess`.
- Exclude from the chart metric: mostly ordinary task management, reset language, pasted logs, quoted instructions, benchmark labels, code/errors, or neutral debugging.
- Keep as a review lead: useful to inspect but too ambiguous for the visible `swear_index_message_rate`.

Put ambiguous but useful terms in `swear_index_excluded_terms`. They will still match in review CSVs, but they will not count in the chart unless another stronger matched term appears in the same message.

Keep a short tuning ledger when preparing a reusable artifact: term, action, matched count, reviewed sample size, false-positive pattern, and reason. For example, `start again` is a review lead because it often means a workflow reset, while `kill it and start again` is a countable phrase because it marks a hotter reset request.

## Tuning Process

1. Run the default audit.
2. Read the top counted terms and 20-50 matched snippets.
3. Read `positive_term_counts.csv` and `positive_messages.csv` for gratitude,
   courtesy, approval, and satisfaction matches.
4. Read candidate phrases for compact, repeated user wording.
5. Add only high-precision phrase terms to the copied lexicons.
6. Remove or narrow terms that mostly match neutral work requests, pasted logs, benchmark labels, or quoted instructions.
7. Re-run and compare top terms before trusting the chart.

The goal is semantic adaptation, not copying a global swear list. For a new user, look for their own ways of expressing anger, disappointment, disbelief, impatience, or sharp rejection. A phrase can be countable even if it is not literal profanity, but it should be narrow enough that it rarely appears in ordinary debugging or planning.

Do not overfit to one person's habits. If the phrase only appears in the example screenshot or README and not in the current user's corpus, do not present it as an observed top term. If a starter term never appears, it can remain in the default lexicon as future coverage, but it should not be highlighted as part of that user's story.

## Corpus Reader Subagents

Use reader subagents when the corpus is large, the user's language/slang is unfamiliar, the first-pass terms are noisy, or a one-person pass cannot review enough evidence and the user explicitly allows subagent work.

Leave `--include-subagents` off by default. It controls whether spawned agent prompts are part of the analyzed user corpus; it is not needed for using subagents as reviewers.

Shard only extracted direct-user messages by date range, thread set, or file path. Give each reader a bounded job:

- Precision audit: identify false positives in current matches and recommend include, narrow, exclude, or review-lead actions.
- Recall audit: find missed phrase-level frustration candidates from unmatched messages and `candidate_phrases.csv`.
- Presentation audit: check that the chart, examples, and model legend are understandable and generated from current-run data.

Each reader should return evidence summaries, not raw private snippets: candidate phrase, rough count or output row references, 2-5 short positive examples paraphrased or minimally quoted, likely false positives, and recommended action. The coordinator makes the final lexicon edits.

## Chart Content

- Title should explain the artifact plainly and personalize when possible, such as `Peter's Codex Swear Meter`. Use `--owner-name` when the local account name is not the right display name.
- Subtitle should fit on one line when possible and say that the line is a count/share of direct user messages.
- Bars should show weekly message volume.
- The line should show `swear_index_message_rate`: the percentage of extracted direct user messages in that week with at least one included swear-index term.
- The model legend should list dominant model families in newest-first order
  when the goal is a timeline. `Msgs` is the direct user-message count for that
  displayed model family in the visible chart window. `% Swear` is a
  per-model-family swear-index rate: swear-index messages for that displayed
  model family divided by all direct user messages for that displayed model
  family. It is not model usage share and it is not the all-model weekly line
  rate.
- Model labels are metadata-backed, not inferred from message text. If a user
  questions recent model counts, audit `source_path`, `title`, `source_kind`,
  `is_subagent`, and `model_label` for the disputed date range before changing
  the calculation.
- Positive-index line should use `positive_index_message_rate`: positive matched
  direct user messages divided by all direct user messages in that week.
- In shareable outputs, name only public GPT model families. Fold unrecognized
  or private model labels into `Other` so internal codenames never appear in
  screenshots, README examples, or generated HTML.
- The examples/top-terms section should be generated from the current run after filtering to swear-index groups, excluding `swear_index_excluded_terms`, and requiring nonzero message counts.
- Do not reuse default lexicon examples as if they were observed examples.
- Generate the model legend only from the current run's `model_timeline_weekly.csv` or embedded chart data. If `unknown` appears, say model metadata was unavailable rather than inventing labels.

## Open-Source Notes

- The tool is local-first and should not upload logs.
- Keep `outputs/` gitignored.
- Include a screenshot only if the owner approves it.
- Document that the default lexicon is a starter and every serious run should inspect/tune it against the user's own corpus.
