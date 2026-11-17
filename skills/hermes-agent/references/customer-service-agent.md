# Customer Service Agent

Customer service agent that handles chats, emails, SMS, Discord/WhatsApp messages, logs interactions to CRM, creates sales orders, handles warranty/returns enquiries, learns communication style from email history, and integrates with website and internal knowledge base.

## Features

- **Multi-channel support**: Email, SMS, Discord, WhatsApp, website chat
- **CRM integration**: Log all interactions to SuiteCRM via REST API
- **Sales order creation**: Generate sales orders in FrontAccounting or WooCommerce
- **Warranty/returns handling**: Guide customers through warranty claims and return processes
- **Voice training**: Analyze email history to learn company communication style
- **Knowledge base integration**: Access internal Mediawiki and WordPress/WooCommerce
- **Escalation workflows**: Transfer to human agents based on complexity or sentiment

## Prerequisites

### Email Access (IMAP)
```
EMAIL_IMAP_HOST=imap.yourprovider.com
EMAIL_IMAP_USER=customer_service@yourdomain.com
EMAIL_IMAP_PASS=your_app_password
```

### CRM Access (SuiteCRM)
```
SUITECRM_URL=https://crm.yourdomain.com
SUITECRM_USERNAME=api_user
SUITECRM_PASSWORD=api_password
```

### FrontAccounting
```
FA_DB_HOST=localhost
FA_DB_USER=hermes_user
FA_DB_PASSWORD=fa_password
FA_DB_NAME=frontacc
```

### WooCommerce
```
WC_URL=https://shop.yourdomain.com
WC_CONSUMER_KEY=ck_your_key
WC_CONSUMER_SECRET=cs_your_secret
```

## Workflow

1. **Message Ingestion**: Monitor all connected channels via Hermes gateway
2. **Voice Training**: Process historical emails to learn brand voice
3. **Knowledge Base Access**: Search Mediawiki for SOPs, WordPress/WooCommerce for product info
4. **CRM Integration**: Log interactions, associate with contacts/leads, track case status
5. **Sales Order Creation**: Check inventory, create orders, send confirmations
6. **Warranty & Returns**: Look up warranty terms, guide through RMA process
7. **Escalation**: Detect frustration or complex issues, transfer to human with full history

## Automated Operation

```bash
hermes cron create "*/2 * * * *" \
  prompt="Check for new customer service messages across all channels, process them, log to CRM, and generate appropriate responses." \
  deliver="origin" \
  skills=["customer-service-agent"]
```

## Troubleshooting

- **Email connection failures**: Verify IMAP credentials, test with the Himalaya reference in `google-workspace` (`google-workspace/references/himalaya.md`), or use `himalaya` CLI directly if installed.
- **CRM API auth errors**: Check API user permissions in SuiteCRM
- **No voice profile**: Check email history exists in IMAP inbox
- **Sales order creation fails**: Test FA/MySQL connection manually
