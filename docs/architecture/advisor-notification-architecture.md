# Advisor Hiring & Notification Architecture

## 1. Sequence: Hire Advisor → Delivery

```
User                         PHP / Router              MariaDB                     Python
 |                                |                        |                         |
 |--- advisor_preferences ------->|                        |                         |
 |   load prefs/email             |                        |                         |
 |<-- preferences form -----------|                        |                         |
 |                                |                        |                         |
 |--- POST save prefs ----------->|                        |                         |
 |   upsert user_settings         |                        |                         |
 |                                |> INSERT users.email    |                         |
 |                                |> upsert user_settings  |                         |
 |<-- saved ----------------------|                        |                         |
 |                                |                        |                         |
 |--- hire_advisors ------------->|                        |                         |
 |   browse list                  |                        |                         |
 |<-- adviser cards --------------|                        |                         |
 |                                |                        |                         |
 |--- POST hire ----------------->|                        |                         |
 |                                |> INSERT user_advisors  |                         |
 |<-- hired ----------------------|                        |                         |
 |                                |                        |                         |
 |=== cron run_advisor_... ========|========================|========================>|
 |                                |                        |   load active advisors   |
 |                                |                        |   generate signals       |
 |                                |                        |   load hired users       |
 |                                |                        |   queue recommendations  |
 |                                |                        |   load user prefs        |
 |                                |                        |   send email/discord/WA  |
 |                                |                        |   mark sent flags        |
 |<===============================|========================|<========================|
 |                                |                        |                         |
 |--- my_recommendations -------->|                        |                         |
 |                                |> SELECT recommendations |                         |
 |<-- recommendation rows --------|                        |                         |
```

## 2. Sequence: Webhook / API event delivery

```
Python (run_advisor_recommendations.py)
  -> MariaDB advisor_recommendations (queue)
  -> Email: SMTP
  -> Discord: Bot DM (open DM by user_id, then message)
  -> Discord: Channel webhook or bot.postMessage(channelId)
  -> WhatsApp: gateway placeholder
```

## 3. Class-like view

```
- class AdvisorRepository
    get_active_advisors() -> list[dict]
    create_run(user_id, date) -> int
    update_run(run_id, status, error=None)

- class AdvisorRunner (in advisors.runner)
    run(slug=None, date=...) -> None
    _generate_signals(advisor) -> list[Signal]
    _persist_trade(db, sig, ...) -> None  # writes transactions + advisor_id + notes

- class AdvisorNotifier
    load_prefs(user_id) -> UserPrefs
    queue_recommendation(user_id, advisor_id, symbol, action, ...)
    deliver(rec_id) -> dict[channel, bool]
    deliver_pending(user_id, limit=50)

- class AdvisorHiringController (PHP)
    index() -> marketplace view
    hire(user_id, advisor_id)
    pause(user_id, advisor_id)
    resume(user_id, advisor_id)
    fire(user_id, advisor_id)

- class AdvisorNotificationController (PHP)
    preferences() -> load/save user_settings advisor_* keys
    myRecommendations() -> read advisor_recommendations
```

## 4. Data flow diagram

```
 AdvisorAccounts (strategy, slug, schedule)
   │
   ├─► user_advisors (hiring state)
   │     │
   │     ├─► run_advisor_recommendations.py
   │     │     ├─► generate signals
   │     │     ├─► filter hired users
   │     │     ├─► advisor_recommendations (queue)
   │     │     └─► AdvisorNotifier.deliver()
   │     │           ├─► load prefs from user_settings
   │     │           ├─► email
   │     │           ├─► discord_dm
   │     │           ├─► discord_channel
   │     │           └─► whatsapp (placeholder)
   │     │
   │     └─► my_recommendations.php
   │           └─► SELECT advisor_recommendations
   │
   └─► advisor_preferences.php
         └─► upsert user_settings
```

## 5. State machine — user_advisors lifecycle

```
 [+] hired (is_active=1)
    │
    ├─ pause ──────► (is_active=0)
    │                  │
    │                  ├─ resume ─────► [+] hired
    │                  └─ fire ───────► * deleted
    │
    └─ fire ───────► * deleted
```

## 6. Recommendation state machine

```
QUEUED (sent_*=0)
   │
   ├ delivery success ► SENT (sent_*=1, sent_at set)
   └ delivery failure ► QUEUED (auto-retried next cron)
```
