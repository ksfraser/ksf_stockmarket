---
name: research
description: "Research workflows: paper writing, knowledge management, prediction market queries, and strategy research agents."
tags: [research, paper, knowledge-management, wiki, obsidian, polymarket, prediction-markets, stockmarket-research]
---

# Research

Class-level umbrella for research workflows: academic paper production, knowledge management, prediction market data, and strategy research agents.

## 1) Paper Writing — `research-paper-writing`

End-to-end academic paper production with LaTeX templates for NeurIPS, ICML, ICLR, COLM, AAAI, and ACL. Covers methodology, citation workflows, human evaluation, and reviewer guidelines.

References: 8 files covering methodology, checklists, citations, experiments, evaluation, paper types, reviewer guidelines, sources.
Templates: 6 conference directories with `.tex`, `.bib`, `.bst`, `.sty`, and `README.md` files.
Scripts: `search_arxiv.py` for arXiv queries.
Full end-to-end writing guide (absorbed from the former `research-paper-writing` skill): `references/paper-writing-guide.md`.

## 2) Knowledge Management — `knowledge-management`

Build, query, and synchronize knowledge bases: markdown wikis with bidirectional links, Obsidian vault management, and MediaWiki publishing/sync.

Key operations: read/write/search Obsidian vaults; maintain `[[Note Name]]` link indexes; publish/sync with internal MediaWiki.

## 3) Prediction Markets — `polymarket`

Query Polymarket read-only REST APIs (Gamma, CLOB, Data). No auth required.

Workflow: search → parse events/markets → present prices as percentages → deep dive with orderbooks/history.

References: `references/api-endpoints.md` for full endpoint reference with curl examples.
Scripts: `scripts/polymarket.py` for API interaction.

## 4) Strategy Research Agent — `stockmarket-research-agent`

Generates daily research briefs from internal MariaDB data (ATR sweep, eval scores, fundamentals) and external sources (Reddit, arXiv, YouTube/Apify transcripts). LLM-backed scoring via configurable providers.

Modes: internal, external, both. Outputs to `memory/institutional/research-brief-YYYY-MM-DD.{md,json}`.

References: LLM providers, external auth, deployment gotchas, YouTube strategy agent.
Workdir: `/var/www/stockmarket-app/`.

## Rules

1. Never hardcode derived model values; keep assumptions first.
2. Always scan source content for API keys/tokens before including in outputs.
3. Prefer structured JSON extraction from YouTube transcripts; validate against schema.
