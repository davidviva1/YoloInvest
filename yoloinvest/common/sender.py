"""Shared Telegram sender for YoloInvest."""
from typing import List

import requests

from yoloinvest.config import DETAILED_FILE, REQUEST_TIMEOUT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class TelegramSender:
    MAX_MESSAGE_LENGTH = 4000

    def __init__(self, bot_token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID):
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")
        if not chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is not set")
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def split_message(self, text: str) -> List[str]:
        if len(text) <= self.MAX_MESSAGE_LENGTH:
            return [text]
        chunks: List[str] = []
        current_chunk = ""
        paragraphs = text.split("\n\n")
        for para in paragraphs:
            if len(para) > self.MAX_MESSAGE_LENGTH:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                lines = para.split("\n")
                for line in lines:
                    if len(current_chunk) + len(line) + 1 > self.MAX_MESSAGE_LENGTH:
                        chunks.append(current_chunk)
                        current_chunk = line
                    else:
                        current_chunk += ("\n" if current_chunk else "") + line
            elif len(current_chunk) + len(para) + 2 > self.MAX_MESSAGE_LENGTH:
                chunks.append(current_chunk)
                current_chunk = para
            else:
                current_chunk += ("\n\n" if current_chunk else "") + para
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        try:
            response = requests.post(
                self.api_url,
                json={"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode},
                timeout=REQUEST_TIMEOUT,
            )
            result = response.json()
            if not result.get("ok"):
                print(f"Error sending message: {result.get('description')}")
                return False
            return True
        except Exception as exc:
            print(f"Exception sending message: {exc}")
            return False

    def send_long_message(self, text: str) -> bool:
        chunks = self.split_message(text)
        print(f"Sending {len(chunks)} message(s)...")
        for i, chunk in enumerate(chunks, 1):
            print(f"  Sending part {i}/{len(chunks)}...")
            if not self.send_message(chunk):
                print(f"Failed to send part {i}")
                return False
            if i < len(chunks):
                import time

                time.sleep(1)
        return True

    def send_report(self, filepath: str = DETAILED_FILE) -> bool:
        try:
            with open(filepath, "r") as f:
                text = f.read()
            return self.send_long_message(text)
        except Exception as exc:
            print(f"Error reading report file: {exc}")
            return False
