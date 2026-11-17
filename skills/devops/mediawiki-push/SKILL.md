---
name: mediawiki-push
description: Push content (pages, files) to a MediaWiki wiki — authentication, tokens, form-based edits, file uploads, and MW-version-specific quirks. Covers both API and form-post paths.
---

# mediawiki-push

Push wiki pages and files to a MediaWiki instance. Covers authentication, token acquisition, edit/create via API and form-post, file uploads, and version-specific quirks.

## When to use

Any task that writes to a MediaWiki wiki: creating pages, updating content, uploading files, importing XML, or verifying recent changes.

## Core workflow

### 1. Discover the wiki

```
# Basic info
curl -sk "https://<wiki>/api.php?action=query&meta=siteinfo&format=json"
# Returns: generator (MW version), server, mainpage, time, read-only flag

# Check existing pages
curl -sk "https://<wiki>/api.php?action=query&list=allpages&aplimit=50&apprefix=<prefix>&format=json"

# Check if a specific page exists
curl -sk "https://<wiki>/api.php?action=query&titles=<Page_Title>&prop=info&format=json"
# Look for "missing" key in response → page doesn't exist
```

### 2. SSL handling

Many internal/self-hosted wikis use self-signed certs. In Python, use an unverified context **for this host only**:

```python
import ssl
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
```

Pass `context=CTX` to every `urllib.request.urlopen()` call. Do NOT disable verification globally.

### 3. Authentication

**MW 1.23.x (and some later configs): form-based login is often the only working path.**

The API `action=login` with `lgtoken=+` frequently returns `WrongToken` or `NeedToken` because the token module isn't wired for API login on these installs.

**Form-based login procedure:**

```python
# Step 1: GET the login form to extract wpLoginToken
login_form_url = f"{WIKI_INDEX}?title=Special:UserLogin&action=edit&type=login&uselang=en"
html, status = get(login_form_url)
wpLoginToken = extract_token(html, "wpLoginToken")  # hidden field value
# If not found, the form may not render it — try fetching again or check for redirects

# Step 2: POST to submitlogin
login_submit_url = f"{WIKI_INDEX}?title=Special:UserLogin&action=submitlogin&type=login"
fields = {
    "wpName": username,
    "wpPassword": password,
    "wpRemember": "1",
    "wpLoginAttempt": "Log in",
    "wpLoginToken": wpLoginToken,
    "title": "Special:UserLogin",
}
html_after, status_after = post(login_submit_url, fields)
# Check response title and body for success indicators:
#   "log in successfully", "Successfully logged in", "You are now logged in"
#   OR "incorrect", "error", "failed", "password"
```

**Verify login succeeded:**

```python
# After login, query userinfo via API
d = api_get({"action":"query","meta":"userinfo","uiprop":"groups|rights|name","format":"json"})
ui = d["query"]["userinfo"]
print(ui["id"], ui["name"], ui["groups"], ui["rights"])
# id > 0 and "edit" in rights → authenticated and can edit
```

### 4. Getting an edit token

**This is the tricky part and varies by MW version and config.**

**MW 1.27+:** `action=query&meta=tokens&type=csrf&format=json` returns `csrftoken`. Works reliably.

**MW 1.23.x (e.g. fhsws002.ksfraser.com/ksfp/bagpipes_wiki):**
- `action=query&meta=tokens` returns `"Unrecognized value for parameter 'meta': tokens"` — module not supported.
- `action=query&prop=info&intoken=edit` on a page returns empty `tokens: {}` and a warning `"Action 'edit' is not allowed for the current user"` for anonymous users.
- After form login, the edit form HTML (`index.php?title=Page&action=edit`) often has an **empty** `wpEditToken` hidden field — no token rendered.
- API `action=edit` with `token=+` returns `badtoken` even after login.

**What this means in practice for MW 1.23.x after form login:**
The form-post edit path (`action=submit`) is the viable route, but it also needs a valid token. If `wpEditToken` is empty in the rendered form, investigate:
- Whether session cookies are being sent with the edit-form request (use a CookieJar that persists across the login → edit-form fetch → edit-submit chain).
- Whether the wiki renders the token only for certain user groups or under certain conditions.
- Whether a fresh login-form fetch after authentication yields a usable token.

**If tokens cannot be obtained**, fall back to:
- Direct form POST with the fields the live edit form uses (capture them via regex on the edit-form HTML).
- Using `token=+` and testing whether this specific wiki accepts it (some do, some don't — test, don't assume).

### 5. Editing pages

**API path (works when a valid token is available):**

```python
api_post({
    "action": "edit",
    "title": page_title,
    "text": content,
    "token": valid_token,
    "summary": edit_summary,
    "format": "json",
    "createonly": "0",  # "1" to fail if page exists
    "bot": "0",
})
# Response: {"edit": {"result": "Success", "pageid": N, "newrevid": M}}
# Or: {"error": {"code": "notoken"|"badtoken"|"protectedtitle", "info": "..."}}
```

**Form-post path (action=submit):**

```python
# Capture the live edit form's field names first
edit_html = get(f"{WIKI_INDEX}?title={title}&action=edit&uselang=en")[0]
field_names = re.findall(r'<(?:input|textarea|select)[^>]*name="([^"]*)"', edit_html)
# Typical fields: wpEditToken, wpTextbox1, wpSummary, wpSave, wpPreview,
#   wpDiff, wpWatchthis, wpMinoredit, wpAntispam, wpSection, wpStarttime,
#   wpEdittime, oldid, format, model, fulltext, go, search, title

# Submit with the fields
fields = {
    "wpEditToken": token_or("+"),
    "wpTextbox1": content,
    "wpSummary": edit_summary,
    "wpSave": "Save page",
    "wpWatchthis": "watch",  # or "nochange"
    "wpMinoredit": "",
    "wpDiff": "",
    "oldid": "0",
    "preview": "0",
    "title": title.replace(" ", "_"),
    "action": "submit",
    "section": "0",
    "wpStarttime": str(int(time.time() * 1000)),
    "wpEdittime": "",
    "fulltext": "1",
    "model": "wikitext",
    "format": "wikitext",
}
url = f"{WIKI_INDEX}?title={quote(title.replace(' ','_'))}&action=submit&uselang=en"
html, status = post(url, fields)
# Check response: look for "return to <title>", "successfully", "saved"
# vs "editconflict", "blocked", "badtoken", "permissions"
```

**Response interpretation:**

| Response pattern | Meaning |
|---|---|
| "return to <Page Title>" or "successfully saved" | Edit succeeded |
| "Creating <Page Title> - WikiName" | Page didn't exist; form returned the create view (edit may or may not have saved — verify via API) |
| "Edit conflict" / "editconflict" | Another edit happened concurrently |
| "blocked" / "limited to users in the group" | Permission denied |
| "badtoken" / "invalid token" | Token invalid or expired |
| "permissions errors" | Auth required |

**Always verify after editing** by querying the page via API:

```python
d = api_get({"action":"query","titles":title,"prop":"info|revisions","rvlimit":1,"format":"json"})
pgs = d["query"]["pages"]
for pid, p in pgs.items():
    if "missing" in p:
        print("  MISSING — edit did not create the page")
    else:
        rev = p.get("revisions", [{}])[0]
        print(f"  EXISTS pageid={p.get('pageid')} revid={rev.get('revid')} by={rev.get('user')} text_len={len(rev.get('*', ''))}")
```

### 6. File uploads

**Via Special:Upload form (MW 1.23.x):**

```python
# Build multipart form
boundary = "----UploadBoundary" + uuid.uuid4().hex[:8]
body = b""
# Regular fields
for k, v in {
    "wpEditToken": token,
    "wpIgnoreWarning": "1",
    "wpUploadDescription": "Upload description",
    "wpDestFile": "filename.odt",
    "title": "Special:Upload",
}.items():
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
    body += f"{v}\r\n".encode()
# File field — name varies: wpUploadFile, file, upload
body += f"--{boundary}\r\n".encode()
body += f'Content-Disposition: form-data; name="wpUploadFile"; filename="{fn}"\r\n'.encode()
body += b"Content-Type: application/vnd.oasis.opendocument.text\r\n\r\n"
body += fdata + b"\r\n"
body += f"--{boundary}--\r\n".encode()

url = f"{WIKI_INDEX}?title=Special:Upload&action=submit&uselang=en"
req = urllib.request.Request(url, data=body, method="POST",
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
             "User-Agent": "HermesAgent/1.0"})
with opener.open(req, timeout=60) as r:
    html = r.read().decode()
# Check for "File:<name>" or "uploaded successfully" in response
```

**Upload field names vary by MW version.** Common names: `wpUploadFile`, `file`, `upload`. Inspect the Special:Upload form HTML to find the actual field name.

**Verify upload via API:**

```python
d = api_get({"action":"query","titles":"File:<name>","prop":"imageinfo",
             "iiprop":"url|size|timestamp|user|mime","format":"json"})
# Look for "missing" → upload didn't work
# Else: ii = p["imageinfo"][0]; ii["url"], ii["size"], ii["user"], ii["timestamp"]
```

### 7. Importing XML

For bulk page creation, use `action=import`:

```python
# First upload the XML to a temporary location or pass as POST body
api_post({
    "action": "import",
    "interwiki": "json",
    "namespace": "0",
    "from": "https://.../export.xml",  # or upload XML and reference
    "token": valid_token,
    "format": "json",
    "summary": "Import from X",
})
```

Alternatively, upload the XML file to the wiki's `Special:Upload` and then import. MW 1.23.x may have limitations on import sources.

## MediaWiki content generation (absorbed from `wiki-content-delivery`)

Generate and stage content for MediaWiki in three formats before pushing.

### ODF (.odt) generation without LibreOffice

When the host has no `soffice`/`libreoffice` binary, assemble a valid .odt by hand as a ZIP with 7 parts:

1. `mimetype` — `application/vnd.oasis.opendocument.text`, **stored uncompressed** (ZIP_STORED), **first entry** in the zip.
2. `content.xml` — body with `office:document-content` root; namespace declarations: `xmlns:office`, `xmlns:style`, `xmlns:text`, `xmlns:table`, `xmlns:draw`, `xmlns:fo`, `xmlns:svg`, `xmlns:meta`, `xmlns:dc`, plus `office:version="1.2"`. Inject each xmlns exactly once — duplicating any produces "duplicate attribute" XML parse errors.
3. `META-INF/manifest.xml` — lists parts and media types.
4. `settings.xml` — minimal `office:document-settings`.
5. `meta.xml` — `office:meta` with dc:title, dc:creator, dc:date, dc:subject, dc:description.
6. `styles.xml` — `office:document-styles` with at least default paragraph style + Heading1/2/3.
7. `Thumbnails/thumbnail.png` — a real non-empty PNG. A 1×1 white PNG (57 bytes) satisfies strict validators; a zero-byte thumbnail is technically valid per ODF spec but some tools reject it.

**Content.xml structure:** `office:body > office:text` containing `text:p`, `text:h` (with `text:outline-level` 0/1/2 for H1/H2/H3), `text:list` + `text:list-item` for bullet lists, and `table:table` + `table:table-row` + `table:table-cell` for tables. Escape `&`, `<`, `>` in text content with `html.escape`.

**Validation after write:**
```python
import zipfile, xml.etree.ElementTree as ET
z = zipfile.ZipFile(path)
assert z.infolist()[0].filename == 'mimetype' and z.infolist()[0].compress_type == 0
assert z.read('mimetype').decode().strip() == 'application/vnd.oasis.opendocument.text'
ET.fromstring(z.read('content.xml'))   # raises on invalid XML
assert z.read('Thumbnails/thumbnail.png')[:8] == b'\x89PNG\r\n\x1a\n'
```
If `ET.fromstring` raises "duplicate attribute" → some xmlns was injected twice. Find and remove the duplication.

**Pitfall — p-tag splitting across page breaks:** when assembling the body by joining paragraph strings, the first H1 should have `fo:break-before="page"` so content starts on a fresh page. Add a paragraph style variant with that property and apply it to the first heading.

### MediaWiki XML generation

Build an export-0.10-style XML with:
- `<siteinfo>` — sitename, base URL, generator, namespaces (at least -2..1).
- One `<page>` per wiki page, each with `<title>`, `<ns>`, optional `<restriction>`, and a `<revision>` containing `<id>`, `<timestamp>`, `<contributor>`, `<comment>`, `<text xml:space="preserve">`.

Page naming conventions (project-specific):
- Overview page: `Pipe_Band_Music_Proficiency`
- Level pages: `Pipe_Band_Training:_Level_N_Segment` where Segment ∈ {Pipes, Drums, Snare, BassTenor}
- Quick reference: `Pipe_Band_Training:_EO_PO_Quick_Reference`
- File description page: `Media:Pipe_Band_EO_PO_Checklists.odt`

**Important:** the MediaWiki XML is useful even if you can't import it. Each page's text is self-contained wiki markup — you can paste it directly into the wiki editor by hand. Always generate both the XML (for automation when credentials exist) and keep the per-page markdown text (for manual paste fallback).

### Building the MediaWiki import file from a markdown master

When the master source is one big markdown file with `== Page: <title> ==` section dividers:

1. Split on the `== Page: ... ==` markers (and the `## Overview page: \`<title>\`` marker for the first page if present).
2. Strip the divider line + following blank line from each page's text.
3. Map each display title to the wiki page name (namespace-prefixed, spaces→underscores).
4. For level pages, parse "Level N — Instrument" → `Pipe_Band_Training:_Level_N_Segment`. Watch for em dashes (U+2014) and other Unicode dash chars — normalize them to `-` before regex matching, otherwise the match silently fails and the page gets skipped.
5. Write the XML.

### ODF as a file-upload to the wiki

The .odt should be uploaded to the wiki's file store so `[[Media:Pipe_Band_EO_PO_Checklists.odt]]` links resolve. MW upload: `action=upload` with `filename`, `file` (multipart), `comment`, `ignorewarnings=true`. Requires edit token OR a logged-in session. Same permission gate as edit.

### Pitfalls

- **Do not push before verifying permissions.** Writing the push script and running it against an anon-blocked wiki produces `notoken`/`badtoken`/permissions-error noise. Check `uiprop=groups|rights` first and stop cleanly if blocked, delivering only the files.
- **MW version matters for tokens.** `meta=tokens` works on 1.24+, not on 1.23. The wiki's `generator` field tells you which. Parameterize your token-strategy on the version.
- **Self-signed cert breaks `curl` too.** `curl -k` (or `--insecure`) bypasses it; in Python, unverified SSL context. Don't treat "curl fails" as "wiki is down" — test with `-k` first.
- **ODF mimetype must be first AND stored uncompressed.** A compressed mimetype or wrong order makes the file unreadable by strict ODF consumers.
- **Empty thumbnail.** Generate a real 1×1 PNG (57 bytes) instead of a zero-byte file.
- **Duplicate xmlns.** Inject namespace declarations exactly once on the root element.
- **Em dashes in page titles break title parsing.** Normalize Unicode dash chars to `-` before splitting/section matching, or the regex silently fails to match the section header.

- **MW 1.23.x has no `meta=tokens` API module.** Don't rely on `action=query&meta=tokens`. Use form-based login + form-based edits, or investigate the token situation after login.
- **`token=+` is not universally accepted.** Some wikis reject it with `badtoken`. Test on a throwaway page first. If it fails, you need a real token from the edit form HTML (if one is rendered) or from the login flow.
- **Empty wpEditToken in edit form after login.** This is a known situation on some MW 1.23 configs. Investigate session cookie propagation, fresh token fetch, or whether the wiki renders tokens only for certain groups.
- **Self-signed certs.** Always use a per-host unverified SSL context in Python. Don't disable verification globally.
- **Form field names vary by MW version.** Always inspect the live form HTML (edit form, upload form) to get the actual field names. Don't hardcode `wpUploadFile` — verify it exists in the form.
- **Cookies must persist across the auth → edit chain.** Use a CookieJar that's shared between the login POST, the edit-form GET, and the edit-submit POST. If cookies are lost between steps, the edit form won't render a token and the submit will fail.
- **"Creating Page - Wiki" response from form submit.** This doesn't necessarily mean the edit failed — it might mean the page didn't exist and the form returned the creation view. **Always verify** by querying the page via API afterward.
- **API edit after form login may still reject token=+.** The form login establishes a session (cookies) but doesn't necessarily make the API token endpoint work. If API edit fails after login, try the form-post path instead.

## References

- `references/mw_1.23_token_investigation.md` — session-specific findings from the fhsws002.ksfraser.com bagpipes wiki auth probe (what worked, what didn't, exact field names, response patterns).
