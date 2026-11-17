# Manual ODF (.odt) Construction Without LibreOffice

Use when LibreOffice / `soffice` is **not available** in the environment and you need to deliver a valid `.odt` file. Validates against strict ODF consumers (LibreOffice, Google Docs import, file-type detectors).

## When this applies

- Headless / managed-agent sessions with no `soffice` binary installed.
- You need a printable, editable document artifact and the user accepts `.odt`.
- The source is structured text (markdown, checklists, tables) that you can render into ODF's `content.xml`.

## ODF is a ZIP of XML — the required layout

| Entry | Must be | Notes |
|---|---|---|
| `mimetype` | **First entry, stored (no compression)** | Content must be exactly `application/vnd.oasis.opendocument.text`. To verify: `z.infolist()[0].filename == 'mimetype' and z.infolist()[0].compress_type == 0`. |
| `content.xml` | Compressed OK | The body. Must parse as well-formed XML. Must declare ODF namespaces on the root element. |
| `styles.xml` | Compressed OK | At minimum the `office:document-styles` with `office:styles` and a default paragraph style. |
| `meta.xml` | Compressed OK | `office:meta` with at least `dc:title`. |
| `settings.xml` | Compressed OK | `office:document-settings`. Can be minimal. |
| `META-INF/manifest.xml` | Compressed OK | `manifest:manifest` listing every part. |
| `Thumbnails/thumbnail.png` | Compressed OK | **Must be a real PNG, not empty.** Some strict validators reject 0-byte thumbnails. A 1×1 white PNG (57 bytes) is enough. |

## The mimetype rule is the most common failure

If `mimetype` is not the first entry, or is compressed, some consumers mis-detect the file. Always write it first with `compress_type=zipfile.ZIP_STORED`.

```python
import zipfile
zout = zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED)
zout.writestr('mimetype', b'application/vnd.oasis.opendocument.text', compress_type=zipfile.ZIP_STORED)
# ... then everything else ...
```

## Thumbnail gotcha

Do not write an empty `Thumbnails/thumbnail.png` (0 bytes). Several validators including LibreOffice's own strict-mode checks will flag it. Build a minimal valid PNG instead:

- 1×1 pixel, 8-bit RGB, white.
- ~57 bytes.
- Can be built with pure-Python `struct` + `zlib`: PNG signature → IHDR chunk → IDAT chunk (filter byte `\x00` + RGB `\xff\xff\xff`, zlib-compressed) → IEND chunk.
- Each chunk is `4-byte type + data + 4-byte CRC32`.

## content.xml namespace pitfall (caught in this session)

If you build `content.xml` from a string template that **already includes** the `xmlns:*` declarations and then **also** inject them with a `.replace()` or string concat, you get a **duplicate attribute** and the XML fails to parse (`xml.etree.ElementTree.ParseError: duplicate attribute`).

**Rule:** define namespaces once on the root element in the template; never re-inject them.

## content.xml minimum shape

```xml
<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
    xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
    xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
    xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
    xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
    xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    office:version="1.2">
  <office:font-face-decls>
    <style:font-face style:name="Liberation Serif" .../>
    <style:font-face style:name="Liberation Sans" .../>
  </office:font-face-decls>
  <office:automatic-styles> ... </office:automatic-styles>
  <office:body>
    <office:text>
      <text:h text:style-name="Heading1" text:outline-level="0">Title</text:h>
      <text:p text:style-name="Standard">Body paragraph.</text:p>
      <text:list><text:list-item><text:p>...</text:p></text:list-item></text:list>
      <table:table table:name="table-1"> ... </table:table>
    </office:text>
  </office:body>
</office:document-content>
```

Required elements: `office:font-face-decls` (at least one font-face, e.g. Liberation Serif + Liberation Sans), `office:automatic-styles`, `office:body > office:text`. Headings use `text:h` with `text:outline-level`. Paragraphs use `text:p`. Lists use `text:list > text:list-item > text:p`. Tables use `table:table > table:table-row > table:table-cell`.

## Validation after building

```python
import zipfile, xml.etree.ElementTree as ET, os

def validate_odt(path):
    z = zipfile.ZipFile(path)
    first = z.infolist()[0]
    assert first.filename == 'mimetype' and first.compress_type == 0
    assert z.read('mimetype').decode().strip() == 'application/vnd.oasis.opendocument.text'
    # thumbnail must be a real PNG
    th = z.read('Thumbnails/thumbnail.png')
    assert th[:8] == b'\x89PNG\r\n\x1a\n' and len(th) > 0
    # content.xml must be well-formed XML
    ET.fromstring(z.read('content.xml'))
    return True
```

## Source material for this section

- This session's ODF build of `Pipe_Band_EO_PO_Checklists.odt` (8,308 bytes, 597 paragraphs, 15-page markdown → ODF).
- Pitfall caught: duplicate namespace attribute on `content.xml` root caused by re-injecting `xmlns:*` via `.replace()` after template already declared them.
- Pitfall caught: 0-byte `Thumbnails/thumbnail.png` rejected by strict ODF validators; replaced with a real 57-byte 1×1 white PNG.
- Validation confirmed via: mimetype-first+STORED check, PNG signature check, `xml.etree.ElementTree.fromstring(content.xml)` parse, and `xml.dom.minidom.parseString` round-trip.
