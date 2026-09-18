# BR-07: AI-Advisor Personas

## Business Requirement

The system shall provide public-facing AI-advisor personas that represent distinct investment philosophies for simulation and reference. Personas include value investing (Warren Buffett-style), growth-at-reasonable-price (Peter Lynch-style), systematic index-region and sector strategies, frequency-based timing strategies (day/week/month/bi-annual), and LLM-enhanced fundamental analysts that read and update forward-guidance, news, product-development, and regulatory-approval tracking tables.

## Business Context

The Paperclip Zero-Human Trading Firm concept requires a diverse set of AI-advisor personas that can simulate different investment approaches. These personas serve as:

1. **Public reference portfolios** - Regular users can view advisor portfolios without logging in, comparing different investment philosophies side by side
2. **Simulation evidence** - Each advisor runs with the same portfolio tables and trade mechanics, making results comparable
3. **Strategy comparison** - Index advisors isolate regional/sector exposures; trader advisors isolate frequency/time-horizon effects

## Advisor Personas

### Value Investing
- **warren-buffett** - Value investing based on Buffett/Munger principles: durable competitive moat, competent management, attractive price relative to intrinsic value. Screens for low P/E, high ROE, low debt, consistent earnings growth.

### Growth at Reasonable Price
- **peter-lynch** - GARP style: grows earnings faster than the market but not excessively valued. Looks for PEG ratio < 1.5, strong earnings growth, reasonable P/E. Categorizes stocks as slow growers, stalwarts, fast growers, turnarounds.

### Index Region/Sector Strategies
- **index-canada** - TSX index-style: broad Canadian market exposure, dividend-focused, sector-balanced
- **index-usa** - US market index-style: S&P 500-style diversification, market-cap weighted
- **index-euro** - European market exposure: diversified across major European exchanges
- **index-cad-us** - Canada-USA cross-border: balanced exposure to both markets
- **index-energy** - Energy sector focus: oil & gas, renewable energy, energy infrastructure
- **index-essentials** - Consumer essentials/staples: defensive, dividend-paying, recession-resistant
- **index-tech** - Technology sector focus: growth-oriented, innovation-driven, higher volatility

### Timing Strategies
- **day-trader** - Daily rebalancing: buys and sells within the day, captures short-term momentum and mean reversion
- **week-trader** - Weekly rebalancing: enters/exits on a weekly cadence, captures weekly patterns
- **month-trader** - Monthly rebalancing: monthly entry/exit decisions, captures monthly seasonality
- **bi-annual-trader** - Semi-annual rebalancing: twice-yearly portfolio review and adjustment

### LLM-Enhanced Fundamental Analysts
- **llm-fundamental-value** - LLM-powered value analysis: reads guidance, news, product dev, regulatory tables; produces conviction scores and investment theses; focuses on undervalued companies with strong fundamentals
- **llm-fundamental-growth** - LLM-powered growth analysis: focuses on companies with accelerating growth trajectories, positive news momentum, favorable regulatory environment, and expanding product lines

## Common Requirements for All Advisors

1. **Public visibility** - Advisor portfolios are public; regular user portfolios are private by default
2. **Fixed start date** - All advisors start from 2025-01-02 with $100,000 CAD initial cash
3. **Mid-price fills** - Trades are priced at the day's mid price (approximate from OHLC)
4. **Same portfolio tables** - All advisors use the same `portfolio` and `portfolio_history` tables
5. **Same trade mechanics** - All advisors execute trades via the same mechanics (no special privileges)

## LLM-Enhanced Advisor Specifics

LLM-enhanced advisors (llm-fundamental-value, llm-fundamental-growth) have additional requirements:

1. **Read llm_* tables at session start** - Before analysis, read `llm_insider_trading`, `llm_news_events`, `llm_product_dev`, `llm_regulatory` for target symbols
2. **Produce conviction scores** - Each analysis produces a conviction score (-100 to +100) and investment thesis summary
3. **Update llm_* tables** - When new information is found during scanning, update the relevant llm_* tables
4. **Fallback chain** - Operate within the LLM fallback chain (primary -> secondary -> fallback per FR-13)
5. **Coordinate with scoring tables** - Feed conviction scores and thesis summaries into `evalsummary`, `evalbusiness`, `evalmanagement`, `evalvalue`

## Acceptance Criteria

- [ ] All advisor personas are created as user accounts in the `users` table
- [ ] All advisor portfolios are created in the `portfolio` table with $100,000 CAD starting cash
- [ ] All advisor portfolios are marked as public
- [ ] Advisor trade history is stored in `portfolio_history` with the same mechanics as regular users
- [ ] LLM-enhanced advisors read llm_* tables before analysis
- [ ] LLM-enhanced advisors produce conviction scores and thesis summaries
- [ ] LLM-enhanced advisors update llm_* tables when new info is found
- [ ] LLM-enhanced advisors use the configured fallback chain (primary -> secondary -> fallback)
- [ ] Public users can view advisor portfolios without logging in
- [ ] Advisor performance can be compared side by side in the UI

## Related

- FR-11: LLM Fundamental Data Tables
- FR-12: Research Wizard Formula Integration
- FR-13: LLM Advisor Admin Screen
- FR-14: Zacks RW Pipeline
- FR-16: Timing Variables in Advisor Control Plane
- `docs/advisors/REQUIREMENTS_DESIGN.md`
- `docs/architecture/architecture-document.md` §10.5-§10.8
