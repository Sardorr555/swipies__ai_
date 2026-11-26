"""Telegram analytics tables, separate from platform subscriptions and CRM/Ads."""
from datetime import datetime
from peewee import (Model, CharField, TextField, DateTimeField, BigIntegerField,
                    IntegerField, BooleanField)
from api.db.db_models import DB, JSONField

class AnalyticsModel(Model):
    class Meta:
        database = DB

class TelegramAnalyticsBot(AnalyticsModel):
    id = CharField(max_length=32, primary_key=True)
    channel_id = CharField(max_length=32, index=True)
    tenant_id = CharField(max_length=32, index=True)
    telegram_bot_id = CharField(max_length=32)
    name = CharField(max_length=160)
    username = CharField(max_length=160, default='')
    identity_secret_ciphertext = TextField()
    started_at = DateTimeField(default=datetime.utcnow)
    last_event_at = DateTimeField(null=True)
    last_processed_at = DateTimeField(null=True)
    native_payments_seen = BooleanField(default=False)
    class Meta:
        table_name = 'telegram_analytics_bot'

class TelegramAnalyticsUser(AnalyticsModel):
    id = CharField(max_length=32, primary_key=True)
    bot_id = CharField(max_length=32, index=True)
    user_key = CharField(max_length=64)
    first_seen = DateTimeField(index=True)
    last_seen = DateTimeField()
    class Meta:
        table_name = 'telegram_analytics_user'
        indexes = ((('bot_id', 'user_key'), True),)

class TelegramAnalyticsConnection(AnalyticsModel):
    channel_id = CharField(max_length=32, primary_key=True)
    bot_id = CharField(max_length=32)
    tenant_id = CharField(max_length=32)
    class Meta:
        table_name = 'telegram_analytics_connection'

class TelegramAnalyticsChat(AnalyticsModel):
    id = CharField(max_length=32, primary_key=True)
    bot_id = CharField(max_length=32, index=True)
    chat_key = CharField(max_length=64)
    kind = CharField(max_length=20)
    label = CharField(max_length=160)
    first_seen = DateTimeField()
    last_seen = DateTimeField(index=True)
    class Meta:
        table_name = 'telegram_analytics_chat'
        indexes = ((('bot_id', 'chat_key'), True),)

class TelegramAnalyticsEvent(AnalyticsModel):
    """Durable SQL outbox and deduplicated event ledger. Contains no message text."""
    id = CharField(max_length=64, primary_key=True)
    bot_id = CharField(max_length=32, index=True)
    kind = CharField(max_length=24)
    user_key = CharField(max_length=64, null=True)
    chat_key = CharField(max_length=64, null=True)
    occurred_at = DateTimeField(index=True)
    payload = JSONField(default=dict)
    processed = BooleanField(default=False, index=True)
    attempts = IntegerField(default=0)
    rejected = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    class Meta:
        table_name = 'telegram_analytics_event'
        indexes = ((('bot_id', 'occurred_at', 'kind'), False),
                   (('bot_id', 'chat_key', 'occurred_at'), False),
                   (('bot_id', 'user_key', 'occurred_at'), False))

class TelegramAnalyticsPaymentSource(AnalyticsModel):
    id = CharField(max_length=32, primary_key=True)
    bot_id = CharField(max_length=32, index=True)
    provider = CharField(max_length=40, default='signed_webhook')
    name = CharField(max_length=100)
    secret_ciphertext = TextField()
    status = CharField(max_length=16, default='pending')
    created_at = DateTimeField(default=datetime.utcnow)
    verified_at = DateTimeField(null=True)
    class Meta:
        table_name = 'telegram_analytics_payment_source'

class TelegramAnalyticsOrder(AnalyticsModel):
    id = CharField(max_length=32, primary_key=True)
    bot_id = CharField(max_length=32, index=True)
    source_id = CharField(max_length=32, index=True)
    user_key = CharField(max_length=64)
    chat_key = CharField(max_length=64, null=True)
    currency = CharField(max_length=3)
    amount_minor = BigIntegerField()
    status = CharField(max_length=20, default='created')
    created_at = DateTimeField(default=datetime.utcnow)
    class Meta:
        table_name = 'telegram_analytics_order'

class TelegramAnalyticsPayment(AnalyticsModel):
    id = CharField(max_length=64, primary_key=True)
    bot_id = CharField(max_length=32, index=True)
    source_id = CharField(max_length=32)
    charge_key = CharField(max_length=64)
    order_id = CharField(max_length=32, unique=True)
    user_key = CharField(max_length=64)
    chat_key = CharField(max_length=64, null=True)
    currency = CharField(max_length=3)
    amount_minor = BigIntegerField()
    paid_at = DateTimeField(index=True)
    class Meta:
        table_name = 'telegram_analytics_payment'
        indexes = ((('bot_id', 'source_id', 'charge_key'), True),
                   (('bot_id', 'paid_at'), False))

class TelegramAnalyticsRefund(AnalyticsModel):
    id = CharField(max_length=64, primary_key=True)
    bot_id = CharField(max_length=32, index=True)
    source_id = CharField(max_length=32)
    charge_key = CharField(max_length=64)
    currency = CharField(max_length=3)
    amount_minor = BigIntegerField()
    refunded_at = DateTimeField(index=True)
    accepted = BooleanField(default=False)
    class Meta:
        table_name = 'telegram_analytics_refund'
        indexes = ((('bot_id', 'source_id', 'charge_key'), False),)

class TelegramAnalyticsShare(AnalyticsModel):
    id = CharField(max_length=32, primary_key=True)
    bot_id = CharField(max_length=32, index=True)
    created_by = CharField(max_length=32)
    token_hash = CharField(max_length=64, unique=True)
    title = CharField(max_length=120)
    settings = JSONField()
    created_at = DateTimeField(default=datetime.utcnow)
    expires_at = DateTimeField(null=True)
    revoked_at = DateTimeField(null=True)
    class Meta:
        table_name = 'telegram_analytics_share'

TABLES = [TelegramAnalyticsBot, TelegramAnalyticsConnection, TelegramAnalyticsUser, TelegramAnalyticsChat,
          TelegramAnalyticsEvent, TelegramAnalyticsPaymentSource, TelegramAnalyticsOrder,
          TelegramAnalyticsPayment, TelegramAnalyticsRefund, TelegramAnalyticsShare]
