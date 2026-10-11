---
name: data-science
description: "Iterative Python exploration, PDF ingestion, OCR fallback, and notebook-based REPL workflows."
tags: [jupyter, notebook, repl, data-science, exploration, iterative, pdf, ocr, tesseract, fitz]
---

# Data Science

Class-level umbrella for data science workflows: live notebook exploration, PDF ingestion, and OCR pipelines.

## 1) Live Jupyter Kernel — `jupyter-live-kernel`

Stateful Python REPL via a live Jupyter kernel. Variables persist across executions. Use instead of `execute_code` when you need iterative exploration, state across steps, or complex data inspection.

Prerequisites: `uv`, `jupyterlab`. Uses `hamelnb` script for server/kernel management.

Workflow: discover servers → execute code with `--compact` → inspect variables → edit cells → restart-run-all for verification.

Pitfalls: first execution may timeout; kernel Python must have all packages installed; argument order matters for subcommands; occasional websocket timeouts retry once.

## 2) PDF/OCR Pipeline — `pdf-ocr-pipeline`

Robust PDF ingestion: prefer `fitz` text extraction, fall back to local Tesseract OCR via FastAPI container when text is empty or `force_ocr=True`.

Canonical pattern: extract text → auto-fallback to OCR → env-driven config for OCR host/port/timeout.

Pitfalls: `fitz.get_text()` does not perform OCR; don't pass raw PDFs to LLMs for OCR; `podman-compose` profiles vary by version; make OCR fallback opt-in.

## Rules

1. Prefer live Jupyter for iterative exploration; use `execute_code` for one-shot scripts needing tool access.
2. Always keep OCR fallback failure-driven, not as the hot path.
3. Store OCR container config in `.env`, not hardcoded.

## Pitfall: local Tesseract hangs on certain scanned PDFs

Some scanned PDFs (e.g. those produced by **easyPDF Printer Driver / BCL easyPDF** with vector-rendered text and no embedded text/raster) cause local Tesseract to enter an extended processing loop that exceeds any practical timeout. Symptoms:
- `pdftotext` returns 0 lines (confirmed scanned, no text layer)
- `pdfimages -list` returns no embedded raster images
- `pymupdf` / `ghostscript` / `pdftoppm` all render the pages successfully (PNG produced, file size reasonable)
- `tesseract image.png out` hangs indefinitely (no output, no error, output file 0 bytes if killed)
- The hang is **resolution-dependent** — tesseract may complete at very low render scales (e.g. pymupdf `Matrix(0.5, 0.5)`) but hang at 1.0x and above

**Fallback when local Tesseract hangs:** use the vision model via `vision_analyze` on the rendered PNG. This is the most reliable path for tricky scans.
- Render pages with `pymupdf` (not `ghostscript -q` — that fails on easyPDF PDFs with `/undefinedfilename in --findlibfile--`)
- For multi-page PDFs, combine all pages into one tall PIL image first (paste vertically) so a single `vision_analyze` call returns the full document text
- Render at 1.0x scale (`fitz.Matrix(1.0, 1.0)`) — large enough that the vision model can read the text, small enough to stay under the model's input limit

See `references/ocr-vision-fallback.md` for a copy-paste recipe.
