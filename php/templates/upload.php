<?php
/**
 * Document Upload page — PDF/CSV upload form with drag-and-drop.
 *
 * Data:
 *   $history  — array of import history from transactions.source_file
 *   $results  — array of parse results (after POST)
 *   $errors   — array of error messages (after POST)
 *   $error    — string error message
 */
$history  = $data['history'] ?? [];
$results  = $data['results'] ?? [];
$errors   = $data['errors'] ?? [];
$formError = $data['error'] ?? null;
$maxSize  = '100MB';
$allowed  = 'PDF, CSV, TXT';
?>
<div class="card" style="margin-bottom:24px;">
    <div class="card-header">&#x1F4E4; Upload Account Statements &amp; Transaction Files</div>
    <p style="margin-bottom:16px;">
        Upload PDF account statements (CIBC Investor's Edge, Questrade, etc.) or CSV transaction exports directly.
        Files are parsed and imported into the transactions table automatically.
        <strong>No email needed</strong> — bypass the 25MB Gmail attachment limit entirely.
    </p>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:16px;">
        <div style="background:rgba(104,211,145,0.1);border:1px solid rgba(104,211,145,0.3);padding:14px;border-radius:var(--radius);">
            <div style="font-size:0.75em;text-transform:uppercase;color:var(--green);margin-bottom:6px;">&#x2705; Supported</div>
            <ul style="margin:0 0 0 16px;font-size:0.85em;line-height:1.8;">
                <li>PDF account statements (any brokerage)</li>
                <li>CSV transaction exports</li>
                <li>Multi-file upload</li>
                <li>Max file size: <strong><?= $maxSize ?></strong></li>
                <li>Allowed: <strong><?= $allowed ?></strong></li>
            </ul>
        </div>
        <div style="background:rgba(237,137,54,0.1);border:1px solid rgba(237,137,54,0.3);padding:14px;border-radius:var(--radius);">
            <div style="font-size:0.75em;text-transform:uppercase;color:var(--orange);margin-bottom:6px;">&#x26A0;&#xFE0F; How It Works</div>
            <ol style="margin:0 0 0 16px;font-size:0.85em;line-height:1.8;">
                <li>Drag &amp; drop files or click to browse</li>
                <li>Files are uploaded to the server</li>
                <li>PDFs: text extracted, transactions parsed</li>
                <li>CSVs: auto-detected format (CIBC, Questrade, generic)</li>
                <li>New transactions inserted (duplicates skipped)</li>
            </ol>
        </div>
    </div>

    <?php if ($formError): ?>
    <div style="background:rgba(252,129,129,0.1);border:1px solid rgba(252,129,129,0.3);padding:12px;border-radius:var(--radius);margin-bottom:16px;color:var(--red);">
        &#x274C; <?= htmlspecialchars($formError) ?>
    </div>
    <?php endif; ?>

    <form method="POST" action="?action=upload&subaction=process" enctype="multipart/form-data" id="uploadForm">
        <input type="hidden" name="MAX_FILE_SIZE" value="104857600">

        <!-- Drop zone -->
        <div id="dropZone" style="border:2px dashed var(--border);border-radius:var(--radius);padding:40px;text-align:center;cursor:pointer;transition:all 0.2s;background:rgba(0,0,0,0.1);"
             ondragover="event.preventDefault();this.style.borderColor='var(--accent)';this.style.background='rgba(99,179,237,0.1)'"
             ondragleave="this.style.borderColor='var(--border)';this.style.background='rgba(0,0,0,0.1)'"
             ondrop="handleDrop(event)"
             onclick="document.getElementById('fileInput').click()">

            <div style="font-size:3em;margin-bottom:12px;">&#x1F4E5;</div>
            <div style="font-size:1.1em;margin-bottom:8px;"><strong>Drop files here</strong> or click to browse</div>
            <div style="font-size:0.8em;color:var(--text3);">
                PDF, CSV, TXT — up to <?= $maxSize ?> each — multiple files OK
            </div>
        </div>

        <input type="file" name="documents[]" id="fileInput" multiple
               accept=".pdf,.csv,.txt"
               style="display:none"
               onchange="handleFiles(this.files)">

        <!-- File list -->
        <div id="fileList" style="margin-top:16px;"></div>

        <!-- Upload button -->
        <div style="margin-top:20px;text-align:center;">
            <button type="submit" class="btn" id="uploadBtn" style="padding:12px 32px;font-size:1em;" disabled>
                &#x1F4E4; Upload &amp; Process Files
            </button>
            <div id="uploadProgress" style="display:none;margin-top:12px;">
                <div style="background:rgba(0,0,0,0.2);border-radius:8px;height:8px;overflow:hidden;">
                    <div id="progressBar" style="background:var(--accent);height:100%;width:0%;transition:width 0.3s;"></div>
                </div>
                <div id="progressText" style="font-size:0.8em;color:var(--text3);margin-top:4px;"></div>
            </div>
        </div>
    </form>

    <script>
    function handleDrop(e) {
        e.preventDefault();
        e.currentTarget.style.borderColor = 'var(--border)';
        e.currentTarget.style.background = 'rgba(0,0,0,0.1)';
        handleFiles(e.dataTransfer.files);
    }

    function handleFiles(files) {
        const list = document.getElementById('fileList');
        const input = document.getElementById('fileInput');
        const btn = document.getElementById('uploadBtn');

        // Build new file list
        const dt = new DataTransfer();
        // Keep existing files
        for (let i = 0; i < input.files.length; i++) {
            dt.items.add(input.files[i]);
        }
        // Add new files
        for (let i = 0; i < files.length; i++) {
            dt.items.add(files[i]);
        }
        input.files = dt.files;

        renderFileList(input.files);
        btn.disabled = input.files.length === 0;
    }

    function renderFileList(files) {
        const list = document.getElementById('fileList');
        if (files.length === 0) { list.innerHTML = ''; return; }

        let html = '<div style="font-size:0.75em;text-transform:uppercase;color:var(--text3);margin-bottom:8px;">' + files.length + ' file(s) selected</div>';
        html += '<div style="display:flex;flex-direction:column;gap:8px;">';

        for (let i = 0; i < files.length; i++) {
            const size = formatSize(files[i].size);
            const ext = files[i].name.split('.').pop().toLowerCase();
            const extColor = ext === 'pdf' ? 'var(--red)' : (ext === 'csv' ? 'var(--green)' : 'var(--accent)');
            html += '<div style="display:flex;align-items:center;gap:12px;background:rgba(0,0,0,0.1);padding:10px 14px;border-radius:var(--radius);">';
            html += '<span style="background:' + extColor + ';color:#fff;padding:2px 8px;border-radius:4px;font-size:0.7em;font-weight:700;">' + ext.toUpperCase() + '</span>';
            html += '<span style="flex:1;font-size:0.9em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + files[i].name + '</span>';
            html += '<span style="font-size:0.75em;color:var(--text3);">' + size + '</span>';
            html += '<span style="cursor:pointer;color:var(--red);font-size:1.2em;" onclick="removeFile(' + i + ')">&#x2715;</span>';
            html += '</div>';
        }
        html += '</div>';
        list.innerHTML = html;
    }

    function removeFile(idx) {
        const input = document.getElementById('fileInput');
        const dt = new DataTransfer();
        for (let i = 0; i < input.files.length; i++) {
            if (i !== idx) dt.items.add(input.files[i]);
        }
        input.files = dt.files;
        renderFileList(input.files);
        document.getElementById('uploadBtn').disabled = input.files.length === 0;
    }

    function formatSize(bytes) {
        const units = ['B','KB','MB','GB'];
        let i = 0;
        while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
        return bytes.toFixed(1) + ' ' + units[i];
    }

    // Form submit progress simulation
    document.getElementById('uploadForm').addEventListener('submit', function() {
        const btn = document.getElementById('uploadBtn');
        const prog = document.getElementById('uploadProgress');
        const bar = document.getElementById('progressBar');
        const txt = document.getElementById('progressText');
        btn.disabled = true;
        btn.textContent = 'Uploading...';
        prog.style.display = 'block';
        let pct = 0;
        const interval = setInterval(function() {
            pct += Math.random() * 15;
            if (pct > 95) pct = 95;
            bar.style.width = pct + '%';
            txt.textContent = Math.round(pct) + '% — processing...';
        }, 500);
    });
    </script>
</div>

<!-- Upload Results (shown after POST) -->
<?php if (!empty($results) || !empty($errors)): ?>
<div class="card" style="margin-top:24px;">
    <div class="card-header">&#x1F4CB; Upload Results</div>

    <?php if (!empty($errors)): ?>
    <div style="background:rgba(252,129,129,0.1);border:1px solid rgba(252,129,129,0.3);padding:14px;border-radius:var(--radius);margin-bottom:16px;">
        <div style="font-size:0.75em;text-transform:uppercase;color:var(--red);margin-bottom:8px;">&#x274C; Errors</div>
        <ul style="margin:0 0 0 20px;font-size:0.85em;color:var(--red);line-height:1.8;">
            <?php foreach ($errors as $err): ?>
            <li><?= htmlspecialchars($err) ?></li>
            <?php endforeach; ?>
        </ul>
    </div>
    <?php endif; ?>

    <?php foreach ($results as $r): ?>
    <div style="background:rgba(0,0,0,0.1);border-left:3px solid var(--green);padding:12px 16px;border-radius:0 var(--radius) var(--radius) 0;margin-bottom:12px;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
            <span style="font-weight:700;"><?= htmlspecialchars($r['filename']) ?></span>
            <span style="background:rgba(99,179,237,0.2);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:0.7em;"><?= strtoupper($r['type']) ?></span>
            <span style="font-size:0.75em;color:var(--text3);"><?= htmlspecialchars($r['parse']['format'] ?? 'unknown') ?> format</span>
        </div>
        <?php $p = $r['parse']; ?>
        <div class="grid-3" style="margin-bottom:8px;">
            <div style="background:rgba(255,255,255,0.05);padding:8px;border-radius:var(--radius);text-align:center;">
                <div style="font-size:0.65em;color:var(--text3);text-transform:uppercase;">Parsed</div>
                <div style="font-size:1.3em;font-weight:700;"><?= number_format($p['parsed'] ?? 0) ?></div>
            </div>
            <div style="background:rgba(255,255,255,0.05);padding:8px;border-radius:var(--radius);text-align:center;">
                <div style="font-size:0.65em;color:var(--text3);text-transform:uppercase;">Imported</div>
                <div style="font-size:1.3em;font-weight:700;color:var(--green);"><?= number_format($p['imported'] ?? 0) ?></div>
            </div>
            <div style="background:rgba(255,255,255,0.05);padding:8px;border-radius:var(--radius);text-align:center;">
                <div style="font-size:0.65em;color:var(--text3);text-transform:uppercase;">Skipped (dupes)</div>
                <div style="font-size:1.3em;font-weight:700;color:var(--yellow);"><?= number_format($p['skipped'] ?? 0) ?></div>
            </div>
        </div>
        <?php if (!empty($p['account'])): ?>
        <div style="font-size:0.8em;color:var(--text3);">Account: <strong><?= htmlspecialchars($p['account']) ?></strong></div>
        <?php endif; ?>
        <?php if (!empty($p['note'])): ?>
        <div style="font-size:0.8em;color:var(--orange);margin-top:4px;">&#x26A0;&#xFE0F; <?= htmlspecialchars($p['note']) ?></div>
        <?php endif; ?>
        <?php if (!empty($p['text_preview'])): ?>
        <details style="margin-top:8px;">
            <summary style="font-size:0.8em;color:var(--accent);cursor:pointer;">View extracted text preview</summary>
            <pre style="background:rgba(0,0,0,0.2);padding:12px;border-radius:var(--radius);font-size:0.75em;overflow:auto;max-height:300px;margin-top:8px;color:var(--text2);"><?= htmlspecialchars($p['text_preview']) ?></pre>
        </details>
        <?php endif; ?>
    </div>
    <?php endforeach; ?>

    <div style="text-align:center;margin-top:16px;">
        <a href="?action=transactions" class="btn">&#x1F4CB; View Transactions</a>
        <a href="?action=upload" class="btn" style="margin-left:12px;">Upload More Files</a>
    </div>
</div>
<?php endif; ?>

<!-- Import History -->
<?php if (!empty($history)): ?>
<div class="card" style="margin-top:24px;">
    <div class="card-header">&#x1F4DA; Import History</div>
    <table class="strategy-table" style="font-size:0.85em;">
        <tr>
            <th>Source File</th>
            <th>Transactions</th>
            <th>Date Range</th>
        </tr>
        <?php foreach ($history as $h): ?>
        <tr>
            <td><?= htmlspecialchars($h['source_file']) ?></td>
            <td style="text-align:center;"><?= number_format($h['txn_count']) ?></td>
            <td><?= htmlspecialchars($h['earliest']) ?> → <?= htmlspecialchars($h['latest']) ?></td>
        </tr>
        <?php endforeach; ?>
    </table>
</div>
<?php endif; ?>
