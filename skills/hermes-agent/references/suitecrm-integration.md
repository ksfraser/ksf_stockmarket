# SuiteCRM Integration for KSFII

Integration capabilities between Hermes agents and SuiteCRM for Fraser Highland Shoppe.

## Features

- **Authentication Management**: Secure login to SuiteCRM using credentials
- **Client Data Synchronization**: Sync client information between Hermes and SuiteCRM
- **Activity Logging**: Log interactions, meetings, follow-ups
- **Opportunity Management**: Create, update, track sales opportunities
- **Task and Calendar Integration**: Manage tasks, appointments, reminders
- **Custom Module Support**: Work with KSFII-specific custom modules

## Connection Methods

- **REST API**: Primary method (`/service/v4_1/rest.php`)
- **Database Direct**: For bulk operations (read-only recommended)

## Authentication

- Username/password via REST API
- Session management and token refresh
- SSL/TLS security

## KSFII-Specific Custom Fields

- KTP (Know The Prospect) tracking
- Policy application status
- Investment application tracking
- Referral source tracking
- Client avatar classification
- Product interest tracking
- Meeting notes and value proposition tracking

## Common Troubleshooting

- **Redirect Handling**: SuiteCRM may return 301/302 redirects
- **Empty API Responses**: Verify correct endpoint URL, authentication, API access enabled
- **Authentication Failures**: Check username/password, API permissions, IP restrictions
- **Connection Timeouts**: Increase timeout values, verify firewall rules

## Usage Examples

```bash
# Test connection
python3 scripts/test_suitecrm_connection.sh

# Create lead
hermes integration run ksfii-suitecrm-integration --action "create-lead" --data "{...}"

# Log activity
hermes integration run ksfii-suitecrm-integration --action "log-activity" --data "{...}"
```

## Reference

- `references/suitecrm_connection_details.md` — Connection parameters, working examples, troubleshooting
- `references/suitecrm_connection_issues.md` — Known issues and solutions
