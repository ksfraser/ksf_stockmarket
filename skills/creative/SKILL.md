---
name: creative-media
description: "Class-level umbrella for creative content generation: ASCII art, infographics, comics, animations, generative art, music, and text humanization."
tags: [ascii-art, infographic, comic, animation, manim, p5js, gen-art, pixel-art, comfyui, music, songwriting, humanizer, pretext, visual-design]
---

# Creative Media

Class-level umbrella for creative content generation: ASCII art, infographics, comics, animations, generative art, pixel art, music, text humanization, and creative browser demos.

## 1) ASCII Art — `ascii-art`

ASCII art and ASCII media: banners, text art, image-to-ASCII, and ASCII video with audio (ascii-video).

## 2) Infographics — `baoyu-infographic`

Infographics: 21 layouts x 21 styles (信息图, 可视化).

## 3) Knowledge Comics — `baoyu-comic`

Knowledge comics (知识漫画): educational, biography, tutorial.

## 4) Image/Video/Audio Generation — `comfyui`

Generate images, video, and audio with ComfyUI — install, launch, manage nodes/models, run workflows with parameter injection. Uses the official comfy-cli for lifecycle and direct REST/WebSocket API for execution.

## 5) Text Humanization — `humanizer`

Humanize text: strip AI-isms and add real voice.

## 6) Animations — `manim-video`

Manim CE animations: 3Blue1Brown math/algo videos.

## 7) Generative Art — `p5js`

p5.js sketches: generative art, shaders, interactive, 3D.

## 8) Pixel Art — `pixel-art`

Pixel art w/ era palettes (NES, Game Boy, PICO-8).

## 9) Creative Browser Demos — `pretext`

Build creative browser demos with @chenglou/pretext — DOM-free text layout for ASCII art, typographic flow around obstacles, text-as-geometry games, kinetic typography, and text-powered generative art. Produces single-file HTML demos by default.

## 10) Songwriting & AI Music — `songwriting-and-ai-music`

Songwriting craft and Suno AI music prompts.

## 11) Idea Generation — `ideation`

Generate project ideas via creative constraints.

## 12) Visual & UI Design — `visual-design`

Class-level skill for visual and UI output: architecture diagrams, hand-drawn Excalidraw diagrams, design-system HTML artifacts (Claude, Vercel, Stripe, Linear, etc.), design-token specs, and reference templates from popular web design systems.

## Rules

1. Prefer local generation (ComfyUI, Manim, p5.js) over cloud APIs when the workflow supports it.
2. Always check model/node dependencies before launching ComfyUI workflows.
3. Use era palettes for pixel art to maintain stylistic consistency.
