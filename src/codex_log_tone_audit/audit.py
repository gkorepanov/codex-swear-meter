from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


UUID_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
TOKEN_RE = re.compile(r"[a-z][a-z0-9']+", re.IGNORECASE)
PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_LEXICON = PACKAGE_DIR / "assets" / "negative_terms.json"
DEFAULT_SWEAR_LEXICON = PACKAGE_DIR / "assets" / "spice_terms.json"
DEFAULT_LOGO = PACKAGE_DIR / "assets" / "codex-swear-meter-logo.png"

SCAFFOLD_PREFIXES = (
    "# AGENTS.md instructions",
    "<INSTRUCTIONS>",
    "<environment_context>",
    "<permissions instructions>",
)

STOPWORDS = {
    "a",
    "about",
    "again",
    "all",
    "also",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "done",
    "for",
    "from",
    "get",
    "go",
    "had",
    "has",
    "have",
    "he",
    "her",
    "here",
    "him",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "just",
    "like",
    "me",
    "more",
    "my",
    "no",
    "not",
    "now",
    "of",
    "on",
    "one",
    "or",
    "our",
    "out",
    "please",
    "so",
    "some",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "think",
    "this",
    "to",
    "up",
    "us",
    "use",
    "want",
    "was",
    "we",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
    "you",
    "your",
}

SPICE_TIMELINE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__CHART_TITLE__</title>
  <style>
    :root {
      --bg: #f7f8fb;
      --paper: #ffffff;
      --ink: #111827;
      --muted: #596579;
      --grid: #dfe5ee;
      --soft-grid: #eef2f7;
      --signal: #ef3340;
      --volume: #2f6fed;
      --border: #d7dee9;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 15px/1.4 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    main {
      width: min(1240px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 36px;
    }

    .chart-card {
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 26px;
      overflow: hidden;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 260px;
      column-gap: 22px;
    }

    .chart-top {
      grid-column: 1;
      margin-bottom: 18px;
      display: flex;
      align-items: center;
      gap: 18px;
      min-width: 0;
    }

    .chart-logo {
      width: 84px;
      height: 84px;
      flex: 0 0 auto;
      object-fit: contain;
      display: block;
    }

    .title-copy {
      min-width: 0;
    }

    h1 {
      margin: 0;
      font-size: 50px;
      line-height: 1;
      letter-spacing: 0;
      white-space: nowrap;
    }

    .subtitle {
      margin: 10px 0 0;
      max-width: none;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.35;
      white-space: nowrap;
    }

    .chart-layout {
      display: contents;
    }

    .chart-wrap {
      position: relative;
      min-width: 0;
      grid-column: 1;
      grid-row: 2;
    }

    canvas {
      display: block;
      width: 100%;
      height: clamp(560px, 54vw, 690px);
    }

    .side-panel {
      grid-column: 2;
      grid-row: 1 / span 2;
      border-left: 1px solid var(--border);
      padding-left: 20px;
      display: flex;
      flex-direction: column;
      gap: 22px;
      min-width: 0;
    }

    h2 {
      margin: 0 0 10px;
      color: var(--ink);
      font-size: 13px;
      line-height: 1.2;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .key-list,
    .examples-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 11px;
    }

    .model-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 9px;
    }

    .key-list li {
      display: grid;
      grid-template-columns: 22px minmax(0, 1fr);
      align-items: start;
      gap: 10px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.3;
    }

    .model-list li {
      display: grid;
      grid-template-columns: 22px minmax(0, 1fr) auto;
      align-items: center;
      gap: 10px;
      color: var(--ink);
      font-size: 14px;
      font-weight: 800;
      line-height: 1.2;
    }

    .model-count {
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      line-height: 1.2;
      white-space: nowrap;
    }

    .key-list strong,
    .examples-list strong {
      display: block;
      color: var(--ink);
      font-size: 14px;
      line-height: 1.25;
      overflow-wrap: anywhere;
    }

    .key-list span {
      display: block;
      margin-top: 2px;
    }

    .bar-key {
      width: 16px;
      height: 20px;
      margin-top: 1px;
      border-radius: 2px;
      background: rgba(47, 111, 237, 0.25);
      border: 1px solid rgba(47, 111, 237, 0.55);
    }

    .line-key {
      width: 21px;
      height: 4px;
      margin-top: 7px;
      border-radius: 99px;
      background: var(--signal);
    }

    .dot-key {
      display: inline-block;
      width: 22px;
      height: 22px;
      margin-top: 0;
      border-radius: 6px;
      background: var(--muted);
      border: 1px solid rgba(17, 24, 39, 0.14);
    }

    .examples-list {
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.3;
    }

    .examples-list li {
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 8px 10px;
      color: var(--ink);
      font-weight: 700;
      background: #fbfcff;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: center;
      gap: 10px;
    }

    .examples-list li span {
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      white-space: nowrap;
    }

    .tooltip {
      position: absolute;
      z-index: 2;
      min-width: 220px;
      max-width: min(300px, calc(100vw - 48px));
      pointer-events: none;
      opacity: 0;
      transform: translate(-50%, -112%);
      transition: opacity 120ms ease;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: rgba(252, 253, 255, 0.98);
      box-shadow: 0 12px 30px rgba(17, 24, 39, 0.12);
      padding: 11px 13px;
      color: var(--ink);
      font-size: 13px;
    }

    .tooltip strong {
      display: block;
      margin-bottom: 4px;
    }

    .tooltip span {
      display: block;
      color: var(--muted);
    }

    @media (max-width: 900px) {
      main {
        width: min(740px, calc(100vw - 24px));
        padding-top: 18px;
      }

      .chart-card {
        padding: 16px;
        display: block;
      }

      .chart-top {
        gap: 12px;
        align-items: flex-start;
      }

      .chart-logo {
        width: 58px;
        height: 58px;
        margin-top: 3px;
      }

      .chart-layout {
        display: grid;
        grid-template-columns: 1fr;
        gap: 16px;
      }

      .chart-wrap {
        grid-column: auto;
        grid-row: auto;
      }

      .side-panel {
        grid-column: auto;
        grid-row: auto;
        border-left: 0;
        border-top: 1px solid var(--border);
        padding: 16px 0 0;
      }

      canvas {
        height: 520px;
      }

      h1 {
        font-size: 31px;
        line-height: 1.05;
        white-space: normal;
      }

      .subtitle {
        font-size: 12px;
        white-space: normal;
      }

      .tooltip {
        display: none;
      }
    }
  </style>
</head>
<body>
  <main>
    <section class="chart-card" aria-label="Codex weekly swear-rate chart">
      <div class="chart-top">
        <img class="chart-logo" src="__CHART_LOGO_DATA_URI__" alt="" aria-hidden="true">
        <div class="title-copy">
          <h1>__CHART_TITLE__</h1>
          <p class="subtitle">__CHART_SUBTITLE__</p>
        </div>
      </div>

      <div class="chart-layout">
        <div class="chart-wrap">
          <canvas id="weeklyChart" aria-label="Weekly swear index and message volume"></canvas>
          <div id="weeklyTooltip" class="tooltip" role="status" aria-live="polite"></div>
        </div>
        <aside class="side-panel" aria-label="Chart legend">
          <div>
            <h2>Legend</h2>
            <ul class="key-list">
              <li><i class="bar-key"></i><span><strong>Message volume</strong></span></li>
              <li><i class="line-key"></i><span><strong>Swear index</strong></span></li>
            </ul>
          </div>

          <div>
            <h2>Dominant Model:</h2>
            <ul class="model-list" id="modelLegend"></ul>
          </div>

          <div>
            <h2>Top Terms</h2>
            <ul class="examples-list" id="exampleList"></ul>
          </div>
        </aside>
      </div>
    </section>
  </main>

  <script>
    const chartStartDate = "__CHART_START_DATE__";
    const weekly = __WEEKLY_DATA__.filter(row => !row.startDate || row.startDate >= chartStartDate);
    const swearExamples = __SWEAR_INDEX_EXAMPLES__;
    const css = getComputedStyle(document.documentElement);
    const colors = {
      ink: css.getPropertyValue("--ink").trim(),
      muted: css.getPropertyValue("--muted").trim(),
      grid: css.getPropertyValue("--grid").trim(),
      softGrid: css.getPropertyValue("--soft-grid").trim(),
      signal: css.getPropertyValue("--signal").trim(),
      volume: css.getPropertyValue("--volume").trim(),
      paper: css.getPropertyValue("--paper").trim()
    };

    function pct(value) {
      return `${(value * 100).toFixed(1)}%`;
    }

    function shortCount(value) {
      if (value >= 1000) return `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}k`;
      return String(value);
    }

    function escapeHTML(value) {
      return String(value).replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }

    function modelColor(label) {
      const value = String(label || "unknown").toLowerCase();
      if (value === "unknown") return "#7b8493";
      if (value.includes("5.5")) return "#16a34a";
      if (value.includes("5.4")) return "#2f6fed";
      if (value.includes("5.3")) return "#a855f7";
      if (value.includes("5.2")) return "#f59e0b";
      if (value.includes("5.1")) return "#db2777";
      if (value.includes("crest")) return "#e03743";
      return "#0f9f8f";
    }

    function shortModel(label) {
      const value = String(label || "unknown").toLowerCase();
      if (value === "unknown") return "unknown";
      const match = value.match(/gpt-(\\d+\\.\\d+)(?:-codex)?/);
      if (match) return `GPT-${match[1]}${value.includes("codex") ? " Codex" : ""}`;
      if (value.includes("crest")) return "Crest";
      return String(label || "other").replace(/ \\([^)]*\\)/, "");
    }

    function clamp(value, min, max) {
      return Math.max(min, Math.min(max, value));
    }

    function rgba(hex, alpha) {
      const clean = hex.replace("#", "");
      const value = parseInt(clean.length === 3 ? clean.split("").map(c => c + c).join("") : clean, 16);
      const r = (value >> 16) & 255;
      const g = (value >> 8) & 255;
      const b = value & 255;
      return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }

    function prepareCanvas(canvas, fallbackHeight) {
      const rect = canvas.getBoundingClientRect();
      const parentWidth = canvas.parentElement ? canvas.parentElement.getBoundingClientRect().width : 0;
      const width = Math.max(320, rect.width || parentWidth || 320);
      const cssHeight = parseFloat(getComputedStyle(canvas).height) || fallbackHeight;
      const height = Math.max(420, cssHeight);
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      return { ctx, width, height };
    }

    function niceRateMax(data) {
      const observed = Math.max(0, ...data.map(row => row.swearIndexRate));
      const padded = Math.max(0.04, observed * 1.25);
      return Math.ceil(padded / 0.02) * 0.02;
    }

    function niceCountMax(data) {
      const observed = Math.max(1, ...data.map(row => row.total));
      const step = observed > 1000 ? 500 : 250;
      return Math.ceil(observed / step) * step;
    }

    function drawChart(canvas, data) {
      const { ctx, width, height } = prepareCanvas(canvas, 620);
      const mobile = width < 560;
      const pad = {
        top: mobile ? 54 : 60,
        right: mobile ? 62 : 78,
        bottom: mobile ? 54 : 58,
        left: mobile ? 68 : 86
      };
      const plotW = width - pad.left - pad.right;
      const plotH = height - pad.top - pad.bottom;
      const maxRate = niceRateMax(data);
      const maxTotal = niceCountMax(data);
      const xStep = plotW / Math.max(1, data.length - 1);
      const barW = Math.max(8, Math.min(48, plotW / data.length * 0.58));

      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = colors.paper;
      ctx.fillRect(0, 0, width, height);

      ctx.strokeStyle = colors.grid;
      ctx.lineWidth = 1;
      ctx.font = `${mobile ? 12 : 14}px system-ui, sans-serif`;
      ctx.textAlign = "left";
      ctx.fillStyle = colors.signal;
      for (let i = 0; i <= 4; i += 1) {
        const y = pad.top + plotH * i / 4;
        const rateValue = maxRate * (1 - i / 4);
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(width - pad.right, y);
        ctx.stroke();
        ctx.fillText(pct(rateValue), mobile ? 4 : 10, y + 5);
      }

      ctx.textAlign = "right";
      ctx.fillStyle = colors.volume;
      for (let i = 0; i <= 4; i += 1) {
        const y = pad.top + plotH * i / 4;
        const countValue = maxTotal * (1 - i / 4);
        ctx.fillText(shortCount(Math.round(countValue)), width - (mobile ? 4 : 10), y + 5);
      }

      ctx.font = `800 ${mobile ? 13 : 15}px system-ui, sans-serif`;
      ctx.fillStyle = colors.signal;
      ctx.textAlign = "left";
      ctx.fillText("Swear index", mobile ? 4 : 10, pad.top - 20);
      ctx.fillStyle = colors.volume;
      ctx.textAlign = "right";
      ctx.fillText("Messages", width - (mobile ? 4 : 10), pad.top - 20);

      data.forEach((row, index) => {
        const x = pad.left + xStep * index;
        ctx.strokeStyle = colors.softGrid;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, pad.top);
        ctx.lineTo(x, pad.top + plotH);
        ctx.stroke();
      });

      data.forEach((row, index) => {
        const x = pad.left + xStep * index;
        const h = (row.total / maxTotal) * plotH;
        const color = modelColor(row.dominantModel);
        ctx.fillStyle = rgba(color, row.dominantModel === "unknown" ? 0.20 : 0.30);
        ctx.strokeStyle = rgba(color, row.dominantModel === "unknown" ? 0.42 : 0.62);
        ctx.fillRect(x - barW / 2, pad.top + plotH - h, barW, h);
        ctx.strokeRect(x - barW / 2, pad.top + plotH - h, barW, h);
      });

      ctx.strokeStyle = colors.signal;
      ctx.lineWidth = mobile ? 3 : 4;
      ctx.beginPath();
      data.forEach((row, index) => {
        const x = pad.left + xStep * index;
        const y = pad.top + plotH - (row.swearIndexRate / maxRate) * plotH;
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      data.forEach((row, index) => {
        const x = pad.left + xStep * index;
        const y = pad.top + plotH - (row.swearIndexRate / maxRate) * plotH;
        ctx.fillStyle = colors.signal;
        ctx.beginPath();
        ctx.arc(x, y, mobile ? 3 : 4, 0, Math.PI * 2);
        ctx.fill();
      });

      ctx.fillStyle = colors.muted;
      ctx.font = `${mobile ? 11 : 13}px system-ui, sans-serif`;
      ctx.textAlign = "center";
      data.forEach((row, index) => {
        const shouldShow = mobile
          ? index === 0 || index === data.length - 1 || (index % 4 === 0 && index < data.length - 3)
          : index === 0 || index === data.length - 1 || index % 2 === 0;
        if (!shouldShow) return;
        const x = pad.left + xStep * index;
        const label = row.dateLabel || row.label;
        ctx.fillText(label, x, height - (mobile ? 18 : 22));
      });

      canvas.__chart = { data, pad, plotW, plotH, maxRate, maxTotal, xStep, width, height };
    }

    function bindTooltip(canvas, tooltip) {
      function hide() {
        tooltip.style.opacity = "0";
      }
      function show(event) {
        const info = canvas.__chart;
        if (!info) return;
        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const rawIndex = Math.round((x - info.pad.left) / info.xStep);
        const index = clamp(rawIndex, 0, info.data.length - 1);
        const row = info.data[index];
        const pointX = info.pad.left + info.xStep * index;
        const pointY = info.pad.top + info.plotH - (row.swearIndexRate / info.maxRate) * info.plotH;
        tooltip.innerHTML = `
          <strong>${escapeHTML(row.dateRange || row.label)}</strong>
          <span>${row.total.toLocaleString()} messages</span>
          <span>${pct(row.swearIndexRate)} swear index (${row.swearIndexMessages} messages)</span>
        `;
        tooltip.style.left = `${clamp(pointX, 120, info.width - 120)}px`;
        tooltip.style.top = `${clamp(pointY, 92, info.height - 96)}px`;
        tooltip.style.opacity = "1";
      }
      canvas.addEventListener("mousemove", show);
      canvas.addEventListener("mouseleave", hide);
      canvas.addEventListener("focus", event => show(event));
      canvas.addEventListener("blur", hide);
    }

    function renderModelLegend(data) {
      const byModel = new Map();
      data.forEach((row, index) => {
        const label = row.dominantModel || "unknown";
        const color = modelColor(label);
        if (!byModel.has(color)) byModel.set(color, { label, color, first: index, last: index, messages: 0 });
        else byModel.get(color).last = index;
      });
      data.forEach(row => {
        (row.models || []).forEach(model => {
          const modelColorKey = modelColor(model.label || "unknown");
          if (!byModel.has(modelColorKey)) return;
          byModel.get(modelColorKey).messages += Number(model.messages || 0);
        });
      });
      const models = Array.from(byModel.values()).sort((a, b) => b.last - a.last);
      document.getElementById("modelLegend").innerHTML = models.map(model => `
        <li aria-label="${escapeHTML(`${shortModel(model.label)}: ${model.messages.toLocaleString()} messages`)}">
          <i class="dot-key" title="${escapeHTML(shortModel(model.label))}" style="background: ${model.color}"></i>
          <span class="model-name">${escapeHTML(shortModel(model.label))}</span>
          <span class="model-count">${model.messages.toLocaleString()} msgs</span>
        </li>
      `).join("");
    }

    function renderExamples(examples) {
      document.getElementById("exampleList").innerHTML = examples.map(example => `
        <li>
          <strong>${escapeHTML(example.term)}</strong>
          <span>${Number(example.messages).toLocaleString()} msgs</span>
        </li>
      `).join("");
    }

    const weeklyCanvas = document.getElementById("weeklyChart");
    const weeklyTooltip = document.getElementById("weeklyTooltip");

    function renderChart() {
      weeklyTooltip.style.opacity = "0";
      weeklyTooltip.style.left = "";
      weeklyTooltip.style.top = "";
      drawChart(weeklyCanvas, weekly);
    }

    renderModelLegend(weekly);
    renderExamples(swearExamples);
    bindTooltip(weeklyCanvas, weeklyTooltip);
    renderChart();
    window.addEventListener("resize", () => {
      window.clearTimeout(window.__swearResizeTimer);
      window.__swearResizeTimer = window.setTimeout(renderChart, 80);
    });
  </script>
</body>
</html>
"""

HTML_CHART_START_DATE = date(2025, 12, 29)
CHART_SUBTITLE = (
    "Weekly count and percentage of direct user messages containing expletives or "
    "swear-adjacent frustration"
)
SWEAR_INDEX_GROUPS = frozenset(
    {
        "swearing",
        "spicy_moment",
        "quality_critique",
        "boundary_violation",
        "frustrated_rework",
    }
)


@dataclass(frozen=True)
class ThreadMeta:
    thread_id: str
    title: str
    cwd: str
    rollout_path: str
    created_at: int | None
    updated_at: int | None
    archived: bool | None
    model_provider: str
    model: str
    reasoning_effort: str


@dataclass(frozen=True)
class TermPattern:
    category: str
    term: str
    weight: int
    group: str
    pattern: re.Pattern[str]


def infer_owner_name(explicit_owner_name: str | None = None) -> str:
    if explicit_owner_name is not None:
        return normalize_owner_name(explicit_owner_name)
    raw = os.environ.get("CODEX_SWEAR_METER_OWNER") or os.environ.get("USER") or Path.home().name
    return normalize_owner_name(raw)


def normalize_owner_name(raw_name: str) -> str:
    cleaned = re.sub(r"[_\-.]+", " ", raw_name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned or cleaned.casefold() in {"root", "runner", "unknown"}:
        return ""
    return " ".join(part[:1].upper() + part[1:] for part in cleaned.split())


def chart_title(owner_name: str | None = None) -> str:
    owner = infer_owner_name(owner_name)
    if not owner:
        return "Codex Swear Meter"
    suffix = "'" if owner.endswith("s") else "'s"
    return f"{owner}{suffix} Codex Swear Meter"


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "extract":
        records = extract_messages(
            Path(args.codex_home),
            Path(args.state) if args.state else None,
            include_subagents=args.include_subagents,
            include_automations=args.include_automations,
        )
        write_jsonl(Path(args.out), records)
        print(f"wrote {len(records):,} user messages to {args.out}")
    elif args.command == "analyze":
        records = read_jsonl(Path(args.messages))
        analyze_records(
            records,
            Path(args.lexicon),
            Path(args.spice_lexicon),
            Path(args.out_dir),
            args.sample_limit,
            args.owner_name,
        )
    elif args.command == "audit":
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        messages_path = out_dir / "user_messages.jsonl"
        records = extract_messages(
            Path(args.codex_home),
            Path(args.state) if args.state else None,
            include_subagents=args.include_subagents,
            include_automations=args.include_automations,
        )
        write_jsonl(messages_path, records)
        analyze_records(
            records,
            Path(args.lexicon),
            Path(args.spice_lexicon),
            out_dir,
            args.sample_limit,
            args.owner_name,
        )
        print(f"wrote {len(records):,} user messages to {messages_path}")
        print(f"wrote audit outputs to {out_dir}")
    elif args.command == "incremental":
        out_dir = Path(args.out_dir)
        delta_dir = Path(args.delta_dir) if args.delta_dir else out_dir / "incremental"
        baseline_messages_path = (
            Path(args.messages) if args.messages else out_dir / "user_messages.jsonl"
        )
        previous_records = (
            read_jsonl(baseline_messages_path) if baseline_messages_path.exists() else []
        )
        current_records = extract_messages(
            Path(args.codex_home),
            Path(args.state) if args.state else None,
            include_subagents=args.include_subagents,
            include_automations=args.include_automations,
        )
        new_records = diff_new_records(current_records, previous_records)
        delta_messages_path = delta_dir / "new_user_messages.jsonl"
        write_jsonl(delta_messages_path, new_records)
        write_incremental_status(
            delta_dir / "incremental_status.json",
            previous_records,
            current_records,
            new_records,
            baseline_messages_path,
            delta_messages_path,
            delta_dir,
            analysis_skipped=args.skip_analysis,
        )
        if not args.skip_analysis:
            analyze_records(
                new_records,
                Path(args.lexicon),
                Path(args.spice_lexicon),
                delta_dir,
                args.sample_limit,
                args.owner_name,
            )
        else:
            clear_incremental_analysis_outputs(delta_dir)
        print(
            "found "
            f"{len(new_records):,} new user messages "
            f"({len(previous_records):,} baseline, {len(current_records):,} current)"
        )
        print(f"wrote incremental messages to {delta_messages_path}")
        print(f"wrote incremental status to {delta_dir / 'incremental_status.json'}")
    else:
        parser.error(f"unknown command: {args.command}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-log-tone-audit",
        description="Extract direct user messages from Codex logs and count negative/upset signals.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="Extract direct user messages to JSONL.")
    extract.add_argument("--codex-home", default=str(Path.home() / ".codex"))
    extract.add_argument("--state", default=None, help="Optional explicit state_5.sqlite path.")
    extract.add_argument("--out", required=True)
    extract.add_argument(
        "--include-subagents",
        action="store_true",
        help="Include spawned subagent and generic agent-job prompts.",
    )
    extract.add_argument(
        "--include-automations",
        action="store_true",
        help="Include recurring automation prompts.",
    )

    analyze = subparsers.add_parser("analyze", help="Analyze an extracted user_messages.jsonl file.")
    analyze.add_argument("--messages", required=True)
    analyze.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    analyze.add_argument("--spice-lexicon", default=str(DEFAULT_SWEAR_LEXICON))
    analyze.add_argument("--out-dir", required=True)
    analyze.add_argument("--sample-limit", type=int, default=75)
    analyze.add_argument(
        "--owner-name",
        default=None,
        help="Optional display name for the chart title. Defaults to the local account name.",
    )

    audit = subparsers.add_parser("audit", help="Extract and analyze in one pass.")
    audit.add_argument("--codex-home", default=str(Path.home() / ".codex"))
    audit.add_argument("--state", default=None, help="Optional explicit state_5.sqlite path.")
    audit.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    audit.add_argument("--spice-lexicon", default=str(DEFAULT_SWEAR_LEXICON))
    audit.add_argument("--out-dir", default="outputs")
    audit.add_argument("--sample-limit", type=int, default=75)
    audit.add_argument(
        "--owner-name",
        default=None,
        help="Optional display name for the chart title. Defaults to the local account name.",
    )
    audit.add_argument(
        "--include-subagents",
        action="store_true",
        help="Include spawned subagent and generic agent-job prompts.",
    )
    audit.add_argument(
        "--include-automations",
        action="store_true",
        help="Include recurring automation prompts.",
    )

    incremental = subparsers.add_parser(
        "incremental",
        help="Review direct user messages that are not present in the last extraction.",
    )
    incremental.add_argument("--codex-home", default=str(Path.home() / ".codex"))
    incremental.add_argument("--state", default=None, help="Optional explicit state_5.sqlite path.")
    incremental.add_argument(
        "--messages",
        default=None,
        help="Existing extracted JSONL to compare against. Defaults to <out-dir>/user_messages.jsonl.",
    )
    incremental.add_argument("--out-dir", default="outputs")
    incremental.add_argument(
        "--delta-dir",
        default=None,
        help="Directory for delta outputs. Defaults to <out-dir>/incremental.",
    )
    incremental.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    incremental.add_argument("--spice-lexicon", default=str(DEFAULT_SWEAR_LEXICON))
    incremental.add_argument("--sample-limit", type=int, default=75)
    incremental.add_argument(
        "--owner-name",
        default=None,
        help="Optional display name for the delta chart title. Defaults to the local account name.",
    )
    incremental.add_argument(
        "--skip-analysis",
        action="store_true",
        help="Only write the delta JSONL and status file.",
    )
    incremental.add_argument(
        "--include-subagents",
        action="store_true",
        help="Include spawned subagent and generic agent-job prompts.",
    )
    incremental.add_argument(
        "--include-automations",
        action="store_true",
        help="Include recurring automation prompts.",
    )
    return parser


def extract_messages(
    codex_home: Path,
    state_path: Path | None = None,
    *,
    include_subagents: bool = False,
    include_automations: bool = False,
) -> list[dict[str, Any]]:
    codex_home = codex_home.expanduser().resolve()
    state_path = state_path or codex_home / "state_5.sqlite"
    by_path, by_thread = load_thread_index(state_path)
    files = list(find_rollout_files(codex_home))
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for path in files:
        for record in parse_rollout(
            path,
            codex_home,
            by_path,
            by_thread,
            include_subagents=include_subagents,
            include_automations=include_automations,
        ):
            key = (record.get("thread_id", ""), record.get("timestamp", ""), record["message"])
            if key in seen:
                continue
            seen.add(key)
            records.append(record)

    records.sort(key=lambda row: (row.get("timestamp") or "", row.get("source_path") or ""))
    return records


def find_rollout_files(codex_home: Path) -> Iterable[Path]:
    roots = [codex_home / "sessions", codex_home / "archived_sessions"]
    for root in roots:
        if not root.exists():
            continue
        yield from sorted(root.rglob("rollout-*.jsonl"))


def load_thread_index(state_path: Path) -> tuple[dict[str, ThreadMeta], dict[str, ThreadMeta]]:
    by_path: dict[str, ThreadMeta] = {}
    by_thread: dict[str, ThreadMeta] = {}
    if not state_path.exists():
        return by_path, by_thread
    query = """
        select id, title, cwd, rollout_path, created_at, updated_at, archived,
               model_provider, model, reasoning_effort
        from threads
    """
    try:
        con = sqlite3.connect(str(state_path))
        con.row_factory = sqlite3.Row
        for row in con.execute(query):
            meta = ThreadMeta(
                thread_id=row["id"],
                title=row["title"] or "",
                cwd=row["cwd"] or "",
                rollout_path=row["rollout_path"] or "",
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                archived=bool(row["archived"]) if row["archived"] is not None else None,
                model_provider=row["model_provider"] or "",
                model=row["model"] or "",
                reasoning_effort=row["reasoning_effort"] or "",
            )
            by_thread[meta.thread_id] = meta
            if meta.rollout_path:
                by_path[str(Path(meta.rollout_path))] = meta
        con.close()
    except sqlite3.Error:
        return by_path, by_thread
    return by_path, by_thread


def parse_rollout(
    path: Path,
    codex_home: Path,
    by_path: dict[str, ThreadMeta],
    by_thread: dict[str, ThreadMeta],
    *,
    include_subagents: bool,
    include_automations: bool,
) -> list[dict[str, Any]]:
    thread_id = thread_id_from_path(path)
    session_cwd = ""
    source_label = ""
    is_subagent = False
    event_records: list[dict[str, Any]] = []
    fallback_records: list[dict[str, Any]] = []
    fallback_seen: set[str] = set()
    meta = by_path.get(str(path)) or (by_thread.get(thread_id) if thread_id else None)

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        first_line = handle.readline()
        if first_line:
            header = parse_session_header(first_line)
            if header:
                thread_id = header.get("thread_id") or thread_id
                session_cwd = header.get("cwd") or ""
                source_label = header.get("source_label") or ""
                is_subagent = bool(header.get("is_subagent"))
                meta = meta or (by_thread.get(thread_id) if thread_id else None)
            if is_subagent and not include_subagents:
                return []
            handle.seek(0)

        for line_number, line in enumerate(handle, start=1):
            # The session_meta and assistant/tool lines can be very large. The audit only
            # needs direct user-message events, with response_item user messages as a fallback
            # for older logs that do not emit event_msg.user_message.
            is_event_candidate = '"user_message"' in line
            is_fallback_candidate = '"role":"user"' in line or '"role": "user"' in line
            if not is_event_candidate and not is_fallback_candidate:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = obj.get("payload")
            if not isinstance(payload, dict):
                continue

            if obj.get("type") == "event_msg" and payload.get("type") == "user_message":
                message = payload.get("message") or ""
                if should_skip_message(message, include_automations=include_automations):
                    continue
                event_records.append(
                    make_record(
                        path=path,
                        codex_home=codex_home,
                        line_number=line_number,
                        timestamp=obj.get("timestamp") or "",
                        thread_id=thread_id,
                        meta=meta,
                        session_cwd=session_cwd,
                        message=message,
                        source_kind="event_msg.user_message",
                        source_label=source_label,
                        is_subagent=is_subagent,
                        turn_index=len(event_records),
                    )
                )
                continue

            if obj.get("type") == "response_item" and payload.get("type") == "message":
                if payload.get("role") != "user":
                    continue
                message = content_to_text(payload.get("content"))
                if should_skip_message(message, include_automations=include_automations) or message in fallback_seen:
                    continue
                fallback_seen.add(message)
                fallback_records.append(
                    make_record(
                        path=path,
                        codex_home=codex_home,
                        line_number=line_number,
                        timestamp=obj.get("timestamp") or "",
                        thread_id=thread_id,
                        meta=meta,
                        session_cwd=session_cwd,
                        message=message,
                        source_kind="response_item.message",
                        source_label=source_label,
                        is_subagent=is_subagent,
                        turn_index=len(fallback_records),
                    )
                )

    return event_records if event_records else fallback_records


def make_record(
    *,
    path: Path,
    codex_home: Path,
    line_number: int,
    timestamp: str,
    thread_id: str,
    meta: ThreadMeta | None,
    session_cwd: str,
    message: str,
    source_kind: str,
    source_label: str,
    is_subagent: bool,
    turn_index: int,
) -> dict[str, Any]:
    clean = message.strip()
    message_id = hashlib.sha256(
        f"{thread_id}\0{timestamp}\0{line_number}\0{clean}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "id": message_id,
        "thread_id": thread_id,
        "timestamp": timestamp,
        "title": meta.title if meta else "",
        "cwd": meta.cwd if meta and meta.cwd else session_cwd,
        "archived": meta.archived if meta else None,
        "source_path": relative_path(path, codex_home),
        "line_number": line_number,
        "source_kind": source_kind,
        "source_label": source_label,
        "is_subagent": is_subagent,
        "model_provider": meta.model_provider if meta else "",
        "model": meta.model if meta else "",
        "reasoning_effort": meta.reasoning_effort if meta else "",
        "model_label": model_label(meta.model if meta else "", meta.reasoning_effort if meta else ""),
        "turn_index": turn_index,
        "char_count": len(clean),
        "word_count": len(TOKEN_RE.findall(clean)),
        "message": clean,
    }


def parse_session_header(line: str) -> dict[str, Any]:
    if '"type":"session_meta"' not in line and '"type": "session_meta"' not in line:
        return {}
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return {}
    payload = obj.get("payload")
    if not isinstance(payload, dict):
        return {}
    source = payload.get("source")
    source_label = source if isinstance(source, str) else json.dumps(source, sort_keys=True)
    return {
        "thread_id": payload.get("id") or "",
        "cwd": payload.get("cwd") or "",
        "source_label": source_label,
        "is_subagent": isinstance(source, dict) and "subagent" in source,
    }


def thread_id_from_path(path: Path) -> str:
    match = UUID_RE.search(path.name)
    return match.group(1) if match else ""


def relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path)


def model_label(model: str, reasoning_effort: str = "") -> str:
    model = (model or "").strip()
    effort = (reasoning_effort or "").strip()
    if not model:
        return "unknown"
    if effort:
        return f"{model} ({effort})"
    return model


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts)


def should_skip_message(message: str, *, include_automations: bool = False) -> bool:
    text = message.strip()
    if not text:
        return True
    if any(text.startswith(prefix) for prefix in SCAFFOLD_PREFIXES):
        return True
    if text.startswith("You are processing one item for a generic agent job."):
        return True
    if "Job ID:" in text and "Item ID:" in text and "Task instruction:" in text:
        return True
    if not include_automations and text.startswith("Automation:"):
        return True
    if text.startswith("# AGENTS.md instructions") or "--- project-doc ---" in text:
        return True
    if "<environment_context>" in text and "<current_date>" in text:
        return True
    if len(text) > 20_000 and "<INSTRUCTIONS>" in text:
        return True
    return False


def analyze_records(
    records: list[dict[str, Any]],
    lexicon_path: Path,
    spice_lexicon_path: Path,
    out_dir: Path,
    sample_limit: int,
    owner_name: str | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    lexicon = load_lexicon(lexicon_path)
    spice_lexicon = load_lexicon(spice_lexicon_path)
    patterns = compile_patterns(lexicon)
    spice_patterns = compile_patterns(spice_lexicon)

    matched_rows: list[dict[str, Any]] = []
    spice_rows: list[dict[str, Any]] = []
    category_messages: Counter[str] = Counter()
    category_occurrences: Counter[str] = Counter()
    signal_messages: Counter[str] = Counter()
    signal_occurrences: Counter[str] = Counter()
    spice_category_messages: Counter[str] = Counter()
    spice_category_occurrences: Counter[str] = Counter()
    spice_group_messages: Counter[str] = Counter()
    spice_group_occurrences: Counter[str] = Counter()
    spice_term_messages: Counter[tuple[str, str, str]] = Counter()
    spice_term_occurrences: Counter[tuple[str, str, str]] = Counter()
    term_messages: Counter[tuple[str, str]] = Counter()
    term_occurrences: Counter[tuple[str, str]] = Counter()
    month_messages: Counter[str] = Counter()
    month_matched: Counter[str] = Counter()
    monthly_spice: defaultdict[str, Counter[str]] = defaultdict(Counter)
    weekly_spice: defaultdict[str, Counter[str]] = defaultdict(Counter)
    model_messages: Counter[str] = Counter()
    model_spicy: Counter[str] = Counter()
    model_swear: Counter[str] = Counter()
    model_swear_index: Counter[str] = Counter()
    monthly_models: defaultdict[str, Counter[str]] = defaultdict(Counter)
    weekly_models: defaultdict[str, Counter[str]] = defaultdict(Counter)
    cwd_messages: Counter[str] = Counter()
    thread_messages: Counter[tuple[str, str]] = Counter()

    for record in records:
        timestamp = record.get("timestamp") or ""
        month = timestamp[:7] if len(timestamp) >= 7 else "unknown"
        week = week_key(timestamp)
        current_model = str(record.get("model_label") or "unknown")
        month_messages[month] += 1
        monthly_spice[month]["total_messages"] += 1
        weekly_spice[week]["total_messages"] += 1
        monthly_models[month][current_model] += 1
        weekly_models[week][current_model] += 1
        model_messages[current_model] += 1

        spice_hits = match_record(record["message"], spice_patterns)
        if spice_hits:
            model_spicy[current_model] += 1
            if any(hit["group"] == "swearing" for hit in spice_hits):
                model_swear[current_model] += 1
            if any(is_swear_index_hit(hit, spice_lexicon) for hit in spice_hits):
                model_swear_index[current_model] += 1
            write_spice_record(
                record,
                spice_hits,
                spice_lexicon,
                spice_rows,
                spice_category_messages,
                spice_category_occurrences,
                spice_group_messages,
                spice_group_occurrences,
                spice_term_messages,
                spice_term_occurrences,
                monthly_spice[month],
                weekly_spice[week],
            )

        hits = match_record(record["message"], patterns)
        if not hits:
            continue

        categories = sorted({hit["category"] for hit in hits})
        signals = sorted({category_signal(category, lexicon) for category in categories})
        terms = sorted({hit["term"] for hit in hits})
        score = sum(category_weight(cat, lexicon) for cat in categories)
        occurrences = sum(int(hit["count"]) for hit in hits)
        score += min(3, max(0, occurrences - len(terms)))

        for category in categories:
            category_messages[category] += 1
        for signal in signals:
            signal_messages[signal] += 1
        for hit in hits:
            key = (hit["category"], hit["term"])
            term_messages[key] += 1
            term_occurrences[key] += int(hit["count"])
            category_occurrences[hit["category"]] += int(hit["count"])
            signal_occurrences[category_signal(hit["category"], lexicon)] += int(hit["count"])

        month_matched[month] += 1
        cwd_messages[record.get("cwd") or ""] += 1
        thread_messages[(record.get("thread_id") or "", record.get("title") or "")] += 1
        matched_rows.append(
            {
                **{k: v for k, v in record.items() if k != "message"},
                "score": score,
                "categories": ";".join(categories),
                "signals": ";".join(signals),
                "terms": ";".join(terms),
                "occurrences": occurrences,
                "snippet": make_snippet(record["message"], hits),
            }
        )

    matched_rows.sort(key=lambda row: (-int(row["score"]), row.get("timestamp") or ""))
    spice_rows.sort(key=lambda row: (-int(row["spice_score"]), row.get("timestamp") or ""))
    write_summary(
        out_dir / "summary.json",
        records,
        matched_rows,
        spice_rows,
        category_messages,
        category_occurrences,
        signal_messages,
        signal_occurrences,
        spice_category_messages,
        spice_category_occurrences,
        spice_group_messages,
        spice_group_occurrences,
        spice_term_messages,
        spice_term_occurrences,
        model_messages,
        model_spicy,
        model_swear,
        model_swear_index,
        term_messages,
        term_occurrences,
    )
    write_category_counts(out_dir / "category_counts.csv", category_messages, category_occurrences)
    write_signal_counts(out_dir / "signal_counts.csv", signal_messages, signal_occurrences)
    write_term_counts(out_dir / "term_counts.csv", term_messages, term_occurrences)
    write_month_counts(out_dir / "monthly_counts.csv", month_messages, month_matched)
    write_matched_messages(out_dir / "matched_messages.csv", matched_rows)
    write_spice_counts(
        out_dir / "spice_counts.csv",
        spice_category_messages,
        spice_category_occurrences,
        spice_lexicon,
    )
    write_spice_group_counts(
        out_dir / "spice_group_counts.csv",
        spice_group_messages,
        spice_group_occurrences,
    )
    write_spice_term_counts(
        out_dir / "spice_term_counts.csv",
        spice_term_messages,
        spice_term_occurrences,
    )
    write_spice_messages(out_dir / "spice_messages.csv", spice_rows)
    write_spice_timeline(out_dir / "spice_timeline_monthly.csv", monthly_spice, "month")
    write_spice_timeline(out_dir / "spice_timeline_weekly.csv", weekly_spice, "week")
    write_model_counts(
        out_dir / "model_counts.csv",
        model_messages,
        model_spicy,
        model_swear,
        model_swear_index,
    )
    write_model_timeline(
        out_dir / "model_timeline_monthly.csv",
        monthly_models,
        monthly_spice,
        "month",
    )
    write_model_timeline(
        out_dir / "model_timeline_weekly.csv",
        weekly_models,
        weekly_spice,
        "week",
    )
    write_spice_timeline_html(
        out_dir / "spice-timeline.html",
        records,
        monthly_spice,
        weekly_spice,
        monthly_models,
        weekly_models,
        model_messages,
        model_spicy,
        model_swear,
        spice_term_messages,
        spice_term_occurrences,
        spice_lexicon,
        owner_name,
    )
    write_review_samples(out_dir / "review_samples.md", matched_rows[:sample_limit])
    write_spice_samples(out_dir / "spice_samples.md", spice_rows[:sample_limit])
    write_candidate_phrases(out_dir / "candidate_phrases.csv", records, matched_rows)


def load_lexicon(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def compile_patterns(lexicon: dict[str, Any]) -> list[TermPattern]:
    patterns: list[TermPattern] = []
    for category, spec in lexicon.get("categories", {}).items():
        weight = int(spec.get("weight", 1))
        for term in spec.get("terms", []):
            patterns.append(
                TermPattern(
                    category=category,
                    term=term,
                    weight=weight,
                    group=str(spec.get("group") or spec.get("signal") or category),
                    pattern=re.compile(term_to_regex(term), re.IGNORECASE),
                )
            )
    return patterns


def term_to_regex(term: str) -> str:
    escaped = re.escape(term.strip())
    escaped = re.sub(r"\\\s+", r"\\s+", escaped)
    if term and term[0].isalnum():
        escaped = r"(?<![A-Za-z0-9_])" + escaped
    if term and term[-1].isalnum():
        escaped = escaped + r"(?![A-Za-z0-9_])"
    return escaped


def category_weight(category: str, lexicon: dict[str, Any]) -> int:
    return int(lexicon.get("categories", {}).get(category, {}).get("weight", 1))


def category_signal(category: str, lexicon: dict[str, Any]) -> str:
    return str(lexicon.get("categories", {}).get(category, {}).get("signal", category))


def category_group(category: str, lexicon: dict[str, Any]) -> str:
    spec = lexicon.get("categories", {}).get(category, {})
    return str(spec.get("group") or spec.get("signal") or category)


def category_description(category: str, lexicon: dict[str, Any]) -> str:
    return str(lexicon.get("categories", {}).get(category, {}).get("description", ""))


def is_swear_index_group(group: str) -> bool:
    return group in SWEAR_INDEX_GROUPS


def swear_index_excluded_terms(lexicon: dict[str, Any]) -> set[str]:
    return {
        str(term).casefold()
        for term in lexicon.get("swear_index_excluded_terms", [])
        if str(term).strip()
    }


def is_swear_index_hit(hit: dict[str, Any], lexicon: dict[str, Any]) -> bool:
    term = str(hit["term"]).casefold()
    if term in swear_index_excluded_terms(lexicon):
        return False
    return is_swear_index_group(category_group(str(hit["category"]), lexicon))


def match_record(message: str, patterns: list[TermPattern]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for pattern in patterns:
        matches = list(pattern.pattern.finditer(message))
        if not matches:
            continue
        hits.append(
            {
                "category": pattern.category,
                "group": pattern.group,
                "term": pattern.term,
                "count": len(matches),
                "first_start": matches[0].start(),
                "first_end": matches[0].end(),
            }
        )
    hits.sort(key=lambda hit: (hit["first_start"], hit["category"], hit["term"]))
    return hits


def write_spice_record(
    record: dict[str, Any],
    hits: list[dict[str, Any]],
    spice_lexicon: dict[str, Any],
    spice_rows: list[dict[str, Any]],
    category_messages: Counter[str],
    category_occurrences: Counter[str],
    group_messages: Counter[str],
    group_occurrences: Counter[str],
    term_messages: Counter[tuple[str, str, str]],
    term_occurrences: Counter[tuple[str, str, str]],
    month_counts: Counter[str],
    week_counts: Counter[str],
) -> None:
    categories = sorted({hit["category"] for hit in hits})
    groups = sorted({category_group(category, spice_lexicon) for category in categories})
    terms = sorted({hit["term"] for hit in hits})
    occurrences = sum(int(hit["count"]) for hit in hits)
    spice_score = sum(category_weight(category, spice_lexicon) for category in categories)
    spice_score += min(4, max(0, occurrences - len(terms)))
    swear_index_hits = [
        hit
        for hit in hits
        if is_swear_index_hit(hit, spice_lexicon)
    ]
    swear_index_occurrences = sum(int(hit["count"]) for hit in swear_index_hits)

    for category in categories:
        category_messages[category] += 1
        month_counts[f"category:{category}:messages"] += 1
        week_counts[f"category:{category}:messages"] += 1
    for group in groups:
        group_messages[group] += 1
        month_counts[f"group:{group}:messages"] += 1
        week_counts[f"group:{group}:messages"] += 1
    for hit in hits:
        category = str(hit["category"])
        group = category_group(category, spice_lexicon)
        term = str(hit["term"])
        count = int(hit["count"])
        key = (group, category, term)
        term_messages[key] += 1
        term_occurrences[key] += count
        category_occurrences[category] += count
        group_occurrences[group] += count
        month_counts[f"category:{category}:occurrences"] += count
        week_counts[f"category:{category}:occurrences"] += count
        month_counts[f"group:{group}:occurrences"] += count
        week_counts[f"group:{group}:occurrences"] += count

    month_counts["spicy_messages"] += 1
    week_counts["spicy_messages"] += 1
    month_counts["spicy_occurrences"] += occurrences
    week_counts["spicy_occurrences"] += occurrences
    if "swearing" in groups:
        month_counts["swear_messages"] += 1
        week_counts["swear_messages"] += 1
        month_counts["swear_occurrences"] += sum(
            int(hit["count"])
            for hit in hits
            if category_group(str(hit["category"]), spice_lexicon) == "swearing"
        )
        week_counts["swear_occurrences"] += sum(
            int(hit["count"])
            for hit in hits
            if category_group(str(hit["category"]), spice_lexicon) == "swearing"
        )
    if swear_index_hits:
        month_counts["swear_index_messages"] += 1
        week_counts["swear_index_messages"] += 1
        month_counts["swear_index_occurrences"] += swear_index_occurrences
        week_counts["swear_index_occurrences"] += swear_index_occurrences

    spice_rows.append(
        {
            **{k: v for k, v in record.items() if k != "message"},
            "spice_score": spice_score,
            "spice_groups": ";".join(groups),
            "spice_categories": ";".join(categories),
            "spice_terms": ";".join(terms),
            "spice_occurrences": occurrences,
            "swore": "swearing" in groups,
            "swear_index": bool(swear_index_hits),
            "swear_index_terms": ";".join(sorted({str(hit["term"]) for hit in swear_index_hits})),
            "snippet": make_snippet(record["message"], hits),
        }
    )


def week_key(timestamp: str) -> str:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    year, week, _ = parsed.isocalendar()
    return f"{year}-W{week:02d}"


def make_snippet(message: str, hits: list[dict[str, Any]], window: int = 180) -> str:
    if not hits:
        return message[: window * 2]
    start = max(0, int(hits[0]["first_start"]) - window)
    end = min(len(message), int(hits[0]["first_end"]) + window)
    prefix = "..." if start else ""
    suffix = "..." if end < len(message) else ""
    return prefix + " ".join(message[start:end].split()) + suffix


def write_summary(
    path: Path,
    records: list[dict[str, Any]],
    matched_rows: list[dict[str, Any]],
    spice_rows: list[dict[str, Any]],
    category_messages: Counter[str],
    category_occurrences: Counter[str],
    signal_messages: Counter[str],
    signal_occurrences: Counter[str],
    spice_category_messages: Counter[str],
    spice_category_occurrences: Counter[str],
    spice_group_messages: Counter[str],
    spice_group_occurrences: Counter[str],
    spice_term_messages: Counter[tuple[str, str, str]],
    spice_term_occurrences: Counter[tuple[str, str, str]],
    model_messages: Counter[str],
    model_spicy: Counter[str],
    model_swear: Counter[str],
    model_swear_index: Counter[str],
    term_messages: Counter[tuple[str, str]],
    term_occurrences: Counter[tuple[str, str]],
) -> None:
    total = len(records)
    matched = len(matched_rows)
    swore = spice_group_messages["swearing"]
    swear_index = sum(1 for row in spice_rows if row.get("swear_index"))
    summary = {
        "total_user_messages": total,
        "matched_user_messages": matched,
        "match_rate": round(matched / total, 6) if total else 0,
        "total_term_occurrences": sum(term_occurrences.values()),
        "spice": {
            "spicy_user_messages": len(spice_rows),
            "spicy_message_rate": round(len(spice_rows) / total, 6) if total else 0,
            "swear_index_messages": swear_index,
            "swear_index_message_rate": round(swear_index / total, 6) if total else 0,
            "swear_messages": swore,
            "swear_message_rate": round(swore / total, 6) if total else 0,
            "swear_occurrences": spice_group_occurrences["swearing"],
            "top_spice_groups_by_messages": spice_group_messages.most_common(),
            "top_spice_categories_by_messages": spice_category_messages.most_common(),
            "top_spice_terms_by_messages": [
                {
                    "group": group,
                    "category": category,
                    "term": term,
                    "messages": count,
                    "occurrences": spice_term_occurrences[(group, category, term)],
                }
                for (group, category, term), count in spice_term_messages.most_common(50)
            ],
        },
        "model": {
            "top_models_by_user_messages": [
                {
                    "model_label": label,
                    "messages": count,
                    "message_share": rate(count, total),
                    "spicy_messages": model_spicy[label],
                    "spicy_message_rate": rate(model_spicy[label], count),
                    "swear_index_messages": model_swear_index[label],
                    "swear_index_message_rate": rate(model_swear_index[label], count),
                    "swear_messages": model_swear[label],
                    "swear_message_rate": rate(model_swear[label], count),
                }
                for label, count in model_messages.most_common(25)
            ]
        },
        "date_range": {
            "first_timestamp": min((r.get("timestamp") for r in records if r.get("timestamp")), default=""),
            "last_timestamp": max((r.get("timestamp") for r in records if r.get("timestamp")), default=""),
        },
        "top_categories_by_messages": category_messages.most_common(),
        "top_signals_by_messages": signal_messages.most_common(),
        "top_terms_by_messages": [
            {"category": cat, "term": term, "messages": count, "occurrences": term_occurrences[(cat, term)]}
            for (cat, term), count in term_messages.most_common(50)
        ],
    }
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def write_signal_counts(
    path: Path,
    messages: Counter[str],
    occurrences: Counter[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["signal", "messages", "occurrences"])
        writer.writeheader()
        for signal, count in messages.most_common():
            writer.writerow(
                {
                    "signal": signal,
                    "messages": count,
                    "occurrences": occurrences[signal],
                }
            )


def write_category_counts(
    path: Path,
    messages: Counter[str],
    occurrences: Counter[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "messages", "occurrences"])
        writer.writeheader()
        for category, count in messages.most_common():
            writer.writerow(
                {
                    "category": category,
                    "messages": count,
                    "occurrences": occurrences[category],
                }
            )


def write_term_counts(
    path: Path,
    messages: Counter[tuple[str, str]],
    occurrences: Counter[tuple[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["category", "term", "messages", "occurrences"]
        )
        writer.writeheader()
        for (category, term), count in messages.most_common():
            writer.writerow(
                {
                    "category": category,
                    "term": term,
                    "messages": count,
                    "occurrences": occurrences[(category, term)],
                }
            )


def write_spice_counts(
    path: Path,
    messages: Counter[str],
    occurrences: Counter[str],
    spice_lexicon: dict[str, Any],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["group", "category", "messages", "occurrences", "description"],
        )
        writer.writeheader()
        for category, count in messages.most_common():
            writer.writerow(
                {
                    "group": category_group(category, spice_lexicon),
                    "category": category,
                    "messages": count,
                    "occurrences": occurrences[category],
                    "description": category_description(category, spice_lexicon),
                }
            )


def write_spice_group_counts(
    path: Path,
    messages: Counter[str],
    occurrences: Counter[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["group", "messages", "occurrences"])
        writer.writeheader()
        for group, count in messages.most_common():
            writer.writerow(
                {
                    "group": group,
                    "messages": count,
                    "occurrences": occurrences[group],
                }
            )


def write_spice_term_counts(
    path: Path,
    messages: Counter[tuple[str, str, str]],
    occurrences: Counter[tuple[str, str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["group", "category", "term", "messages", "occurrences"],
        )
        writer.writeheader()
        for (group, category, term), count in messages.most_common():
            writer.writerow(
                {
                    "group": group,
                    "category": category,
                    "term": term,
                    "messages": count,
                    "occurrences": occurrences[(group, category, term)],
                }
            )


def write_month_counts(
    path: Path,
    total_messages: Counter[str],
    matched_messages: Counter[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["month", "total_messages", "matched_messages", "match_rate"]
        )
        writer.writeheader()
        for month in sorted(total_messages):
            total = total_messages[month]
            matched = matched_messages[month]
            writer.writerow(
                {
                    "month": month,
                    "total_messages": total,
                    "matched_messages": matched,
                    "match_rate": round(matched / total, 6) if total else 0,
                }
            )


def write_spice_timeline(
    path: Path,
    period_counts: dict[str, Counter[str]],
    period_field: str,
) -> None:
    category_keys = sorted({
        key
        for counts in period_counts.values()
        for key in counts
        if key.startswith("category:") and key.endswith(":messages")
    })
    group_keys = sorted({
        key
        for counts in period_counts.values()
        for key in counts
        if key.startswith("group:") and key.endswith(":messages")
    })
    dynamic_fields: list[str] = []
    for key in group_keys:
        group = key.split(":", 2)[1]
        dynamic_fields.extend([f"{group}_messages", f"{group}_message_rate"])
    for key in category_keys:
        category = key.split(":", 2)[1]
        dynamic_fields.extend([f"{category}_messages", f"{category}_message_rate"])

    fieldnames = [
        period_field,
        "total_messages",
        "spicy_messages",
        "spicy_message_rate",
        "swear_index_messages",
        "swear_index_message_rate",
        "swear_index_occurrences",
        "swear_index_occurrences_per_100_messages",
        "swear_messages",
        "swear_message_rate",
        "swear_occurrences",
        "swear_occurrences_per_100_messages",
        *dict.fromkeys(dynamic_fields),
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for period in sorted(period_counts):
            counts = period_counts[period]
            total = counts["total_messages"]
            row: dict[str, Any] = {
                period_field: period,
                "total_messages": total,
                "spicy_messages": counts["spicy_messages"],
                "spicy_message_rate": rate(counts["spicy_messages"], total),
                "swear_index_messages": counts["swear_index_messages"],
                "swear_index_message_rate": rate(counts["swear_index_messages"], total),
                "swear_index_occurrences": counts["swear_index_occurrences"],
                "swear_index_occurrences_per_100_messages": per_100(
                    counts["swear_index_occurrences"], total
                ),
                "swear_messages": counts["swear_messages"],
                "swear_message_rate": rate(counts["swear_messages"], total),
                "swear_occurrences": counts["swear_occurrences"],
                "swear_occurrences_per_100_messages": per_100(
                    counts["swear_occurrences"], total
                ),
            }
            for key in group_keys:
                group = key.split(":", 2)[1]
                value = counts[key]
                row[f"{group}_messages"] = value
                row[f"{group}_message_rate"] = rate(value, total)
            for key in category_keys:
                category = key.split(":", 2)[1]
                value = counts[key]
                row[f"{category}_messages"] = value
                row[f"{category}_message_rate"] = rate(value, total)
            writer.writerow(row)


def write_model_counts(
    path: Path,
    model_messages: Counter[str],
    model_spicy: Counter[str],
    model_swear: Counter[str],
    model_swear_index: Counter[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "model_label",
                "messages",
                "message_share",
                "spicy_messages",
                "spicy_message_rate",
                "swear_index_messages",
                "swear_index_message_rate",
                "swear_messages",
                "swear_message_rate",
            ],
        )
        writer.writeheader()
        total = sum(model_messages.values())
        for label, count in model_messages.most_common():
            writer.writerow(
                {
                    "model_label": label,
                    "messages": count,
                    "message_share": rate(count, total),
                    "spicy_messages": model_spicy[label],
                    "spicy_message_rate": rate(model_spicy[label], count),
                    "swear_index_messages": model_swear_index[label],
                    "swear_index_message_rate": rate(model_swear_index[label], count),
                    "swear_messages": model_swear[label],
                    "swear_message_rate": rate(model_swear[label], count),
                }
            )


def write_model_timeline(
    path: Path,
    model_periods: dict[str, Counter[str]],
    spice_periods: dict[str, Counter[str]],
    period_field: str,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                period_field,
                "total_messages",
                "dominant_model",
                "dominant_model_messages",
                "dominant_model_share",
                "second_model",
                "second_model_messages",
                "second_model_share",
                "third_model",
                "third_model_messages",
                "third_model_share",
                "swear_index_messages",
                "swear_index_message_rate",
                "swear_messages",
                "swear_message_rate",
                "spicy_messages",
                "spicy_message_rate",
            ],
        )
        writer.writeheader()
        for period in sorted(model_periods):
            counts = model_periods[period]
            total = sum(counts.values())
            top = counts.most_common(3)
            padded = top + [("", 0)] * (3 - len(top))
            spice_counts = spice_periods.get(period, Counter())
            writer.writerow(
                {
                    period_field: period,
                    "total_messages": total,
                    "dominant_model": padded[0][0],
                    "dominant_model_messages": padded[0][1],
                    "dominant_model_share": rate(padded[0][1], total),
                    "second_model": padded[1][0],
                    "second_model_messages": padded[1][1],
                    "second_model_share": rate(padded[1][1], total),
                    "third_model": padded[2][0],
                    "third_model_messages": padded[2][1],
                    "third_model_share": rate(padded[2][1], total),
                    "swear_index_messages": spice_counts["swear_index_messages"],
                    "swear_index_message_rate": rate(
                        spice_counts["swear_index_messages"], total
                    ),
                    "swear_messages": spice_counts["swear_messages"],
                    "swear_message_rate": rate(spice_counts["swear_messages"], total),
                    "spicy_messages": spice_counts["spicy_messages"],
                    "spicy_message_rate": rate(spice_counts["spicy_messages"], total),
                }
            )


def write_spice_timeline_html(
    path: Path,
    _records: list[dict[str, Any]],
    _monthly_spice: dict[str, Counter[str]],
    weekly_spice: dict[str, Counter[str]],
    _monthly_models: dict[str, Counter[str]],
    weekly_models: dict[str, Counter[str]],
    _model_messages: Counter[str],
    _model_spicy: Counter[str],
    _model_swear: Counter[str],
    spice_term_messages: Counter[tuple[str, str, str]],
    spice_term_occurrences: Counter[tuple[str, str, str]],
    spice_lexicon: dict[str, Any],
    owner_name: str | None,
) -> None:
    weekly = build_html_period_rows(weekly_spice, weekly_models)
    examples = top_swear_index_examples(
        spice_term_messages,
        spice_term_occurrences,
        spice_lexicon,
    )
    title = chart_title(owner_name)

    replacements = {
        "__CHART_TITLE__": html.escape(title),
        "__CHART_SUBTITLE__": html.escape(CHART_SUBTITLE),
        "__CHART_LOGO_DATA_URI__": html.escape(png_data_uri(DEFAULT_LOGO)),
        "__CHART_START_DATE__": HTML_CHART_START_DATE.isoformat(),
        "__WEEKLY_DATA__": json_for_script(weekly),
        "__SWEAR_INDEX_EXAMPLES__": json_for_script(examples),
    }
    rendered = SPICE_TIMELINE_TEMPLATE
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    path.write_text(rendered, encoding="utf-8")


def png_data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def top_swear_index_examples(
    messages: Counter[tuple[str, str, str]],
    occurrences: Counter[tuple[str, str, str]],
    lexicon: dict[str, Any],
    limit: int = 10,
) -> list[dict[str, Any]]:
    by_term_messages: Counter[str] = Counter()
    by_term_occurrences: Counter[str] = Counter()
    excluded = swear_index_excluded_terms(lexicon)
    for (group, _category, term), count in messages.items():
        if not is_swear_index_group(group):
            continue
        if term.casefold() in excluded:
            continue
        by_term_messages[term] += count
        by_term_occurrences[term] += occurrences[(group, _category, term)]
    ranked = sorted(
        by_term_messages,
        key=lambda term: (-by_term_messages[term], -by_term_occurrences[term], term),
    )
    return [
        {
            "term": term,
            "messages": by_term_messages[term],
            "occurrences": by_term_occurrences[term],
        }
        for term in ranked[:limit]
    ]


def build_html_period_rows(
    spice_periods: dict[str, Counter[str]],
    model_periods: dict[str, Counter[str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for period in sorted(spice_periods):
        spice_counts = spice_periods[period]
        total = spice_counts["total_messages"]
        top = model_periods.get(period, Counter()).most_common(3)
        padded = top + [("", 0)] * (3 - len(top))
        date_label, date_range = period_date_text(period)
        start_date, end_date = period_bounds(period)
        rows.append(
            {
                "label": period,
                "dateLabel": date_label,
                "dateRange": date_range,
                "startDate": start_date.isoformat() if start_date else "",
                "endDate": end_date.isoformat() if end_date else "",
                "monthKey": f"{start_date.year}-{start_date.month:02d}" if start_date else "",
                "total": total,
                "models": [
                    {"label": label or "unknown", "messages": count}
                    for label, count in model_periods.get(period, Counter()).most_common()
                ],
                "spicyMessages": spice_counts["spicy_messages"],
                "spicyRate": rate(spice_counts["spicy_messages"], total),
                "swearIndexMessages": spice_counts["swear_index_messages"],
                "swearIndexRate": rate(spice_counts["swear_index_messages"], total),
                "swearIndexPer100": per_100(
                    spice_counts["swear_index_occurrences"], total
                ),
                "swearMessages": spice_counts["swear_messages"],
                "swearRate": rate(spice_counts["swear_messages"], total),
                "swearPer100": per_100(spice_counts["swear_occurrences"], total),
                "calloutRate": rate(spice_counts["group:callout:messages"], total),
                "emotionRate": rate(spice_counts["group:emotion_spike:messages"], total),
                "dominantModel": padded[0][0] or "unknown",
                "dominantModelMessages": padded[0][1],
                "dominantModelShare": rate(padded[0][1], total),
                "secondModel": padded[1][0],
                "secondModelMessages": padded[1][1],
                "secondModelShare": rate(padded[1][1], total),
                "thirdModel": padded[2][0],
                "thirdModelMessages": padded[2][1],
                "thirdModelShare": rate(padded[2][1], total),
            }
        )
    return rows


def json_for_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


MONTH_ABBREVIATIONS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def period_date_text(period: str) -> tuple[str, str]:
    start, end = period_bounds(period)
    if start and end and "-W" in period:
        return short_date(start), date_range_text(start, end)
    if start and "-W" not in period:
        return f"{MONTH_ABBREVIATIONS[start.month - 1]} {start.year}", period
    return period, period


def period_bounds(period: str) -> tuple[date | None, date | None]:
    if "-W" in period:
        try:
            year_text, week_text = period.split("-W", 1)
            start = date.fromisocalendar(int(year_text), int(week_text), 1)
        except ValueError:
            return None, None
        return start, start + timedelta(days=6)
    try:
        parsed = datetime.strptime(period, "%Y-%m")
    except ValueError:
        return None, None
    start = parsed.date()
    if start.month == 12:
        end = date(start.year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(start.year, start.month + 1, 1) - timedelta(days=1)
    return start, end


def short_date(value: date) -> str:
    return f"{MONTH_ABBREVIATIONS[value.month - 1]} {value.day}"


def date_range_text(start: date, end: date) -> str:
    if start.year == end.year and start.month == end.month:
        return f"{short_date(start)}-{end.day}, {start.year}"
    if start.year == end.year:
        return f"{short_date(start)}-{short_date(end)}, {start.year}"
    return f"{short_date(start)}, {start.year}-{short_date(end)}, {end.year}"


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def per_100(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 3) if denominator else 0.0


def write_matched_messages(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "id",
        "timestamp",
        "score",
        "categories",
        "signals",
        "terms",
        "occurrences",
        "thread_id",
        "title",
        "cwd",
        "model_label",
        "model",
        "reasoning_effort",
        "source_path",
        "line_number",
        "turn_index",
        "char_count",
        "word_count",
        "snippet",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_spice_messages(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "id",
        "timestamp",
        "spice_score",
        "spice_groups",
        "spice_categories",
        "spice_terms",
        "spice_occurrences",
        "swore",
        "swear_index",
        "swear_index_terms",
        "thread_id",
        "title",
        "cwd",
        "model_label",
        "model",
        "reasoning_effort",
        "source_path",
        "line_number",
        "turn_index",
        "char_count",
        "word_count",
        "snippet",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_review_samples(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Review Samples",
        "",
        "Highest-scoring matched user turns for manual lexicon review.",
        "These snippets are local corpus artifacts and should not be committed or published.",
        "",
    ]
    for index, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"## {index}. score {row['score']} | {row.get('timestamp', '')}",
                "",
                f"- categories: `{row.get('categories', '')}`",
                f"- signals: `{row.get('signals', '')}`",
                f"- terms: `{row.get('terms', '')}`",
                f"- model: `{row.get('model_label', '')}`",
                f"- title: `{row.get('title', '')}`",
                f"- cwd: `{row.get('cwd', '')}`",
                "",
                f"> {row.get('snippet', '').replace(chr(10), ' ')}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_spice_samples(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Spice Samples",
        "",
        "Highest-scoring spicy user turns for local review.",
        "These snippets are local corpus artifacts and should not be committed or published.",
        "",
    ]
    for index, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"## {index}. spice {row['spice_score']} | {row.get('timestamp', '')}",
                "",
                f"- groups: `{row.get('spice_groups', '')}`",
                f"- categories: `{row.get('spice_categories', '')}`",
                f"- terms: `{row.get('spice_terms', '')}`",
                f"- swore: `{row.get('swore', '')}`",
                f"- swear index: `{row.get('swear_index', '')}`",
                f"- model: `{row.get('model_label', '')}`",
                f"- title: `{row.get('title', '')}`",
                f"- cwd: `{row.get('cwd', '')}`",
                "",
                f"> {row.get('snippet', '').replace(chr(10), ' ')}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_candidate_phrases(
    path: Path,
    records: list[dict[str, Any]],
    matched_rows: list[dict[str, Any]],
    limit: int = 200,
    max_chars: int = 1000,
) -> None:
    matched_ids = {row["id"] for row in matched_rows}
    all_counts: Counter[str] = Counter()
    matched_counts: Counter[str] = Counter()

    for record in records:
        # Phrase discovery is meant to suggest human-review terms. Long prompts,
        # pasted plans, and benchmark artifacts drown that signal, so keep this
        # to compact turns by default.
        if int(record.get("char_count") or 0) > max_chars:
            continue
        tokens = [
            token.lower().strip("'")
            for token in TOKEN_RE.findall(record["message"])
            if token.lower().strip("'") not in STOPWORDS and len(token) > 2
        ]
        phrases = list(iter_ngrams(tokens, 1)) + list(iter_ngrams(tokens, 2)) + list(iter_ngrams(tokens, 3))
        unique_phrases = set(phrases)
        all_counts.update(unique_phrases)
        if record["id"] in matched_ids:
            matched_counts.update(unique_phrases)

    rows = []
    for phrase, matched_count in matched_counts.items():
        total_count = all_counts[phrase]
        if matched_count < 3:
            continue
        specificity = matched_count / total_count if total_count else 0
        rows.append(
            {
                "phrase": phrase,
                "matched_messages": matched_count,
                "all_messages": total_count,
                "specificity": round(specificity, 4),
            }
        )

    rows.sort(key=lambda row: (-row["specificity"], -row["matched_messages"], row["phrase"]))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["phrase", "matched_messages", "all_messages", "specificity"]
        )
        writer.writeheader()
        writer.writerows(rows[:limit])


def iter_ngrams(tokens: list[str], n: int) -> Iterable[str]:
    if len(tokens) < n:
        return
    for index in range(0, len(tokens) - n + 1):
        phrase = " ".join(tokens[index : index + n])
        if phrase:
            yield phrase


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def record_comparison_key(record: dict[str, Any]) -> tuple[str, str, str]:
    message = " ".join(str(record.get("message") or "").split())
    return (
        str(record.get("thread_id") or ""),
        str(record.get("timestamp") or ""),
        message,
    )


def diff_new_records(
    current_records: list[dict[str, Any]],
    previous_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    previous_keys = {record_comparison_key(record) for record in previous_records}
    return [
        record
        for record in current_records
        if record_comparison_key(record) not in previous_keys
    ]


def timestamp_range(records: list[dict[str, Any]]) -> dict[str, str]:
    timestamps = [
        str(record.get("timestamp") or "") for record in records if record.get("timestamp")
    ]
    return {
        "first_timestamp": min(timestamps, default=""),
        "last_timestamp": max(timestamps, default=""),
    }


def count_messages_on_utc_day(records: list[dict[str, Any]], day: str) -> int:
    return sum(1 for record in records if str(record.get("timestamp") or "").startswith(day))


def write_incremental_status(
    path: Path,
    previous_records: list[dict[str, Any]],
    current_records: list[dict[str, Any]],
    new_records: list[dict[str, Any]],
    baseline_messages_path: Path,
    delta_messages_path: Path,
    delta_analysis_dir: Path,
    *,
    analysis_skipped: bool,
) -> None:
    today_utc = datetime.now(timezone.utc).date().isoformat()
    status = {
        "baseline_messages_path": str(baseline_messages_path),
        "delta_messages_path": str(delta_messages_path),
        "delta_analysis_dir": str(delta_analysis_dir),
        "analysis_skipped": analysis_skipped,
        "needs_refresh": bool(new_records),
        "baseline_user_messages": len(previous_records),
        "current_user_messages": len(current_records),
        "new_user_messages": len(new_records),
        "today_utc": today_utc,
        "baseline_messages_today_utc": count_messages_on_utc_day(previous_records, today_utc),
        "current_messages_today_utc": count_messages_on_utc_day(current_records, today_utc),
        "new_messages_today_utc": count_messages_on_utc_day(new_records, today_utc),
        "baseline_date_range": timestamp_range(previous_records),
        "current_date_range": timestamp_range(current_records),
        "new_date_range": timestamp_range(new_records),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")


def clear_incremental_analysis_outputs(delta_dir: Path) -> None:
    derived_names = {
        "summary.json",
        "matched_messages.csv",
        "spice_messages.csv",
        "spice_term_counts.csv",
        "spice_category_counts.csv",
        "spice_group_counts.csv",
        "spice_timeline_weekly.csv",
        "spice_timeline_monthly.csv",
        "spice-timeline.html",
        "model_counts.csv",
        "model_timeline_weekly.csv",
        "model_timeline_monthly.csv",
        "category_counts.csv",
        "signal_counts.csv",
        "term_counts.csv",
        "candidate_phrases.csv",
    }
    for name in derived_names:
        path = delta_dir / name
        if path.exists():
            path.unlink()
