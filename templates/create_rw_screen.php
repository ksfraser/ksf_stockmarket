<?php
/**
 * Create Zacks RW Screen — rule builder UI.
 */
$pageTitle = $data['pageTitle'] ?? 'Create Screen';
$error = $data['error'] ?? '';
$fields = $data['fields'] ?? [];
$operators = $data['operators'] ?? [];
?>
<div class="card">
    <div class="card-header">
        <h3>Create Your Own Screen</h3>
        <span class="text-muted">Build a custom Research Wizard screen from Zacks field rules.</span>
    </div>
    <div class="card-body">
        <?php if ($error): ?>
            <div style="background:rgba(252,129,129,0.15);border:1px solid var(--red);color:var(--red);padding:12px;border-radius:var(--radius);margin-bottom:16px;font-size:0.9em;">
                <?= htmlspecialchars($error) ?>
            </div>
        <?php endif; ?>

        <form method="POST" action="?action=create_rw_screen" id="create-screen-form">
            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Screen Name</label>
                <input type="text" name="name" required placeholder="e.g. High ROE Momentum"
                       style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            </div>

            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Description (optional)</label>
                <input type="text" name="description" placeholder="Brief description of this screen"
                       style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
            </div>

            <div style="margin-bottom:16px;">
                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                    <input type="checkbox" name="is_public" value="1" style="accent-color:var(--accent);">
                    <span style="font-size:0.9em;">Make this screen public (visible to other users)</span>
                </label>
            </div>

            <div style="margin-bottom:16px;">
                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
                    <input type="checkbox" name="is_shared" value="1" style="accent-color:var(--accent);">
                    <span style="font-size:0.9em;">Share with my advisors</span>
                </label>
            </div>

            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Category (optional)</label>
                <input type="text" name="category" placeholder="e.g. Buffett, Lynch, Graham, CANSLIM"
                       list="screen-categories"
                       style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
                <datalist id="screen-categories">
                    <option value="Buffett">
                    <option value="Lynch">
                    <option value="Graham">
                    <option value="CANSLIM">
                    <option value="Growth">
                    <option value="Value">
                    <option value="Dividend">
                    <option value="Momentum">
                    <option value="Quality">
                </datalist>
            </div>

            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:8px;">
                    Rules <span style="color:var(--red);">*</span>
                </label>
                <div id="rules-container">
                    <!-- Rules injected by JS -->
                </div>
                <button type="button" id="add-rule-btn"
                        style="margin-top:8px;background:var(--bg2);border:1px solid var(--border);color:var(--accent);padding:6px 12px;border-radius:4px;cursor:pointer;">
                    + Add Rule
                </button>
            </div>

            <div style="display:flex;gap:12px;margin-top:20px;">
                <button type="submit"
                        style="background:var(--accent);color:#fff;padding:10px 20px;border:none;border-radius:4px;cursor:pointer;font-size:0.95em;">
                    Save Screen
                </button>
                <a href="?action=rw_screens" style="padding:10px 20px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;text-decoration:none;font-size:0.95em;">
                    Cancel
                </a>
            </div>
        </form>
    </div>
</div>

<script>
(function() {
    const fields = <?= json_encode($fields, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) ?>;
    const operators = <?= json_encode($operators, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) ?>;
    const container = document.getElementById('rules-container');
    const addBtn = document.getElementById('add-rule-btn');

    function buildFieldOptions() {
        let html = '<optgroup label="">-- select field --</optgroup>';
        for (const [group, items] of Object.entries(fields)) {
            html += '<optgroup label="' + group + '">';
            for (const item of items) {
                html += '<option value="' + item.code + '">' + item.code + ' — ' + item.label + '</option>';
            }
            html += '</optgroup>';
        }
        return html;
    }

    function buildOperatorOptions(selected = 'EQ') {
        let html = '';
        for (const [val, label] of Object.entries(operators)) {
            html += '<option value="' + val + '"' + (val === selected ? ' selected' : '') + '>' + label + '</option>';
        }
        return html;
    }

    function addRule(data = null) {
        const div = document.createElement('div');
        div.className = 'rule-row';
        div.style.cssText = 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:8px;background:var(--bg2);border:1px solid var(--border);border-radius:4px;margin-bottom:8px;';

        const connectiveSelect = document.createElement('select');
        connectiveSelect.name = 'rules[][connective]';
        connectiveSelect.style.cssText = 'padding:6px;background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:4px;';
        const andOpt = document.createElement('option'); andOpt.value = 'AND'; andOpt.textContent = 'AND';
        const orOpt = document.createElement('option'); orOpt.value = 'OR'; orOpt.textContent = 'OR';
        connectiveSelect.appendChild(andOpt);
        connectiveSelect.appendChild(orOpt);
        if (data && strtoupper(data.connective) === 'OR') orOpt.selected = true; else andOpt.selected = true;

        const fieldSelect = document.createElement('select');
        fieldSelect.name = 'rules[][code]';
        fieldSelect.innerHTML = buildFieldOptions();
        fieldSelect.style.cssText = 'padding:6px;background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:4px;min-width:220px;';
        if (data) fieldSelect.value = data.code;

        const opSelect = document.createElement('select');
        opSelect.name = 'rules[][operator]';
        opSelect.innerHTML = buildOperatorOptions(data ? data.operator : 'EQ');
        opSelect.style.cssText = 'padding:6px;background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:4px;';

        const valueInput = document.createElement('input');
        valueInput.type = 'text';
        valueInput.name = 'rules[][value]';
        valueInput.value = data ? data.value : '';
        valueInput.placeholder = 'Value';
        valueInput.style.cssText = 'width:80px;padding:6px;background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:4px;';

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.textContent = '✕';
        removeBtn.style.cssText = 'background:transparent;border:none;color:var(--red);cursor:pointer;font-size:1.1em;padding:4px 8px;';
        removeBtn.onclick = function() { div.remove(); };

        div.appendChild(connectiveSelect);
        div.appendChild(fieldSelect);
        div.appendChild(opSelect);
        div.appendChild(valueInput);
        div.appendChild(removeBtn);
        container.appendChild(div);
    }

    addBtn.onclick = function() { addRule(); };

    // Add one default rule
    addRule();
})();
</script>
