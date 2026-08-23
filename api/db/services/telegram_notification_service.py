#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import json
import logging
import threading
import requests

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """Dispatches real-time alerts to admin and advertiser Telegram chats/channels."""

    @classmethod
    def _send_telegram_request_async(cls, bot_token: str, chat_id: str, text: str, parse_mode: str = "HTML", reply_markup: dict = None):
        """Asynchronous HTTP worker sending message to Telegram API."""
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup

            response = requests.post(url, json=payload, timeout=8)
            if response.status_code != 200:
                logger.warning(f"Telegram notification non-200 response: {response.status_code} - {response.text}")
        except Exception as e:
            logger.warning(f"Telegram notification delivery error (non-blocking): {e}")

    @classmethod
    def send_message(cls, text: str, chat_id: str = "", parse_mode: str = "HTML", reply_markup: dict = None) -> bool:
        """Send message using background thread to avoid blocking main event loop."""
        from common.settings import (
            TELEGRAM_BOT_TOKEN,
            TELEGRAM_ADMIN_CHAT_ID,
            TELEGRAM_NOTIFICATIONS_ENABLED,
        )

        if not TELEGRAM_NOTIFICATIONS_ENABLED:
            return False

        token = TELEGRAM_BOT_TOKEN
        target_chat = chat_id or TELEGRAM_ADMIN_CHAT_ID

        if not token or not target_chat:
            return False

        t = threading.Thread(
            target=cls._send_telegram_request_async,
            args=(token, target_chat, text, parse_mode, reply_markup),
            daemon=True,
        )
        t.start()
        return True

    @classmethod
    def notify_admin_new_campaign(cls, campaign, advertiser_name: str = "") -> bool:
        """Alert superuser/admin about a newly submitted ad campaign requiring moderation."""
        try:
            name = getattr(campaign, "name", "")
            product = getattr(campaign, "product_name", "")
            ad_text = getattr(campaign, "advertisement_text", "")
            url = getattr(campaign, "landing_url", "")
            daily_budget = getattr(campaign, "daily_budget", 0.0)
            bid = getattr(campaign, "bid_amount", 0.10)
            languages = getattr(campaign, "target_languages", []) or ["Все языки"]
            models = getattr(campaign, "target_models", []) or ["Все модели"]

            lang_str = ", ".join(languages) if isinstance(languages, list) else str(languages)
            mod_str = ", ".join(models) if isinstance(models, list) else str(models)

            msg = (
                "📢 <b>Новая рекламная кампания на модерации!</b>\n\n"
                f"🏢 <b>Рекламодатель:</b> {advertiser_name or 'Кабинет рекламодателя'}\n"
                f"🏷 <b>Кампания:</b> {name}\n"
                f"📦 <b>Продукт:</b> {product}\n"
                f"📝 <b>Текст:</b> <i>{ad_text}</i>\n"
                f"🔗 <b>Ссылка:</b> {url}\n"
                f"🌐 <b>Языки:</b> <code>{lang_str}</code>\n"
                f"🤖 <b>Модели:</b> <code>{mod_str}</code>\n"
                f"💰 <b>Бюджет:</b> ${daily_budget:.2f}/день (CPC: ${bid:.2f})\n\n"
                "👉 Перейдите в админ-панель <code>/admin/ads</code> для одобрения или отклонения."
            )
            return cls.send_message(msg)
        except Exception as e:
            logger.warning(f"Error formatting new campaign notification: {e}")
            return False

    @classmethod
    def notify_admin_payment_received(cls, order_data: dict) -> bool:
        """Alert superuser/admin about a successfully settled Atmos payment."""
        try:
            amount_usd = order_data.get("amount_usd", 0.0)
            amount_uzs = order_data.get("amount_uzs", 0)
            purpose = order_data.get("purpose", "")
            card_masked = order_data.get("card_masked", "••••")
            order_id = order_data.get("order_id", "")
            plan_id = order_data.get("plan_id", "")

            purpose_title = "Пополнение баланса рекламодателя" if purpose == "advertiser_deposit" else f"Апгрейд подписки на план {plan_id.upper()}"

            msg = (
                "💳 <b>Поступил новый платеж через Atmos!</b>\n\n"
                f"💵 <b>Сумма:</b> <b>${amount_usd:.2f} USD</b> ({amount_uzs:,} UZS)\n"
                f"🎯 <b>Назначение:</b> {purpose_title}\n"
                f"💳 <b>Карта:</b> <code>{card_masked}</code>\n"
                f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n\n"
                "✅ <i>Средства моментально зачислены и услуга активирована.</i>"
            )
            return cls.send_message(msg)
        except Exception as e:
            logger.warning(f"Error formatting payment notification: {e}")
            return False

    @classmethod
    def notify_admin_campaign_moderated(cls, campaign_name: str, status: str, note: str = "") -> bool:
        """Notify admin channel when a campaign is approved or rejected."""
        try:
            status_emoji = "✅ Одобрена" if status == "approved" else "❌ Отклонена"
            msg = (
                f"🛡 <b>Статус модерации обновлен:</b> {status_emoji}\n\n"
                f"🏷 <b>Кампания:</b> {campaign_name}\n"
            )
            if note:
                msg += f"💬 <b>Причина/комментарий:</b> {note}\n"
            return cls.send_message(msg)
        except Exception as e:
            logger.warning(f"Error formatting campaign moderation notification: {e}")
            return False
