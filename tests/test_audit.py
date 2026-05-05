import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from codex_log_tone_audit.audit import (
    DEFAULT_LEXICON,
    DEFAULT_LOGO,
    DEFAULT_SWEAR_LEXICON,
    build_html_period_rows,
    build_model_legend,
    chart_model_display_label,
    chart_title,
    compile_patterns,
    diff_new_records,
    infer_owner_name,
    is_swear_index_hit,
    is_swear_index_group,
    match_record,
    model_label,
    main,
    parse_rollout,
    period_date_text,
    should_skip_message,
    top_swear_index_examples,
    week_key,
)


class AuditTests(unittest.TestCase):
    def test_skip_scaffold_and_automations(self):
        self.assertTrue(should_skip_message("# AGENTS.md instructions\n..."))
        self.assertTrue(should_skip_message("<skill>\n<name>active-research-loop</name>"))
        self.assertTrue(should_skip_message("<turn_aborted>"))
        self.assertTrue(should_skip_message("Automation: Queue Keeper\n..."))
        self.assertFalse(
            should_skip_message("Automation: Queue Keeper\n...", include_automations=True)
        )
        self.assertTrue(
            should_skip_message(
                "You are processing one item for a generic agent job.\nJob ID: x"
            )
        )

    def test_term_boundaries(self):
        lexicon = {
            "categories": {
                "problem_report": {
                    "weight": 1,
                    "terms": ["issue", "not working"],
                }
            }
        }
        patterns = compile_patterns(lexicon)
        self.assertEqual(match_record("the issue is not working", patterns)[0]["term"], "issue")
        self.assertFalse(match_record("the tissue sample is fine", patterns))

    def test_spice_pattern_groups(self):
        lexicon = {
            "categories": {
                "hard_swearing": {
                    "group": "swearing",
                    "weight": 4,
                    "terms": ["fuck", "fucking", "what the fuck"],
                }
            }
        }
        hits = match_record("what the fuck happened", compile_patterns(lexicon))
        self.assertEqual({hit["group"] for hit in hits}, {"swearing"})
        self.assertEqual({hit["term"] for hit in hits}, {"fuck", "what the fuck"})

    def test_swear_index_excludes_operational_friction_groups(self):
        self.assertTrue(is_swear_index_group("swearing"))
        self.assertTrue(is_swear_index_group("quality_critique"))
        self.assertFalse(is_swear_index_group("problem_report"))
        self.assertFalse(is_swear_index_group("incomplete_work"))
        self.assertFalse(is_swear_index_group("callout"))

    def test_swear_index_excludes_context_only_terms(self):
        lexicon = {
            "swear_index_excluded_terms": ["start again"],
            "categories": {
                "boundary": {
                    "group": "boundary_violation",
                    "weight": 3,
                    "terms": ["start again", "delete this shit"],
                }
            },
        }
        hits = match_record("delete this shit and start again", compile_patterns(lexicon))
        by_term = {hit["term"]: hit for hit in hits}
        self.assertFalse(is_swear_index_hit(by_term["start again"], lexicon))
        self.assertTrue(is_swear_index_hit(by_term["delete this shit"], lexicon))

    def test_top_examples_exclude_context_only_terms(self):
        lexicon = {"swear_index_excluded_terms": ["start again"], "categories": {}}
        messages = {
            ("boundary_violation", "boundary", "start again"): 3,
            ("boundary_violation", "boundary", "delete this shit"): 2,
            ("callout", "agent_callout", "try again"): 9,
        }
        occurrences = {
            ("boundary_violation", "boundary", "start again"): 4,
            ("boundary_violation", "boundary", "delete this shit"): 2,
            ("callout", "agent_callout", "try again"): 9,
        }
        examples = top_swear_index_examples(messages, occurrences, lexicon)
        self.assertEqual([row["term"] for row in examples], ["delete this shit"])

    def test_week_key(self):
        self.assertEqual(week_key("2026-03-11T17:44:49.123Z"), "2026-W11")

    def test_html_period_rows_include_model_swear_index_counts(self):
        rows = build_html_period_rows(
            {"2026-W01": Counter({"total_messages": 10, "swear_index_messages": 2})},
            {"2026-W01": Counter({"gpt-5.5 (xhigh)": 10})},
            {"2026-W01": Counter({"gpt-5.5 (xhigh)": 2})},
        )

        self.assertEqual(rows[0]["models"][0]["messages"], 10)
        self.assertEqual(rows[0]["models"][0]["swearIndexMessages"], 2)

    def test_model_legend_percent_is_per_model_swear_rate(self):
        rows = [
            {
                "dominantModel": "gpt-5.5 (xhigh)",
                "models": [
                    {"label": "gpt-5.5 (xhigh)", "messages": 10, "swearIndexMessages": 2},
                    {"label": "gpt-5.4 (xhigh)", "messages": 5, "swearIndexMessages": 0},
                ],
            },
            {
                "dominantModel": "gpt-5.4 (high)",
                "models": [
                    {"label": "gpt-5.4 (high)", "messages": 15, "swearIndexMessages": 3},
                    {"label": "gpt-5.5 (medium)", "messages": 5, "swearIndexMessages": 0},
                ],
            },
        ]

        legend = {row["displayLabel"]: row for row in build_model_legend(rows)}

        self.assertEqual(legend["GPT-5.5"]["messages"], 15)
        self.assertEqual(legend["GPT-5.5"]["swearIndexMessages"], 2)
        self.assertEqual(legend["GPT-5.5"]["swearIndexRate"], 0.133333)
        self.assertEqual(legend["GPT-5.4"]["messages"], 20)
        self.assertEqual(legend["GPT-5.4"]["swearIndexMessages"], 3)
        self.assertEqual(legend["GPT-5.4"]["swearIndexRate"], 0.15)

    def test_chart_model_display_label_keeps_unrecognized_models_distinct(self):
        self.assertEqual(
            chart_model_display_label("gpt-5.3-codex-spark (xhigh)"),
            "GPT-5.3 Codex",
        )
        self.assertEqual(chart_model_display_label("crest-alpha (xhigh)"), "Crest")
        self.assertEqual(chart_model_display_label("some-new-model (medium)"), "some-new-model")

    def test_model_label(self):
        self.assertEqual(model_label("gpt-5.4", "xhigh"), "gpt-5.4 (xhigh)")
        self.assertEqual(model_label("gpt-5.4", ""), "gpt-5.4")
        self.assertEqual(model_label("", "xhigh"), "unknown")

    def test_period_date_text(self):
        self.assertEqual(period_date_text("2026-W11"), ("Mar 9", "Mar 9-15, 2026"))
        self.assertEqual(period_date_text("2026-03"), ("Mar 2026", "2026-03"))

    def test_packaged_default_lexicons_exist(self):
        self.assertTrue(DEFAULT_LEXICON.exists())
        self.assertTrue(DEFAULT_SWEAR_LEXICON.exists())
        self.assertTrue(DEFAULT_LOGO.exists())
        self.assertLess(DEFAULT_LOGO.stat().st_size, 100_000)

    def test_chart_title_personalizes_owner_name(self):
        self.assertEqual(infer_owner_name("peter"), "Peter")
        self.assertEqual(chart_title("peter"), "Peter's Codex Swear Meter")
        self.assertEqual(chart_title("james"), "James' Codex Swear Meter")
        self.assertEqual(chart_title(""), "Codex Swear Meter")

    def test_diff_new_records_uses_stable_message_identity(self):
        previous = [
            {
                "thread_id": "thread-1",
                "timestamp": "2026-01-01T00:00:01Z",
                "message": "already processed",
            }
        ]
        current = [
            {
                "thread_id": "thread-1",
                "timestamp": "2026-01-01T00:00:01Z",
                "message": "already   processed",
            },
            {
                "thread_id": "thread-1",
                "timestamp": "2026-01-01T00:00:02Z",
                "message": "what the hell is this",
            },
        ]
        self.assertEqual(diff_new_records(current, previous), [current[1]])

    def test_parse_rollout_excludes_subagents_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp)
            path = codex_home / "sessions/2026/01/01/rollout-2026-01-01T00-00-00-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.jsonl"
            path.parent.mkdir(parents=True)
            lines = [
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                        "cwd": "/tmp/example",
                        "source": {"subagent": {"thread_spawn": {"depth": 1}}},
                    },
                },
                {
                    "timestamp": "2026-01-01T00:00:01Z",
                    "type": "event_msg",
                    "payload": {"type": "user_message", "message": "this is broken"},
                },
            ]
            path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
            self.assertEqual(
                parse_rollout(path, codex_home, {}, {}, include_subagents=False, include_automations=False),
                [],
            )
            included = parse_rollout(
                path,
                codex_home,
                {},
                {},
                include_subagents=True,
                include_automations=False,
            )
            self.assertEqual(len(included), 1)
            self.assertTrue(included[0]["is_subagent"])

    def test_parse_rollout_skips_fallback_scaffold_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp)
            path = codex_home / "sessions/2026/01/01/rollout-2026-01-01T00-00-00-cccccccc-cccc-cccc-cccc-cccccccccccc.jsonl"
            path.parent.mkdir(parents=True)
            lines = [
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                        "cwd": "/tmp/example",
                    },
                },
                {
                    "timestamp": "2026-01-01T00:00:01Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "<skill>\n<name>active-research-loop</name>"}],
                    },
                },
                {
                    "timestamp": "2026-01-01T00:00:02Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "what the hell is this"}],
                    },
                },
            ]
            path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
            records = parse_rollout(
                path,
                codex_home,
                {},
                {},
                include_subagents=False,
                include_automations=False,
            )
            self.assertEqual([record["message"] for record in records], ["what the hell is this"])

    def test_audit_command_runs_end_to_end_on_fixture_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            codex_home = root / ".codex"
            out_dir = root / "outputs"
            path = codex_home / "sessions/2026/01/01/rollout-2026-01-01T00-00-00-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb.jsonl"
            path.parent.mkdir(parents=True)
            lines = [
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                        "cwd": "/tmp/example",
                    },
                },
                {
                    "timestamp": "2026-01-01T00:00:01Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "what the hell is this, it looks really bad",
                    },
                },
            ]
            path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")

            main(
                [
                    "audit",
                    "--codex-home",
                    str(codex_home),
                    "--out-dir",
                    str(out_dir),
                    "--owner-name",
                    "alex",
                ]
            )

            html = (out_dir / "spice-timeline.html").read_text(encoding="utf-8")
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertIn("Alex&#x27;s Codex Swear Meter", html)
            self.assertIn("% of Codex user messages containing swearing", html)
            self.assertIn('class="chart-logo"', html)
            self.assertIn("data:image/png;base64,", html)
            self.assertIn("model-rate", html)
            self.assertIn("drawSwearLabels", html)
            self.assertEqual(summary["total_user_messages"], 1)
            self.assertEqual(summary["spice"]["swear_index_messages"], 1)

    def test_incremental_command_writes_delta_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            codex_home = root / ".codex"
            out_dir = root / "outputs"
            path = codex_home / "sessions/2026/01/01/rollout-2026-01-01T00-00-00-cccccccc-cccc-cccc-cccc-cccccccccccc.jsonl"
            path.parent.mkdir(parents=True)
            lines = [
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                        "cwd": "/tmp/example",
                    },
                },
                {
                    "timestamp": "2026-01-01T00:00:01Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "already processed",
                    },
                },
                {
                    "timestamp": "2026-01-01T00:00:02Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "what the hell is this",
                    },
                },
            ]
            path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
            out_dir.mkdir()
            (out_dir / "user_messages.jsonl").write_text(
                json.dumps(
                    {
                        "thread_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                        "timestamp": "2026-01-01T00:00:01Z",
                        "message": "already processed",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            main(
                [
                    "incremental",
                    "--codex-home",
                    str(codex_home),
                    "--out-dir",
                    str(out_dir),
                    "--owner-name",
                    "alex",
                ]
            )

            delta_rows = [
                json.loads(line)
                for line in (out_dir / "incremental/new_user_messages.jsonl").read_text(
                    encoding="utf-8"
                ).splitlines()
            ]
            status = json.loads(
                (out_dir / "incremental/incremental_status.json").read_text(
                    encoding="utf-8"
                )
            )
            summary = json.loads(
                (out_dir / "incremental/summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual([row["message"] for row in delta_rows], ["what the hell is this"])
            self.assertTrue(status["needs_refresh"])
            self.assertEqual(status["new_user_messages"], 1)
            self.assertFalse(status["analysis_skipped"])
            self.assertEqual(summary["total_user_messages"], 1)
            self.assertEqual(summary["spice"]["swear_index_messages"], 1)

    def test_incremental_skip_analysis_clears_stale_delta_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            codex_home = root / ".codex"
            out_dir = root / "outputs"
            path = codex_home / "sessions/2026/01/01/rollout-2026-01-01T00-00-00-dddddddd-dddd-dddd-dddd-dddddddddddd.jsonl"
            path.parent.mkdir(parents=True)
            lines = [
                {
                    "timestamp": "2026-01-01T00:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                        "cwd": "/tmp/example",
                    },
                },
                {
                    "timestamp": "2026-01-01T00:00:01Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "already processed",
                    },
                },
            ]
            path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
            out_dir.mkdir()
            (out_dir / "user_messages.jsonl").write_text(
                json.dumps(
                    {
                        "thread_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                        "timestamp": "2026-01-01T00:00:01Z",
                        "message": "already processed",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            delta_dir = out_dir / "incremental"
            delta_dir.mkdir()
            (delta_dir / "summary.json").write_text('{"stale": true}\n', encoding="utf-8")

            main(
                [
                    "incremental",
                    "--codex-home",
                    str(codex_home),
                    "--out-dir",
                    str(out_dir),
                    "--skip-analysis",
                ]
            )

            status = json.loads(
                (out_dir / "incremental/incremental_status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(status["analysis_skipped"])
            self.assertEqual(status["new_user_messages"], 0)
            self.assertFalse((delta_dir / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
