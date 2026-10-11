# Deck Refresh — Updating Numbers Across Existing Presentations

Updates a presentation with new numbers — quarterly refreshes, earnings updates, comp rolls, rebased market data. Use whenever the user asks to "update the deck with Q4 numbers", "refresh the comps", "roll this forward", "swap in the new earnings", or any request to swap figures across an existing deck without rebuilding it.

## Environment Check

- **Add-in** — the deck is open live; edit text runs, table cells, and chart data directly.
- **Chat** — the deck is an uploaded file; edit by regenerating affected slides.

Either way: smallest possible change, existing formatting stays intact.

This is a four-phase process and Phase 3 is an approval gate.

## Phase 1 — Get the Data

Ask the user how the new numbers are arriving:
- **Pasted mapping** — user types or pastes "revenue $485M → $512M, EBITDA $120M → $135M"
- **Uploaded Excel** — old/new columns, or a fresh output sheet
- **Just the new values** — "Q4 revenue was $512M, margins were 22%"

Also ask about **derived numbers**: if revenue moves, does the user want growth rates and share percentages recalculated?

## Phase 2 — Read Everything, Find Everything

Read every slide. For each old value, find every instance — including the ones that don't look the same:

| Variant | Example |
|---------|---------|
| Scale | `$485M`, `$0.485B`, `$485,000,000` |
| Precision | `$485M`, `$485.0M`, `~$485M` |
| Unit style | `$485M`, `$485MM`, `$485 million`, `485M` |
| Embedded | "revenue grew to $485M", axis labels |

**Where numbers hide:**
- Text boxes, table cells, chart data labels and axis labels
- Chart source data — the numbers driving the bars
- Footnotes, source lines, small print

Build a list: for each old value, every location, exact text, and what it'll become.

## Phase 3 — Present the Plan, Get Approval

Show the full change list before editing. Include:
- Old → new value mappings
- Every slide/location where each value appears
- Flagged derived numbers that may need recalculation

Use `ask_user_question` for approval: proceed, proceed but skip flagged items, or revise mapping first.

## Phase 4 — Execute, Preserve, Report

- **Text in a shape** — change value, leave font/size/color/bold state
- **Table cell** — change cell, leave table alone
- **Chart data** — update underlying series values so bars/lines move

After the last edit, report what happened and flag any derived numbers that still need manual review.

Run visual verification — a number that got longer might overflow its text box.

## What You're Not Doing

- **Not rebuilding slides** — if narrative no longer makes sense, flag it
- **Not recalculating unless asked** — derived numbers are the user's call
- **Not touching formatting** — match the deck's existing style
