# OCR Vision-Model Fallback (when local Tesseract hangs)

## When to use

- `pdftotext` returns 0 lines (no embedded text — confirmed scanned)
- `pdfimages -list` returns no embedded raster images
- `tesseract <rendered.png> out` hangs or returns 0 bytes
- The OCR container is unavailable / unhealthy
- You need text quickly and can't restart the container pipeline

## The recipe (copy-paste)

### 1. Render + combine pages with pymupdf + PIL

```python
from PIL import Image
import fitz, os, glob

pdfs = sorted(glob.glob('/path/to/pdfs/*.pdf'))
for f in pdfs:
    base = os.path.splitext(os.path.basename(f))[0]
    doc = fitz.open(f)
    pages = []
    for i in range(len(doc)):
        # Matrix(1.0, 1.0) is the sweet spot. Lower may miss text,
        # higher can blow past the vision model's input limit on tall pages.
        pix = doc[i].get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
        path = f'/tmp/{os.getpid()}_{i}.png'
        pix.save(path)
        pages.append(Image.open(path))
    doc.close()
    if not pages:
        continue
    total_h = sum(p.height for p in pages)
    max_w = max(p.width for p in pages)
    combined = Image.new('RGB', (max_w, total_h), 'white')
    y = 0
    for p in pages:
        combined.paste(p, (0, y))
        y += p.height
    combined.save(f'/path/to/combined/{base}.png')
```

### 2. Call vision_analyze on each combined PNG

```python
# One call per combined image. For a 2-page PDF, one call returns
# both pages. The vision model handles tall images well up to ~7000px.
import hermes_tools as ht
text = ht.vision_analyze(
    image_url=f'/path/to/combined/{base}.png',
    question='Extract ALL text from this scanned document image. Return every word exactly as it appears, preserving structure, numbering, and formatting.'
)
```

Or from the main tool surface:
```
vision_analyze(image_url='/path/to/combined/<filename>.png',
               question='Extract ALL text...')
```

### 3. Optional: batch all calls in parallel (delegate_task)

For 20+ PDFs, spawn a single leaf subagent that runs the render+OCR loop
in its own context window and returns the consolidated text. Saves
the parent context from 20+ vision responses.

## Why this works when tesseract doesn't

- The vision model is a multimodal transformer — it doesn't have
  tesseract's layout-analysis loops that go into spin on pathological
  PDF rasterizations
- Combining pages vertically (rather than tiling horizontally) keeps
  page order, which preserves document structure in the response
- White background fill at composite time avoids edge artifacts at
  page boundaries

## Tools/paths verified on this host

- `python3.10` (not `python3` — pymupdf installed for 3.10 only)
- `import fitz` (PyMuPDF 1.27.x)
- `from PIL import Image` (Pillow)
- `vision_analyze` (Hermes top-level tool — accepts local file paths)
- Combined images up to ~7000px tall render fine; 9-page PDFs
  (7128px) completed in one call

## Things that DON'T work (don't waste time here)

- `gs -q -dNOPAUSE -dBATCH -sDEVICE=pngalpha -r150 ...` → fails
  on easyPDF PDFs with `/undefinedfilename in --findlibfile--`
  (remove `-q` to get a working gs, but the resulting PNG still
  makes tesseract hang)
- `pdftoppm -png -r 100` → produces PNG, but tesseract still hangs
  on it (the hang is about the rendered content, not the renderer)
- `tesseract --psm 6` / `--oem 1` / stdin / grayscale conversion →
  still hangs, same content
- `tesseract` at very low render scale (Matrix 0.5x) → completes
  but with 0 bytes of text (text too small at 0.5x)

## Known good sources this technique has been verified against

- Canadian Cadet pipe band POs (A-CR-CCP-911/PG-001) — all 25
  scanned PDFs OCR'd cleanly (POs 113S–319 + 1STech–5STech)
- Any scanned PDF where tesseract hangs but `fitz.open()` renders
  without error is a candidate
