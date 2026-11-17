# YouTube Strategy Agent Reference

Ported from `jackson-video-resources/yt-strategy-agent`. Adds YouTube channel watching, transcript extraction via Apify, structured strategy parsing via LLM, recency-weighted rule merging, and shift detection.

## Dependencies

```bash
pip install apify-client google-api-python-client google-auth-httplib2 google-auth-oauthlib sentence-transformers numpy
```

## Admin Settings Keys

| Key | Type | Purpose |
|---|---|---|
| `youtube_api_key` | password | YouTube Data API v3 key |
| `apify_token` | password | Apify token for `karamelo/youtube-transcripts` |
| `youtube_watch_channels` | text | Comma-separated `@handles` or URLs |

## Python Functions

| Function | Purpose |
|---|---|
| `_youtube_channel_search(handles, limit)` | Resolves handles → channel IDs → uploads playlists → latest videos |
| `_youtube_transcript_fetch(video_ids, apify_token)` | Fetches transcripts via Apify actor `karamelo/youtube-transcripts` |
| `_youtube_extract_transcript(transcript, title)` | LLM extracts structured strategy JSON from transcript |
| `_youtube_impact_summary(extraction, title, spec)` | LLM writes 3–5 sentence brief on how new video affects current paper-trading spec |
| `_recency_weighted_rules(extractions)` | Merges rolling window of extractions using recency weights + cosine similarity grouping |
| `_youtube_shift_detect(handle, new_extraction, dir)` | Detects semantic drift + contradictions; appends to `changelog.md` |

## Structured Extraction Schema

```json
{
  "strategy_summary": "2-4 sentences describing host approach",
  "buy_rules": [{"rule": "...", "confidence": 0.0-1.0, "source_quote": "verbatim snippet"}],
  "sell_rules": [{"rule": "...", "confidence": 0.0-1.0, "source_quote": "..."}],
  "risk_notes": [{"note": "...", "confidence": 0.0-1.0, "source_quote": "..."}],
  "timing_notes": [{"note": "...", "confidence": 0.0-1.0, "source_quote": "..."}],
  "executed_trades": [{"asset": "...", "direction": "long|short", "entry": "...", "exit": "...", "outcome": "..."}],
  "strategy_shift": {"changed": false, "what_changed": "...", "vs_prior": "..."}
}
```

## Recency Weighting Constants

| Constant | Value | Purpose |
|---|---|---|
| `_YOUTUBE_WEIGHTS` | `[1.00, 0.70, 0.50, 0.35, 0.25]` | Per-video weight in rolling window |
| `_YOUTUBE_MIN_CONFIDENCE` | `0.30` | Minimum effective confidence to keep a grouped rule |
| `_YOUTUBE_SIMILARITY_THRESHOLD` | `0.82` | Cosine similarity for grouping duplicate rules |

## Output Format

YouTube extractions are appended to the external brief markdown under `## YouTube Strategy Extractions` with sections: Summary, Buy rules, Sell rules, Risk notes, Timing notes, Executed trades. Each rule shows `(confidence)` and `> source_quote`.

## Pitfalls

- **Apify costs**: `karamelo/youtube-transcripts` actor charges per video; monitor Apify usage
- **YouTube quota**: Data API v3 has 10,000 units/day default; `search().list` costs 100 units, `playlistItems().list` costs 1 per call
- **Transcript availability**: Not all videos have captions; Apify returns empty for those
- **LLM token usage**: Full transcripts are truncated to 60k chars before sending to LLM
- **sentence-transformers model**: `all-MiniLM-L6-v2` is ~80MB; caches in `~/.cache/torch/sentence_transformers`
