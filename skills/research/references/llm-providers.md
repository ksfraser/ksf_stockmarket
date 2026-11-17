# LLM Provider Implementation Notes

## Multi-provider scoring in `research_agent.py`

`score_idea_with_llm(conn, idea)` reads from `system_settings` and supports 6 providers.

### Provider resolution order
1. Read `llm_base_url` from `system_settings`
2. If empty, resolve default by `llm_provider`:
   - `openrouter` → `https://openrouter.ai/api/v1`
   - `openai` → `https://api.openai.com/v1`
   - `anthropic` → `https://api.anthropic.com`
   - `ollama` → `http://localhost:11434`
   - `google` → `https://generativelanguage.googleapis.com/v1beta`
   - `azure` → `https://<resource>.openai.azure.com`

### API shapes
- **OpenAI-compatible**: POST `/chat/completions`, Bearer auth
  - Providers: openrouter, openai, azure
- **Anthropic**: POST `/v1/messages`, `x-api-key` auth, `anthropic-version: 2023-06-01`
- **Ollama**: POST `/api/chat`, no auth, `stream: false`, response in `message.content`
- **Google**: POST `/models/{model}:generateContent`, key as query param `?key=...`, response in `candidates[0].content.parts[0].text`

### Prompt contract
Always ask for JSON only:
```
Score this trading/strategy idea from 1–10 on three axes:
  - novelty: how original is the approach?
  - feasibility: how implementable is it?
  - edge: does it have a plausible alpha edge?

Title: {title}
Source: {source}
URL: {url}

Return JSON only: {novelty, feasibility, edge, reasoning}.
```

### Fallback behavior
- No `llm_api_key` → `{"novelty":5,"feasibility":5,"edge":5,"total":15,"model":"heuristic"}`
- HTTP/network error → same heuristic with `error` field
- JSON parse failure → same heuristic

### Key gotcha
`score_idea_with_llm` requires the live `conn` cursor. If you call it from a different context, pass the connection explicitly. It uses `_get_system_setting(conn, key)` not a global config.
