<?php
/**
 * WealthSystem Evaluations Detail
 *
 * Expects: $eval_ws['domains']
 * domains = [
 *   'Value' => ['score'=>..., 'max'=>..., 'grade'=>'A-F', 'note'=>'...'],
 *   'Growth' => [...],
 *   'Quality' => [...],
 *   'Momentum' => [...],
 * ]
 */
if (empty($eval_ws) || empty($eval_ws['domains'] ?? [])):
?>
<p class="text-muted">Evaluation breakdown not yet available.</p>
<?php return; endif;

$gradeColors = ['A'=>'var(--green)','B'=>'#4caf50','C'=>'var(--yellow)','D'=>'var(--red)','F'=>'var(--red)'];
$domains = $eval_ws['domains'];
$total = 0; $max = 0;
foreach ($domains as $d) { $total += (int)($d['score'] ?? 0); $max += (int)($d['max'] ?? 0); }
$pct = $max > 0 ? round(($total / max((int)$max, 1)) * 100, 1) : 0;
$overall = $pct >= 90 ? 'A' : ($pct >= 80 ? 'B' : ($pct >= 70 ? 'C' : ($pct >= 60 ? 'D' : 'F')));
?>
<div style="display:flex; gap:20px; align-items:center; margin-bottom:10px;">
    <div style="font-size:2.5em; font-weight:700; color:<?= $gradeColors[$overall] ?? 'var(--text1)' ?>">
        <?= htmlspecialchars($overall) ?>
    </div>
    <div style="font-size:0.9em; color:var(--text3);">Evaluation Composite <?= $pct ?>%</div>
</div>
<div class="stats-grid">
    <?php foreach (['Value'=>'Value','Growth'=>'Growth','Quality'=>'Quality','Momentum'=>'Momentum'] as $k => $label):
        $d = $domains[$k] ?? ['score'=>0,'max'=>100,'grade'=>'F','note'=>'not scored'];
        $dp = (int)($d['max'] ?? 100) > 0 ? round(((int)$d['score'] ?? 0) / max((int)$d['max'], 1) * 100, 1) : 0;
    ?>
        <div class="stat-card">
            <div class="stat-value" style="color:<?= $gradeColors[$d['grade'] ?? 'F'] ?? 'var(--red)' ?>"><?= htmlspecialchars($d['grade'] ?? 'F') ?></div>
            <div class="stat-label"><?= htmlspecialchars($label) ?> (<?= $dp ?>%)</div>
            <?php if (!empty($d['note'])): ?>
                <div style="font-size:0.8em; color:var(--text3); margin-top:4px;"><?= htmlspecialchars($d['note']) ?></div>
            <?php endif; ?>
        </div>
    <?php endforeach; ?>
</div>
