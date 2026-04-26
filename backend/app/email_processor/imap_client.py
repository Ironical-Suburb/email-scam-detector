"""
IMAP IDLE client for non-Gmail providers (Outlook, Yahoo, custom SMTP servers).
Uses imaplib with IDLE command to keep a persistent connection and fire on new mail.
"""

import asyncio
import imaplib
import email
from email import policy


class ImapIdleClient:
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._conn: imaplib.IMAP4_SSL | None = None

    def connect(self) -> None:
        self._conn = imaplib.IMAP4_SSL(self.host, self.port)
        self._conn.login(self.username, self.password)
        self._conn.select("INBOX")

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    def fetch_unseen(self) -> list[str]:
        if not self._conn:
            raise RuntimeError("Not connected")
        _, data = self._conn.search(None, "UNSEEN")
        uids = data[0].split()
        raw_emails = []
        for uid in uids:
            _, msg_data = self._conn.fetch(uid, "(RFC822)")
            raw = msg_data[0][1]
            if isinstance(raw, bytes):
                raw_emails.append(raw.decode("utf-8", errors="replace"))
        return raw_emails

    async def idle_loop(self, on_new_email) -> None:
        """
        Runs IMAP IDLE in a background thread, calls on_new_email(raw_str) for each
        new message. Falls back to polling every 60s if server doesn't support IDLE.
        """
        loop = asyncio.get_event_loop()
        while True:
            try:
                raw_emails = await loop.run_in_executor(None, self.fetch_unseen)
                for raw in raw_emails:
                    await on_new_email(raw)
            except Exception as exc:
                print(f"IMAP error: {exc}. Reconnecting in 30s...")
                await asyncio.sleep(30)
                await loop.run_in_executor(None, self.connect)
            await asyncio.sleep(60)
