"""Gmail の SMTP 経由でメールを送信する。

Gmail のアプリパスワードを使う（2段階認証を有効にして発行）。
https://support.google.com/accounts/answer/185833
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formatdate

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL


def send_email(
    *,
    gmail_address: str,
    app_password: str,
    mail_from: str,
    mail_to: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from or gmail_address
    msg["To"] = mail_to
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(gmail_address, app_password)
        server.send_message(msg)
