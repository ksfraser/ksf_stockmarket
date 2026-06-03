<?php
/**
 * Upload page — drag-and-drop file upload + upload history.
 */
$history = $data['history'] ?? [];
$results = $data['results'] ?? [];
$errors  = $data['errors'] ?? [];
$error   = $data['error'] ?? '';
?>

<!-- Upload Form -->
<div class="card">
    <div class="card-header">&#x1F4E4; Upload Statements &amp; Transaction Files</div>
    <p style="font-size:0.85em;color:var(--text3);margin-bottom:12px;">
        Supported: PDF (CIBC Investor's Edge, Questrade, BMO), CSV (Questrade export, generic). Max 100MB per file.
        Files are processed immediately and deleted — nothing is stored long-term.
    </p>

    <?php if ($error): ?>
        <div style="background:#3a1a1a;border:1px solid #5a2a2a;padding:10px 14px;border-radius:6px;margin-bottom:12px;color:#a44;">
            &#x274C; <?php echo htmlspecialchars($error); ?>
        </div>
    <?php endif; ?>

    <form method="POST" action="?action=upload" enctype="multipart/form-data" id="uploadForm">
        <div id="dropZone" style="border:2px dashed var(--border);border-radius:8px;padding:30px;text-align:center;cursor:pointer;background:var(--bg2);transition:border-color 0.2s;">
            <div style="font-size:2em;margin-bottom:8px;">&#x1F4C1;</div>
            <div style="color:var(--text3);font-size:0.9em;">Drag &amp; drop files here, or click to browse</div>
            <div style="color:var(--text3);font-size:0.75em;margin-top:4px;">PDF, CSV, TXT — up to 100MB each</div>
        </div>
        <div id="fileList" style="margin-top:10px;"></div>
        <div style="margin-top:12px;">
            <button type="button" id="uploadBtn" onclick="submitFiles()" disabled style="padding:8px 24px;background:var(--accent);color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:600;opacity:0.5;">&#x1F4E4; Upload &amp; Process</button>
            <span id="uploadStatus" style="margin-left:12px;font-size:0.85em;color:var(--text3);"></span>
        </div>
    </form>
</div>

<!-- Processing Results -->
<div id="uploadResults" class="card" style="<?php echo (empty($results) && empty($errors)) ? 'display:none;' : ''; ?>">
    <div class="card-header">&#x1F4CB; Upload Results</div>
    <?php if (!empty($results) || !empty($errors)): ?>
    <?php foreach ($results as $r): ?>
        <div style="margin-bottom:8px;padding:10px;border-radius:6px;background:<?php echo ($r['status'] ?? '') === 'error' ? '#3a1a1a' : '#1a3a1a'; ?>;border:1px solid <?php echo ($r['status'] ?? '') === 'error' ? '#5a2a2a' : '#2a5a2a'; ?>;">
            <strong><?php echo htmlspecialchars($r['filename']); ?></strong>
            <?php if (($r['status'] ?? '') === 'processed'): ?>
                <span style="color:#4a4;">&#x2705; Processed</span>
                <span style="color:var(--text3);font-size:0.85em;">
                    — <?php echo $r['format'] ?? 'unknown'; ?>,
                    <?php echo $r['parsed']; ?> parsed,
                    <?php echo $r['imported']; ?> imported,
                    <?php echo $r['skipped']; ?> skipped
                </span>
                <?php if (!empty($r['note'])): ?>
                    <div style="color:#aa4;font-size:0.8em;margin-top:4px;">&#x26A0;&#xFE0F; <?php echo htmlspecialchars($r['note']); ?></div>
                <?php endif; ?>
                <?php if (!empty($r['suspicious_lines']) || !empty($r['text_preview'])): ?>
                    <details style="margin-top:6px;font-size:0.8em;">
                        <summary style="cursor:pointer;color:var(--text3);">&#x1F50D; Debug: extracted text preview</summary>
                        <?php if (!empty($r['text_preview'])): ?>
                            <pre style="background:var(--bg1);border:1px solid var(--border);padding:8px;margin-top:4px;max-height:200px;overflow:auto;white-space:pre-wrap;font-size:0.75em;color:var(--text3);"><?php echo htmlspecialchars($r['text_preview']); ?></pre>
                        <?php endif; ?>
                        <?php if (!empty($r['suspicious_lines'])): ?>
                            <div style="margin-top:4px;color:var(--text3);">Lines with dates + amounts (potential transactions):</div>
                            <?php foreach ($r['suspicious_lines'] as $sl): ?>
                                <pre style="background:var(--bg1);border:1px solid var(--border);padding:4px 8px;margin-top:2px;font-size:0.75em;color:#aa4;white-space:pre-wrap;"><?php echo htmlspecialchars($sl); ?></pre>
                            <?php endforeach; ?>
                        <?php endif; ?>
                    </details>
                <?php endif; ?>
            <?php else: ?>
                <span style="color:#a44;">&#x274C; Error</span>
                <span style="color:var(--text3);font-size:0.85em;"> — <?php echo htmlspecialchars($r['error'] ?? 'Unknown error'); ?></span>
            <?php endif; ?>
        </div>
    <?php endforeach; ?>
    <?php foreach ($errors as $e): ?>
        <div style="margin-bottom:8px;padding:10px;border-radius:6px;background:#3a1a1a;border:1px solid #5a2a2a;">
            <strong><?php echo htmlspecialchars($e['filename']); ?></strong>
            <span style="color:#a44;">&#x274C; <?php echo htmlspecialchars($e['error']); ?></span>
        </div>
    <?php endforeach; ?>
    <?php endif; ?>
</div>

<!-- Upload History (from upload_log table) -->
<div class="card" id="historyCard">
    <div class="card-header">&#x1F4C5; Upload History</div>
    <?php if (empty($history)): ?>
        <p class="text-muted">No uploads yet.</p>
    <?php else: ?>
    <table style="font-size:0.85em;">
        <thead>
            <tr>
                <th>File</th>
                <th>Size</th>
                <th>Status</th>
                <th>Format</th>
                <th>Parsed</th>
                <th>Imported</th>
                <th>Error</th>
                <th>Time</th>
                <th>Date</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($history as $h): ?>
            <tr>
                <td><strong><?php echo htmlspecialchars($h['original_filename']); ?></strong></td>
                <td class="r"><?php
                    $sz = $h['file_size']; $u = ['B','KB','MB','GB']; $i = 0;
                    while ($sz >= 1024 && $i < 3) { $sz /= 1024; $i++; }
                    echo round($sz,1) . ' ' . $u[$i];
                ?></td>
                <td>
                    <?php
                    $statusColors = ['processed' => '#4a4', 'error' => '#a44', 'partial' => '#aa4', 'processing' => '#888'];
                    $sc = $statusColors[$h['status']] ?? '#888';
                    ?>
                    <span style="color:<?php echo $sc; ?>;"><?php echo strtoupper($h['status']); ?></span>
                </td>
                <td style="color:var(--text3);"><?php echo htmlspecialchars($h['detected_format'] ?? '—'); ?></td>
                <td class="r"><?php echo (int)$h['rows_parsed']; ?></td>
                <td class="r"><?php echo (int)$h['rows_imported']; ?></td>
                <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#a44;font-size:0.85em;">
                    <?php echo htmlspecialchars($h['error_message'] ?? ''); ?>
                </td>
                <td class="r" style="color:var(--text3);">
                    <?php echo $h['processing_time_ms'] ? $h['processing_time_ms'] . 'ms' : '—'; ?>
                </td>
                <td style="color:var(--text3);"><?php echo date('Y-m-d H:i', strtotime($h['created_at'])); ?></td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
    <?php endif; ?>
</div>

<script>
const dropZone = document.getElementById('dropZone');
const fileList  = document.getElementById('fileList');
const uploadBtn = document.getElementById('uploadBtn');
const uploadStatus = document.getElementById('uploadStatus');
let selectedFiles = [];

function handleFiles(files) {
    selectedFiles = [...selectedFiles, ...Array.from(files)];
    renderFileList();
}

function renderFileList() {
    fileList.innerHTML = '';
    if (!selectedFiles.length) {
        uploadBtn.disabled = true; uploadBtn.style.opacity = '0.5';
        return;
    }
    uploadBtn.disabled = false; uploadBtn.style.opacity = '1';
    selectedFiles.forEach((f, i) => {
        const div = document.createElement('div');
        div.style.cssText = 'padding:6px 10px;background:var(--bg2);border:1px solid var(--border);border-radius:4px;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center;';
        const sizeKB = (f.size / 1024).toFixed(0);
        div.innerHTML = '<span>' + f.name + ' <span style="color:var(--text3);font-size:0.8em;">(' + sizeKB + ' KB)</span></span><button type="button" onclick="removeFile(' + i + ')" style="background:none;border:none;color:#a44;cursor:pointer;font-size:1.2em;">&times;</button>';
        fileList.appendChild(div);
    });
}

function removeFile(idx) {
    selectedFiles.splice(idx, 1);
    renderFileList();
}

async function submitFiles() {
    if (!selectedFiles.length) return;
    uploadBtn.disabled = true;
    uploadStatus.textContent = 'Uploading...';

    const fd = new FormData();
    selectedFiles.forEach(f => fd.append('documents[]', f, f.name));

    try {
        const resp = await fetch('?action=upload', { method: 'POST', body: fd });
        if (resp.ok) {
            const html = await resp.text();
            // Parse the response and replace only the results area, not the whole document
            const parser = new DOMParser();
            const newDoc = parser.parseFromString(html, 'text/html');

            // Update results card
            const newResults = newDoc.querySelector('#uploadResults');
            const existingResults = document.querySelector('#uploadResults');

            if (newResults && existingResults) {
                existingResults.replaceWith(newResults);
            }

            // Update history card
            const newHistory = newDoc.querySelector('#historyCard');
            const existingHistory = document.querySelector('#historyCard');
            if (newHistory && existingHistory) {
                existingHistory.replaceWith(newHistory);
            }

            // Clear file list and reset
            selectedFiles = [];
            renderFileList();
            uploadStatus.textContent = '';
        } else {
            uploadStatus.textContent = 'Upload failed (HTTP ' + resp.status + ')';
            uploadBtn.disabled = false;
        }
    } catch (err) {
        uploadStatus.textContent = 'Upload error: ' + err.message;
        uploadBtn.disabled = false;
    }
}

dropZone.addEventListener('click', () => {
    const inp = document.createElement('input');
    inp.type = 'file'; inp.multiple = true;
    inp.accept = '.pdf,.csv,.txt';
    inp.style.display = 'none';
    inp.addEventListener('change', () => { handleFiles(inp.files); inp.remove(); });
    document.body.appendChild(inp);
    inp.click();
});

dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.borderColor = 'var(--accent)'; });
dropZone.addEventListener('dragleave', () => { dropZone.style.borderColor = 'var(--border)'; });
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--border)';
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
});
</script>
