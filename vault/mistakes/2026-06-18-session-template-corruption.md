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

engineering_pattern: Modified producer without validating consumer

beginner_explanation: >
  A template is a form that a program fills in. The program reading the form
  expects it to start in a specific way. The old form was left at the top of the
  file and the new form was added below it. The program saw the old form first,
  got confused, and ignored everything after it.

real_world_analogy: >
  A teacher hands out an exam paper with two sets of instructions stapled together.
  Students follow the first set of instructions, which are outdated and wrong.
  The correct instructions are on page two, but students never reach them because
  they already started following the wrong ones.

warning_signs:
  - Changed the format of a file that another program reads
  - Did not delete the old version before adding the new version
  - Did not test whether the reading program could still parse the file
  - File had content before the opening --- delimiter

prevention_checklist:
  - Verify the file starts with --- before saving
  - Run the parser on the file immediately after any format change
  - Run the ingestion pipeline after updating any template
  - Delete old format entirely before writing new format
  - Check parser output matches expected fields
---

## What Happened

The session.md template had the old plain-text template block at the top of the
file. The new YAML frontmatter block was added below it instead of replacing it.
Because the file did not start with ---, python-frontmatter treated the entire
file as body text and returned empty metadata for every field.

## Root Cause

The old template was not deleted before the new format was written. Both versions
were in the same file. The reading program (python-frontmatter) only recognises
frontmatter if the file starts with ---. When it does not, it silently ignores
all YAML fields and returns nothing.

## Fix Applied

Deleted lines 1 through 16 of session.md, which contained the old plain-text
template. The file now begins with --- and all frontmatter fields parse correctly.

## Lesson Learned

When replacing a template format, delete the old version entirely before writing
the new one. After any change to a template or file format, immediately test that
the reading program can still parse it correctly.
