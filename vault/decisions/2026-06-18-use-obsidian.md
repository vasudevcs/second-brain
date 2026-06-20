---
type: decision
date: 2026-06-18
project: second-brain
title: Use Obsidian as the primary capture interface
status: accepted
reason: Already in daily use. Markdown files are portable and version-controllable. Avoids building a custom frontend before the intelligence layer exists.
outcome:
tags:
  - architecture
  - obsidian
---

## Context
Needed a note-writing interface for daily engineering capture. Options were a
custom web dashboard, a CLI-only system, or Obsidian.

## Options Considered
- Custom web dashboard — maximum control, high build cost, distraction from core goal
- CLI-only system — fast to build, poor for long-form writing
- Obsidian — already in use, markdown portable, graph view included

## Chosen Option
Obsidian

## Rationale
Building a frontend would consume time better spent on the intelligence layer.
Obsidian's YAML frontmatter support aligns directly with the ingestion pipeline.
Markdown files are plain text — no vendor lock-in, survives any future tool change.

## Actual Outcome
