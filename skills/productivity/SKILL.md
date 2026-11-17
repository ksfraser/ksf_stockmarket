---
name: productivity
description: "Productivity tools: Google Workspace, Linear, Maps, Notion, Teams meeting pipeline."
tags: [google-workspace, gmail, calendar, drive, sheets, docs, linear, maps, geocoding, notion, teams, meetings, microsoft-graph]
---

# Productivity

Class-level umbrella for productivity and workspace tools: email/calendar/docs, issue trackers, maps, knowledge bases, and meeting automation.

## 1) Google Workspace — `google-workspace`

Gmail, Calendar, Drive, Contacts, Sheets, Docs via `gws` CLI or bundled Python client. OAuth2 setup with `setup.py`, `google_api.py` as compatibility wrapper.

References: Gmail search syntax, Himalaya IMAP/SMTP fallback.
Scripts: setup.py, google_api.py, gws_bridge.py, _hermes_home.py.

## 2) Linear — `linear`

Issue and project management via Linear GraphQL API using `curl`. No MCP server, no OAuth. Supports full issue lifecycle, projects, teams, labels, and comments.

## 3) Maps — `maps`

Location intelligence via OpenStreetMap/Nominatim, Overpass API, OSRM, and TimeAPI.io. Python stdlib only, no API key required.

Scripts: `scripts/maps_client.py` — 8 commands (search, reverse, nearby, distance, directions, timezone, area, bbox).

## 4) Notion — `notion`

Notion API via `ntn` CLI (preferred on macOS/Linux) or HTTP + curl (cross-platform). Covers pages, databases (data sources), markdown, Workers, and file uploads.

References: block-types, Airtable REST API.
Prerequisites: `NOTION_API_KEY`.

## 5) Teams Meeting Pipeline — `teams-meeting-pipeline`

Operate the Teams meeting summary pipeline via Hermes CLI — summarize meetings, inspect pipeline status, replay jobs, manage Microsoft Graph subscriptions.

Prerequisites: `MSGRAPH_TENANT_ID`, `MSGRAPH_CLIENT_ID`, `MSGRAPH_CLIENT_SECRET`.

## Rules

1. Never send emails, create calendar events, delete files, or modify Docs/Sheets without user confirmation.
2. Check auth before first use of any tool; guide the user through setup if missing.
3. Respect rate limits; batch reads when possible.
