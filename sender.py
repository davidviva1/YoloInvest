#!/usr/bin/env python3
"""
Telegram Sender - 发送简报到 Telegram
处理消息长度限制，自动分段发送
"""
import requests
from typing import List
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, DETAILED_FILE


class TelegramSender:
    """Telegram 消息发送器"""

    MAX_MESSAGE_LENGTH = 4000  # Telegram 限制 4096，留点余量

    def __init__(self, bot_token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID):
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")
        if not chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is not set")

        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def split_message(self, text: str) -> List[str]:
        """智能分割消息（按段落分割，避免截断）"""
        if len(text) <= self.MAX_MESSAGE_LENGTH:
            return [text]

        chunks = []
        current_chunk = ""

        # 按段落分割
        paragraphs = text.split('\n\n')

        for para in paragraphs:
            # 如果单个段落就超长，强制分割
            if len(para) > self.MAX_MESSAGE_LENGTH:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # 按行分割超长段落
                lines = para.split('\n')
                for line in lines:
                    if len(current_chunk) + len(line) + 1 > self.MAX_MESSAGE_LENGTH:
                        chunks.append(current_chunk)
                        current_chunk = line
                    else:
                        current_chunk += ("\n" if current_chunk else "") + line

            # 正常段落
            elif len(current_chunk) + len(para) + 2 > self.MAX_MESSAGE_LENGTH:
                chunks.append(current_chunk)
                current_chunk = para
            else:
                current_chunk += ("\n\n" if current_chunk else "") + para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """发送单条消息"""
        try:
            response = requests.post(
                self.api_url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                },
                timeout=10
            )

            result = response.json()
            if not result.get("ok"):
                print(f"Error sending message: {result.get('description')}")
                return False

            return True

        except Exception as e:
            print(f"Exception sending message: {e}")
            return False

    def send_long_message(self, text: str) -> bool:
        """发送长消息（自动分段）"""
        chunks = self.split_message(text)

        print(f"Sending {len(chunks)} message(s)...")

        for i, chunk in enumerate(chunks, 1):
            print(f"  Sending part {i}/{len(chunks)}...")

            if not self.send_message(chunk):
                print(f"Failed to send part {i}")
                return False

            # 避免触发速率限制
            if i < len(chunks):
                import time
                time.sleep(1)

        return True

    def send_report(self, filepath: str = DETAILED_FILE) -> bool:
        """发送简报文件"""
        try:
            with open(filepath, "r") as f:
                text = f.read()

            return self.send_long_message(text)

        except Exception as e:
            print(f"Error reading report file: {e}")
            return False


if __name__ == "__main__":
    sender = TelegramSender()
    success = sender.send_report()

    if success:
        print("✅ Report sent successfully!")
    else:
        print("❌ Failed to send report")
