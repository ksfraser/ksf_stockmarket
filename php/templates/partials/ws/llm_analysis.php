<?php
/**
 * WealthSystem LLM Qualitative Analysis Detail
 *
 * Expects: $llm_ws['text'] or $llm_ws['summary'] or fallback scalar
 */
$llm_ws = $llm_ws ?? $qualitative ?? [];
if (empty($llm_ws) && empty($qualitative)):
?>
<p class="text-muted">LLM qualitative analysis not yet available for this symbol.</p>
<?php return; endif;

$text = is_string($llm_ws) ? $llm_ws : ($llm_ws['text'] ?? $llm_ws['summary'] ?? $llm_ws['conclusion'] ?? json_encode($llm_ws, JSON_PRETTY_PRINT));
?>
<div style="padding:12px; background:var(--bg2); border:1px solid var(--border); border-radius:8px;">
    <div style="font-size:0.9em; line-height:1.5; color:var(--text1);">
        <?= nl2br(htmlspecialchars($text)) ?>
    </div>
</div>
