<?php
require_once __DIR__ . '/partials/helpers.php';
$advisors = $data['advisors'] ?? [];
$hired = $data['hired'] ?? [];
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
                        <form method="post" style="display:inline;">
                            <input type="hidden" name="action" value="hire">
                            <input type="hidden" name="advisor_id" value="<?= $aid ?>">
                            <button class="btn" type="submit">Hire</button>
                        </form>
                    <?php else: ?>
                        <form method="post" style="display:inline;">
                            <input type="hidden" name="action" value="<?= $activeHired ? 'pause' : 'resume' ?>">
                            <input type="hidden" name="advisor_id" value="<?= $aid ?>">
                            <button class="btn" type="submit" style="background:var(--yellow);color:#000;"><?= $activeHired ? 'Pause' : 'Resume' ?></button>
                        </form>
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
</div>
