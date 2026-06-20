---
type: mistake
date: 2026-06-18
project: second-brain
title: Session template had corrupted frontmatter
category: process
severity: minor
time_lost_mins: 15
recurrence: 0
tags:
  - templates
  - frontmatter
---

## What Happened
The session.md template had a plain-text template block prepended before
the YAML frontmatter delimiter. Because the file did not start with ---,
python-frontmatter parsed the entire file as body text and ignored the
YAML block entirely.

## Root Cause
The old plain-text template was not deleted before the new YAML-based
template was added. Both versions coexisted in the same file.

## Fix Applied
Deleted lines 1-16 of session.md so the file now begins with ---.
Verified with python-frontmatter that all fields parse correctly.

## Lesson Learned
When replacing a template format, delete the old version entirely before
writing the new one. Never append a new format to an existing file.
