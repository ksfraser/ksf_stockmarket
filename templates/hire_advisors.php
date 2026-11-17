<?php
require_once __DIR__ . '/partials/helpers.php';
$advisors = $data['advisors'] ?? [];
$hired = $data['hired'] ?? [];
$allScreens = $data['all_screens'] ?? [];
$allStrategies = $data['all_strategies'] ?? [];
?>
<div class="card" style="border-color:var(--accent);">
    <div class="card-header">🧑‍💼 Hire an Advisor</div>
    <p class="muted">
        Browse the available advisors and hire them to assist your portfolio.
        When an advisor acts, it writes a transaction with notes explaining the action.
        You can pause or fire advisors at any time.
    </p>

    <table style="width:100%;">
        <thead>
            <tr>
                <th>Advisor</th>
                <th>Strategy</th>
                <th>Status</th>
                <th>Hired</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
        <?php foreach ($advisors as $a):
            $aid = (int)($a['id'] ?? 0);
            $activeHired = !empty($hired[$aid]['is_active']);
            $hiredAt = $hired[$aid]['hired_at'] ?? '';
            $my = $hired[$aid] ?? null;
        ?>
            <tr>
                <td><strong><?= htmlspecialchars($a['display_name'] ?? $a['slug']) ?></strong><br>
                    <small class="muted"><?= htmlspecialchars($a['slug']) ?></small>
                </td>
                <td><?= htmlspecialchars($a['strategy'] ?? 'general') ?></td>
                <td>
                    <?php if (!empty($activeHired)): ?>
                        <span style="color:var(--green);">● Active</span>
                    <?php elseif (!empty($hired[$aid])): ?>
                        <span style="color:var(--yellow);">● Paused</span>
                    <?php else: ?>
                        <span style="color:var(--text3);">○ Not hired</span>
                    <?php endif; ?>
                </td>
                <td>
                    <?= $hiredAt ? htmlspecialchars(date('Y-m-d', strtotime($hiredAt))) : '—' ?>
                </td>
                <td style="white-space:nowrap;">
                    <?php if (empty($hired[$aid])): ?>
                        <button class="btn" type="button" onclick="showHireModal(<?= $aid ?>, '<?= htmlspecialchars($a['display_name'] ?? $a['slug']) ?>')">Hire</button>
                    <?php else: ?>
                        <form method="post" style="display:inline;">
                            <input type="hidden" name="action" value="<?= $activeHired ? 'pause' : 'resume' ?>">
                            <input type="hidden" name="advisor_id" value="<?= $aid ?>">
                            <button class="btn" type="submit" style="background:var(--yellow);color:#000;"><?= $activeHired ? 'Pause' : 'Resume' ?></button>
                        </form>
                        <button class="btn" type="button" onclick="showConfigureModal(<?= $aid ?>, '<?= htmlspecialchars($a['display_name'] ?? $a['slug']) ?>')">Configure</button>
                        <form method="post" style="display:inline;" onsubmit="return confirm('Fire this advisor? This removes them from your hired list.');">
                            <input type="hidden" name="action" value="fire">
                            <input type="hidden" name="advisor_id" value="<?= $aid ?>">
                            <button class="btn" type="submit" style="background:var(--red);color:#fff;">Fire</button>
                        </form>
                    <?php endif; ?>
                </td>
            </tr>
        <?php endforeach; ?>
        </tbody>
    </table>
</div>

<div style="margin-top:24px;text-align:center;">
    <a class="btn" href="?action=my_advisors">View My Advisors &amp; Their Trades</a>
    <a class="btn" href="?action=strategy_guidance" style="background:var(--bg2);color:var(--text);margin-left:8px;">Advisor Guidance</a>
    <a class="btn" href="?action=advisors_portfolios" style="background:var(--accent);color:#fff;margin-left:8px;">Advisors & Portfolios Dashboard</a>
</div>

<!-- Hire Modal -->
<div id="hire-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:1000;justify-content:center;align-items:center;">
    <div style="background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);padding:24px;width:90%;max-width:600px;max-height:90vh;overflow-y:auto;">
        <h3>Hire Advisor</h3>
        <p id="hire-modal-name" style="color:var(--text3);margin-bottom:16px;"></p>
        <form method="post" id="hire-form">
            <input type="hidden" name="action" value="hire">
            <input type="hidden" name="advisor_id" id="hire-advisor-id">

            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Notes (optional)</label>
                <textarea name="notes" rows="2" style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;"></textarea>
            </div>

            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Link Screens</label>
                <select name="linked_screen_ids[]" multiple size="6" style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
                    <?php foreach ($allScreens as $s): ?>
                        <option value="<?= (int)$s['id'] ?>"><?= htmlspecialchars($s['name']) ?></option>
                    <?php endforeach; ?>
                </select>
                <p style="font-size:0.75em;color:var(--text3);margin-top:4px;">Hold Ctrl/Cmd to select multiple.</p>
            </div>

            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Strategy Rules</label>
                <select name="strategy_rules[]" multiple size="6" style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
                    <?php foreach ($allStrategies as $s): ?>
                        <option value="<?= htmlspecialchars($s['name'] ?? '') ?>"><?= htmlspecialchars($s['name'] ?? '') ?> (<?= htmlspecialchars($s['category'] ?? '') ?>)</option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Money Management</label>
                <select name="money_management[]" multiple size="6" style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
                    <?php foreach ($allStrategies as $s): ?>
                        <?php if (($s['category'] ?? '') === 'money_management'): ?>
                            <option value="<?= htmlspecialchars($s['name'] ?? '') ?>"><?= htmlspecialchars($s['name'] ?? '') ?></option>
                        <?php endif; ?>
                    <?php endforeach; ?>
                </select>
            </div>

            <div style="display:flex;gap:12px;justify-content:flex-end;">
                <button type="submit" class="btn" style="background:var(--accent);color:#fff;">Hire</button>
                <button type="button" class="btn" onclick="closeHireModal()" style="background:var(--bg2);color:var(--text);">Cancel</button>
            </div>
        </form>
    </div>
</div>

<!-- Configure Modal -->
<div id="configure-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:1000;justify-content:center;align-items:center;">
    <div style="background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);padding:24px;width:90%;max-width:600px;max-height:90vh;overflow-y:auto;">
        <h3>Configure Advisor</h3>
        <p id="configure-modal-name" style="color:var(--text3);margin-bottom:16px;"></p>
        <form method="post" id="configure-form">
            <input type="hidden" name="action" value="configure">
            <input type="hidden" name="advisor_id" id="configure-advisor-id">

            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Notes</label>
                <textarea name="notes" rows="2" id="configure-notes" style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;"></textarea>
            </div>

            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Link Screens</label>
                <select name="linked_screen_ids[]" id="configure-screens" multiple size="6" style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
                    <?php foreach ($allScreens as $s): ?>
                        <option value="<?= (int)$s['id'] ?>"><?= htmlspecialchars($s['name']) ?></option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Strategy Rules</label>
                <select name="strategy_rules[]" id="configure-strategies" multiple size="6" style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
                    <?php foreach ($allStrategies as $s): ?>
                        <option value="<?= htmlspecialchars($s['name'] ?? '') ?>"><?= htmlspecialchars($s['name'] ?? '') ?> (<?= htmlspecialchars($s['category'] ?? '') ?>)</option>
                    <?php endforeach; ?>
                </select>
            </div>

            <div style="margin-bottom:16px;">
                <label style="display:block;font-size:0.85em;color:var(--text3);margin-bottom:4px;">Money Management</label>
                <select name="money_management[]" id="configure-money" multiple size="6" style="width:100%;padding:8px;background:var(--bg2);border:1px solid var(--border);color:var(--text);border-radius:4px;">
                    <?php foreach ($allStrategies as $s): ?>
                        <?php if (($s['category'] ?? '') === 'money_management'): ?>
                            <option value="<?= htmlspecialchars($s['name'] ?? '') ?>"><?= htmlspecialchars($s['name'] ?? '') ?></option>
                        <?php endif; ?>
                    <?php endforeach; ?>
                </select>
            </div>

            <div style="display:flex;gap:12px;justify-content:flex-end;">
                <button type="submit" class="btn" style="background:var(--accent);color:#fff;">Save</button>
                <button type="button" class="btn" onclick="closeConfigureModal()" style="background:var(--bg2);color:var(--text);">Cancel</button>
            </div>
        </form>
    </div>
</div>

<script>
function showHireModal(id, name) {
    document.getElementById('hire-advisor-id').value = id;
    document.getElementById('hire-modal-name').textContent = 'Hiring: ' + name;
    document.getElementById('hire-modal').style.display = 'flex';
}
function closeHireModal() {
    document.getElementById('hire-modal').style.display = 'none';
}
function showConfigureModal(id, name) {
    document.getElementById('configure-advisor-id').value = id;
    document.getElementById('configure-modal-name').textContent = 'Configure: ' + name;
    // Pre-fill existing values
    var hired = <?= json_encode($hired, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) ?>;
    var row = hired[id] || {};
    document.getElementById('configure-notes').value = row.notes || '';
    // screens / strategies / money are CSV strings in DB; convert to arrays for multi-select
    var screens = row.linked_screen_ids ? row.linked_screen_ids.split(',') : [];
    var strats = row.strategy_rules ? JSON.parse(row.strategy_rules) : [];
    var money = row.money_management ? JSON.parse(row.money_management) : [];
    setMultiSelectValues('configure-screens', screens.map(Number));
    setMultiSelectValues('configure-strategies', strats);
    setMultiSelectValues('configure-money', money);
    document.getElementById('configure-modal').style.display = 'flex';
}
function closeConfigureModal() {
    document.getElementById('configure-modal').style.display = 'none';
}
function setMultiSelectValues(selectId, values) {
    var select = document.getElementById(selectId);
    for (var i = 0; i < select.options.length; i++) {
        select.options[i].selected = values.includes(Number(select.options[i].value));
    }
}
// Close modals on outside click
window.onclick = function(event) {
    var hire = document.getElementById('hire-modal');
    var config = document.getElementById('configure-modal');
    if (event.target === hire) closeHireModal();
    if (event.target === config) closeConfigureModal();
}
</script>
