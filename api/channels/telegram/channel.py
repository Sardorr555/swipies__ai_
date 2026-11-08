from __future__ import annotations

import logging
import os
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from telegram import ReplyParameters, Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from ..core.base import Channel, IncomingMessage, OutgoingMessage
from ..core.registry import register_channel

LOGGER = logging.getLogger(__name__)


@dataclass
class TelegramAccount:
    account_id: str
    token: str


def _chat_type(chat) -> str:
    t = getattr(chat, "type", "")
    if t == "private":
        return "p2p"
    if t in ("group", "supergroup"):
        return "group"
    if t == "channel":
        return "channel"
    return str(t) or "unknown"


class TelegramChannel(Channel):
    channel_id = "telegram"

    def __init__(self, account: TelegramAccount) -> None:
        super().__init__()
        self.account = account
        self.account_id = account.account_id
        self._app: Optional[Application] = None
        self._processed_updates: OrderedDict[int, bool] = OrderedDict()

    def _mark_update_processed(self, update_id: int) -> None:
        if len(self._processed_updates) >= 2000:
            for _ in range(500):
                if self._processed_updates:
                    self._processed_updates.popitem(last=False)
        self._processed_updates[update_id] = True

    async def _send_reply(self, msg, text: str) -> None:
        try:
            if self._app and self._app.bot:
                await self._app.bot.send_message(
                    chat_id=msg.chat.id,
                    text=text,
                    reply_parameters=ReplyParameters(message_id=msg.message_id, allow_sending_without_reply=True),
                )
        except Exception as e:
            LOGGER.error("[telegram:%s] failed to send reply: %s", self.account_id, e)

    async def start(self) -> None:
        self._app = Application.builder().token(self.account.token).build()
        self._app.add_handler(MessageHandler(filters.ALL, self._on_update))
        LOGGER.info("[telegram:%s] starting long-poll", self.account_id)
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)

    async def stop(self) -> None:
        if self._app is None:
            return
        try:
            if self._app.updater and self._app.updater.running:
                await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        except Exception:
            LOGGER.error("[telegram:%s] stop error", self.account_id, exc_info=True)
        finally:
            self._app = None

    async def send(self, message: OutgoingMessage) -> None:
        if self._app is None:
            return
        try:
            chat_id = int(message.chat_id)
        except (TypeError, ValueError):
            LOGGER.error("[telegram:%s] invalid chat_id: %r", self.account_id, message.chat_id)
            return

        reply_parameters = None
        if message.reply_to_message_id:
            try:
                reply_parameters = ReplyParameters(
                    message_id=int(message.reply_to_message_id),
                    allow_sending_without_reply=True,
                )
            except (TypeError, ValueError):
                reply_parameters = None
        try:
            await self._app.bot.send_message(
                chat_id=chat_id,
                text=message.text,
                reply_parameters=reply_parameters,
            )
        except Exception:
            LOGGER.error("[telegram:%s] send failed", self.account_id, exc_info=True)

    async def _on_update(self, update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            if not update or not update.update_id:
                return

            if update.update_id in self._processed_updates:
                LOGGER.debug("[telegram:%s] duplicate update_id %s ignored", self.account_id, update.update_id)
                return

            self._mark_update_processed(update.update_id)

            msg = update.effective_message
            if msg is None or msg.from_user is None or msg.from_user.is_bot:
                return

            text = msg.text or msg.caption or ""

            # Check if this message is a voice or audio note
            voice = getattr(msg, "voice", None)
            audio = getattr(msg, "audio", None)

            if not text and (voice or audio):
                media_item = voice or audio
                from api.db.services.audio_service import (
                    AudioTranscriptionService,
                    MAX_TELEGRAM_AUDIO_SIZE_BYTES,
                    MAX_TELEGRAM_DURATION_SECONDS,
                )
                from api.db.services.chat_channel_service import ChatChannelService

                e, cc = ChatChannelService.get_by_id(self.account_id)
                if not e or not cc:
                    LOGGER.warning("[telegram:%s] channel record not found for voice handling", self.account_id)
                    return

                allowed, sub_msg = AudioTranscriptionService.check_voice_subscription_access(
                    tenant_id=cc.tenant_id,
                    sender_id=str(msg.from_user.id),
                    channel_config=cc.config,
                )
                if not allowed:
                    await self._send_reply(msg, sub_msg)
                    return

                duration = getattr(media_item, "duration", 0) or 0
                if duration > MAX_TELEGRAM_DURATION_SECONDS:
                    await self._send_reply(
                        msg,
                        "🎤 Длительность голосового сообщения превышает 5 минут. Пожалуйста, отправьте более короткую запись или текст.",
                    )
                    return

                file_size = getattr(media_item, "file_size", 0) or 0
                if file_size > MAX_TELEGRAM_AUDIO_SIZE_BYTES:
                    await self._send_reply(
                        msg,
                        "🎤 Размер аудиофайла превышает 20 МБ. Пожалуйста, отправьте файл меньшего размера или текст.",
                    )
                    return

                suffix = ".ogg"
                if audio and getattr(audio, "file_name", None):
                    cand_ext = os.path.splitext(audio.file_name)[-1].lower()
                    if cand_ext:
                        suffix = cand_ext

                temp_audio_file = None
                try:
                    fd, temp_path = tempfile.mkstemp(suffix=suffix)
                    os.close(fd)
                    temp_audio_file = temp_path

                    tg_file = await _ctx.bot.get_file(media_item.file_id)
                    await tg_file.download_to_drive(custom_path=temp_audio_file)

                    success, transcribed_text, code = AudioTranscriptionService.transcribe_audio(
                        tenant_id=cc.tenant_id,
                        audio_path=temp_audio_file,
                        user_id=cc.tenant_id,
                    )
                    if not success:
                        LOGGER.warning(
                            "[telegram:%s] voice transcription failed (code %s): %s",
                            self.account_id,
                            code,
                            transcribed_text,
                        )
                        await self._send_reply(
                            msg,
                            "🎤 Не удалось распознать голосовое сообщение. Пожалуйста, повторите попытку или напишите текстом.",
                        )
                        return

                    text = transcribed_text
                    LOGGER.info(
                        "[telegram:%s] voice message recognized successfully (chars: %d, sender: %s)",
                        self.account_id,
                        len(text),
                        msg.from_user.id,
                    )

                except Exception as down_err:
                    LOGGER.error("[telegram:%s] voice processing error: %s", self.account_id, down_err, exc_info=True)
                    await self._send_reply(
                        msg,
                        "🎤 Произошла ошибка при обработке голосового сообщения. Пожалуйста, отправьте вопрос текстом.",
                    )
                    return
                finally:
                    if temp_audio_file and os.path.exists(temp_audio_file):
                        try:
                            os.remove(temp_audio_file)
                        except Exception as rm_err:
                            LOGGER.debug("[telegram:%s] temp audio cleanup error: %s", self.account_id, rm_err)

            if not (text or "").strip():
                return

            incoming = IncomingMessage(
                channel=self.channel_id,
                account_id=self.account_id,
                chat_id=str(msg.chat.id),
                chat_type=_chat_type(msg.chat),
                message_id=str(msg.message_id),
                sender_id=str(msg.from_user.id),
                text=text,
                raw=update,
            )
            await self._dispatch(incoming)
        except Exception:
            LOGGER.error("[telegram:%s] inbound message handling error", self.account_id, exc_info=True)


def _build(account_id: str, cfg: dict) -> Channel:
    token = cfg.get("token")
    if not token:
        raise ValueError(f"telegram account '{account_id}' is missing token")
    return TelegramChannel(TelegramAccount(account_id=account_id, token=str(token)))


register_channel("telegram", _build)
