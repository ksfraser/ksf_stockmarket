---
name: visual-design
description: "Class-level skill for visual and UI output: architecture diagrams, hand-drawn Excalidraw diagrams, design-system HTML artifacts (Claude, Vercel, Stripe, Linear, etc.), design-token specs, and reference templates from popular web design systems."
tags: [visual-design, architecture-diagram, excalidraw, claude-design, popular-web-designs, design-md, html, css, layout, diagram]
related_skills: [ascii-art, p5js, manim-video, sketch, design-md]
license: MIT
version: 1.0.0
author: Hermes Agent
platforms: [linux, macos, windows]
---

# Visual Design

Class-level skill for creating and copying visual/UI content: architecture diagrams, hand-drawn drafts, and design-system HTML artifacts.

## Trigger conditions

Use this skill for:

- Generating clear, layered architecture or cloud diagrams (SVG/HTML)
- Creating hand-drawn, sketch-style visual content (Excalidraw JSON)
- Building one-off design-system implementations in self-contained HTML (claude-design)
- Replicating popular design systems as reference HTML/CSS (popular-web-designs)
- Converting Figma-style design-token definitions into workable specs (design-md)
- Selecting a reference design system for a mockup or prototype

Select the subsection below that matches the target medium.

## 1) Architecture diagrams

Generate dark-themed, layered SVG/HTML diagrams: cloud, infra, network, or component views.

**Guiding rules**
- Use the darkest, near-black background; no pastel colors — deep navy/dark earth accents only
- Build from bottom-left (foundation) to top-right (clients)
- Consistent component sizing, rounded corners, neutral containers
- Start from `templates/template.html` and extend it

## 2) Excalidraw hand-drawn diagrams

Create sketch-style drafts in Excalidraw JSON format.

**Guiding rules**
- Default theme: light canvas, dark (#1e1e1e) strokes
- Use `rectangle`, `ellipse`, `arrow`, `text`, and `line` primitives
- Rough, hand-drawn feel is the point — straight lines get slight random offsets
- Group related elements and label cleanly
- Upload via `scripts/upload.py` if a running Excalidraw instance is available

**Color reference** — `references/colors.md`.
**Mode reference** — `references/dark-mode.md`.
**Example reference** — `references/examples.md`.

## 3) Claude-style design system (claude-design)

Implement Anthropic's warm, editorial "literary salon" aesthetic as a self-contained HTML page.

**Guiding rules**
- Background: parchment (`#f5f4ed`) — not white, not off-white
- Serif headlines with tight line-height (1.10–1.30)
- Terracotta brand accent (`#c96442`) — the sole "color"
- Every gray has a warm yellow-brown undertone; zero cool blue-grays
- Ring-based shadows (`0px 0px 0px 1px`) for depth without visible borders
- Magazine-like pacing: generous section spacing, serif-driven hierarchy

## 4) Popular web design systems (popular-web-designs)

Use `templates/<design>.md` as reference. Each template file is a condensed implementation guide with layout, color, and typography rules for that design system (Stripe, Vercel, Linear, Airbnb, Apple, etc.).

**Workflow**
1. Pick the reference matching the request (or ask to browse `templates/`)
2. Read the chosen `templates/<design>.md`
3. Replicate the visual system in HTML/CSS — follow the vendor's spacing, shadow, type conventions

## 5) Design tokens (design-md)

Author or validate DESIGN.md token spec files.

**When to use**
- Converting Figma/Sketch exports into executable design tokens
- Documenting color, spacing, type, and shadow scales in machine-readable form
- Validating a token file against the DESIGN.md token spec

**Starter** — `templates/starter.md`.

## References & assets

- `references/colors.md` — Excalidraw color palette
- `references/dark-mode.md` — Excalidraw dark theme guidance
- `references/examples.md` — Excalidraw example architectures
- `templates/template.html` — base architecture diagram HTML
- `templates/claude.md` — Claude design system reference
- `templates/<design>.md` — 40+ popular web design systems
- `templates/starter.md` — DESIGN.md token spec starter
- `scripts/upload.py` — Excalidraw JSON upload helper
