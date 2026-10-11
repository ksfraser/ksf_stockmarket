# OCR API Contract

## Endpoint

`POST /ocr`

## Request

- Content-Type: `multipart/form-data`
- Field: `file` (binary)
- Accepts: `image/*` in the sample app, but the ingestion helper sends `application/pdf` when posting PDFs from parsers.py.

## Response

Success `200`:

```json
{
  "text": "extracted text here",
  "filename": "uploaded.pdf"
}
```

Error `400`/`500`:

```json
{
  "detail": "error message"
}
```

## Client resolution order in `ocr_pdf()`

1. JSON field `text`
2. JSON field `data`
3. Raw response text (`resp.text`)

## Timeouts

Default `OCR_TIMEOUT=60`. For large scanned statements, prefer `120` to avoid upload/processing race conditions.
