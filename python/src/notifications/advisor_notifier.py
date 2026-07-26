"""Advisor notification dispatcher.

Reads user notification preferences from user_settings and sends advisor
recommendations via:
- Email (SMTP)
- Discord DM (bot token + user Discord ID in user_settings)
- Discord channel webhook (per-user/channel, defaulting to global alert webhook)
- WhatsApp (via HTTP gateway framework)

Framework for WhatsApp is in place; creds/backfill come later.

"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UserPrefs:
    user_id: int
    email: str = ''
    notify_email: bool = False
    notify_discord_dm: bool = False
    discord_user_id: str = ''
    notify_discord_channel: bool = False
    discord_channel_id: str = ''
    notify_whatsapp: bool = False
    whatsapp_number: str = ''


class AdvisorNotifier:
    def __init__(self, db: Any) -> None:
        self.db = db

    @staticmethod
    def _setting_value(rows: list[dict], key: str, default: str = '') -> str:
        for r in rows:
            if r.get('setting_key') == key:
                return r.get('setting_value') or default
        return default

    def load_prefs(self, user_id: int) -> UserPrefs:
        with self.db.cursor() as cur:
            cur.execute(
                'SELECT setting_key, setting_value FROM user_settings WHERE user_id = %s',
                (user_id,),
            )
            rows = cur.fetchall()

        with self.db.cursor() as cur:
            cur.execute('SELECT email FROM users WHERE id = %s', (user_id,))
            user = cur.fetchone() or {}

        return UserPrefs(
            user_id=user_id,
            email=user.get('email', ''),
            notify_email=self._setting_value(rows, 'advisor_notify_email') == '1',
            notify_discord_dm=self._setting_value(rows, 'advisor_notify_discord_dm') == '1',
            discord_user_id=self._setting_value(rows, 'advisor_discord_user_id', ''),
            notify_discord_channel=self._setting_value(rows, 'advisor_notify_discord_channel') == '1',
            discord_channel_id=self._setting_value(rows, 'advisor_discord_channel_id', ''),
            notify_whatsapp=self._setting_value(rows, 'advisor_notify_whatsapp') == '1',
            whatsapp_number=self._setting_value(rows, 'advisor_whatsapp_number', ''),
        )

    def queue_recommendation(
        self,
        user_id: int,
        advisor_id: int,
        symbol: str,
        action: str,
        price: float,
        max_price: Optional[float] = None,
        stop_limit: Optional[float] = None,
        notes: Optional[str] = None,
        signal_reasons: Optional[str] = None,
    ) -> int:
        with self.db.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO advisor_recommendations
                    (user_id, advisor_id, symbol, action, price, max_price, stop_limit, notes, signal_reasons)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (user_id, advisor_id, symbol, action, price, max_price, stop_limit, notes, signal_reasons),
            )
            self.db.commit()
            return int(cur.lastrowid)

    def deliver(self, rec_id: int) -> dict[str, bool]:
        with self.db.cursor() as cur:
            cur.execute(
                'SELECT * FROM advisor_recommendations WHERE id = %s LIMIT 1',
                (rec_id,),
            )
            rec = cur.fetchone()
        if not rec:
            return {}

        user_id = int(rec['user_id'])
        prefs = self.load_prefs(user_id)
        results: dict[str, bool] = {}

        text = (
            "📋 Advisor Recommendation\n"
            f"Action: {rec['action']} {rec['symbol']}\n"
            f"Price: ${float(rec['price']):.2f}"
        )
        if rec.get('max_price'):
            text += f"\nMax: ${float(rec['max_price']):.2f}"
        if rec.get('stop_limit'):
            text += f"\nStop: ${float(rec['stop_limit']):.2f}"
        if rec.get('notes'):
            text += f"\n{rec['notes']}"

        if prefs.notify_email and prefs.email:
            results['email'] = self._send_email(
                prefs.email, f"Advisor: {rec['action']} {rec['symbol']}", text
            )

        if prefs.notify_discord_dm and prefs.discord_user_id:
            results['discord_dm'] = self._send_discord_dm(prefs.discord_user_id, text)

        if prefs.notify_discord_channel and prefs.discord_channel_id:
            results['discord_channel'] = self._send_discord_channel(prefs.discord_channel_id, text)

        if prefs.notify_whatsapp and prefs.whatsapp_number:
            results['whatsapp'] = self._send_whatsapp(prefs.whatsapp_number, text)

        sent_any = any(results.values())
        with self.db.cursor() as cur:
            sets = ['sent_at = NOW()']
            params: list[Any] = [rec_id]
            if results.get('email'):
                sets.append('sent_email = 1')
            if results.get('discord_dm'):
                sets.append('sent_discord_dm = 1')
            if results.get('discord_channel'):
                sets.append('sent_discord_channel = 1')
            if results.get('whatsapp'):
                sets.append('sent_whatsapp = 1')
            cur.execute(f"UPDATE advisor_recommendations SET {', '.join(sets)} WHERE id = %s", params)
            self.db.commit()

        return results

    def deliver_pending(self, user_id: int, limit: int = 50) -> list[dict]:
        with self.db.cursor() as cur:
            cur.execute(
                '''
                SELECT id FROM advisor_recommendations
                WHERE user_id = %s AND sent_email = 0 AND sent_discord_dm = 0
                  AND sent_discord_channel = 0 AND sent_whatsapp = 0
                ORDER BY recommended_at DESC LIMIT %s
                ''',
                (user_id, limit),
            )
            rows = cur.fetchall()
        results: list[dict] = []
        for r in rows:
            res = self.deliver(int(r['id']))
            results.append({'id': int(r['id']), 'sent': res})
        return results

    @staticmethod
    def _send_email(to: str, subject: str, body: str) -> bool:
        here = os.path.dirname(os.path.abspath(__file__))
        _load_dotenv(os.path.join(here, '..', '..', 'config', '.env'))
        host = os.environ.get('SMTP_HOST') or os.environ.get('EMAIL_SMTP_HOST', '')
        port = int(os.environ.get('SMTP_PORT') or os.environ.get('EMAIL_SMTP_PORT', '587'))
        user = os.environ.get('SMTP_USER') or os.environ.get('EMAIL_SMTP_USER', '')
        password = os.environ.get('SMTP_PASS') or os.environ.get('EMAIL_SMTP_PASS', '')
        from_email = (
            os.environ.get('SMTP_FROM') or os.environ.get('EMAIL_SMTP_FROM') or user or ''
        )
        if not host or not user or not password:
            logger.warning('SMTP not configured')
            return False
        try:
            import smtplib

            msg = f'From: {from_email}\r\nTo: {to}\r\nSubject: {subject}\r\n\r\n{body}\r\n'
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(user, password)
                server.sendmail(from_email, [to], msg.encode('utf-8'))
            return True
        except Exception as exc:
            logger.error('Email send failed: %s', exc)
            return False

    @staticmethod
    def _send_discord_dm(user_id: str, text: str) -> bool:
        token = os.environ.get('DISCORD_BOT_TOKEN', '')
        if not token:
            return False
        try:
            import requests

            payload = {'recipient_id': str(user_id)}
            r = requests.post(
                'https://discord.com/api/v10/users/@me/channels',
                headers={'Authorization': f'Bot {token}', 'Content-Type': 'application/json'},
                json=payload,
                timeout=10,
            )
            channel = r.json()
            channel_id = channel.get('id')
            if not channel_id:
                return False
            r2 = requests.post(
                f'https://discord.com/api/v10/channels/{channel_id}/messages',
                headers={'Authorization': f'Bot {token}', 'Content-Type': 'application/json'},
                json={'content': text},
                timeout=10,
            )
            return r2.status_code == 200
        except Exception as exc:
            logger.error('Discord DM failed: %s', exc)
            return False

    @staticmethod
    def _send_discord_channel(channel_id: str, text: str) -> bool:
        webhook = os.environ.get('DISCORD_ALERT_WEBHOOK', '')
        token = os.environ.get('DISCORD_BOT_TOKEN', '')
        url = webhook or f'https://discord.com/api/v10/channels/{channel_id}/messages'
        headers = {'Content-Type': 'application/json'}
        if not webhook and token:
            headers['Authorization'] = f'Bot {token}'
        elif not webhook:
            return False
        try:
            import requests

            payload = {'content': text}
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            return r.status_code in (200, 204)
        except Exception as exc:
            logger.error('Discord channel send failed: %s', exc)
            return False

    @staticmethod
    def _normalize_number(number: str) -> str:
        cleaned = ''.join(ch for ch in number if ch.isdigit() or ch == '+')
        if not cleaned.startswith('+'):
            cleaned = '+' + cleaned
        return cleaned

    @staticmethod
    def _send_whatsapp(number: str, text: str) -> bool:
        result = _send_whatsapp_gateway(number, text)
        return bool(result.get('accepted'))


def _send_whatsapp_gateway(
    number: str, text: str, provider_message_id: Optional[str] = None
) -> dict[str, Any]:
    """WhatsApp gateway framework.

    Reads:
      WHATSAPP_ENABLED=true|false
      WHATSAPP_GATEWAY_URL=https://gateway.example
      WHATSAPP_FROM_NUMBER=+15550000000
      WHATSAPP_API_KEY=...

    Behavior:
      - If WHATSAPP_ENABLED is not true -> accepted=False, reason='disabled'
      - If WHATSAPP_GATEWAY_URL is missing -> accepted=False, reason='not_configured'
      - Normalizes destination number to E.164
      - POSTs {to, from_number, text, provider_message_id} to /v1/send
      - Provider SHOULD later POST to /v1/status for callbacks
      - Returns {accepted, status_code, gateway_message_id, reason}
    """
    here = os.path.dirname(os.path.abspath(__file__))
    _load_dotenv(os.path.join(here, '..', '..', 'config', '.env'))
    _load_dotenv(os.path.expanduser('~/.hermes/.env'))

    enabled = (os.environ.get('WHATSAPP_ENABLED') or '').lower() == 'true'
    if not enabled:
        return {'accepted': False, 'reason': 'disabled'}

    gateway_url = (os.environ.get('WHATSAPP_GATEWAY_URL') or '').rstrip('/')
    if not gateway_url:
        logger.warning('WHATSAPP_GATEWAY_URL not configured')
        return {'accepted': False, 'reason': 'not_configured'}

    api_key = os.environ.get('WHATSAPP_API_KEY') or os.environ.get('WHATSAPP_GATEWAY_API_KEY') or ''
    from_number = os.environ.get('WHATSAPP_FROM_NUMBER', '')

    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    payload = {
        'to': AdvisorNotifier._normalize_number(number),
        'from_number': from_number,
        'text': text,
        'provider_message_id': provider_message_id,
    }

    try:
        import requests

        url = f'{gateway_url}/v1/send'
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        data: dict[str, Any] = {}
        try:
            data = r.json()
        except Exception:
            data = {'raw': r.text}
        logger.info('WhatsApp gateway response %s: %s', r.status_code, data)
        return {
            'accepted': r.status_code in (200, 202),
            'status_code': r.status_code,
            'gateway_message_id': data.get('message_id') or data.get('id'),
            'reason': data.get('status') or data.get('error') or ('sent' if r.status_code in (200, 202) else 'http_error'),
            'upstream': data,
        }
    except Exception as exc:
        logger.error('WhatsApp gateway send failed: %s', exc)
        return {'accepted': False, 'reason': f'exception: {exc}'}


def _load_dotenv(path: str) -> None:
    """Minimal dotenv loader for cron scripts that don't load app.py."""
    try:
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except FileNotFoundError:
        pass


def ensure_env() -> None:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _load_dotenv(os.path.join(here, '..', 'config', '.env'))
    _load_dotenv(os.path.expanduser('~/.hermes/.env'))
