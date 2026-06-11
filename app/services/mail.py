"""E-Mail-Versand (SMTP). Ohne Konfiguration: Logging-Fallback für die Entwicklung."""
import smtplib
import ssl
from email.message import EmailMessage
from flask import current_app


def is_configured():
    cfg = current_app.config
    return bool(cfg.get('MAIL_SERVER') and cfg.get('MAIL_USERNAME'))


def send_email(to, subject, body):
    """Versendet eine E-Mail. Gibt True bei Versand/Log zurück, False bei Fehler.
    Ohne SMTP-Konfiguration wird die Nachricht nur protokolliert (Dev)."""
    if not to:
        return False
    cfg = current_app.config
    sender = cfg.get('MAIL_FROM') or cfg.get('MAIL_USERNAME') or 'noreply@dropbid.local'

    if not is_configured():
        current_app.logger.info(
            f"[MAIL:LOG] An: {to}\nBetreff: {subject}\n{body}\n{'-'*40}")
        print(f"[MAIL:LOG] -> {to} | {subject}")
        return True

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = to
        msg.set_content(body)

        host = cfg['MAIL_SERVER']
        port = int(cfg.get('MAIL_PORT', 587))
        user = cfg.get('MAIL_USERNAME')
        pwd = cfg.get('MAIL_PASSWORD')

        if cfg.get('MAIL_USE_SSL'):
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, context=ctx) as s:
                if user:
                    s.login(user, pwd)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as s:
                if cfg.get('MAIL_USE_TLS', True):
                    s.starttls(context=ssl.create_default_context())
                if user:
                    s.login(user, pwd)
                s.send_message(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"[MAIL:ERROR] {e}")
        return False


def send_many(recipients, subject, body):
    """Sendet dieselbe Nachricht an mehrere Empfänger."""
    ok = 0
    for r in recipients:
        if send_email(r, subject, body):
            ok += 1
    return ok
