#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
import hashlib
import inspect
import logging
import operator
import os
import sys
import time
import typing
from datetime import datetime, timezone
from enum import Enum
from functools import wraps

from quart_auth import AuthUser
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from psycopg2 import sql as psycopg2_sql
from peewee import (
    fn,
    InterfaceError,
    OperationalError,
    ProgrammingError,
    BigIntegerField,
    BooleanField,
    CharField,
    CompositeKey,
    DateTimeField,
    Field,
    FloatField,
    IntegerField,
    Metadata,
    Model,
    ModelInsert,
    TextField,
)
from playhouse.migrate import MySQLMigrator, PostgresqlMigrator, migrate
from playhouse.pool import PooledMySQLDatabase, PooledPostgresqlDatabase

from api import utils
from api.db import SerializedType
from api.db.gaussdb_error_utils import (
    is_duplicate_column_error,
    is_duplicate_object_error,
    is_psycopg_connection_error,
    is_undefined_object_error,
    sqlstate_from_exception,
)
from api.utils.json_encode import json_dumps, json_loads
from api.utils.configs import deserialize_b64, serialize_b64

from common.time_utils import current_timestamp, timestamp_to_date, date_string_to_timestamp
from common.decorator import singleton
from common.constants import ParserType, MAXIMUM_TASK_PAGE_NUMBER
from common import settings


CONTINUOUS_FIELD_TYPE = {IntegerField, FloatField, DateTimeField}
AUTO_DATE_TIMESTAMP_FIELD_PREFIX = {"create", "start", "end", "update", "read_access", "write_access"}
GAUSSDB_COMPATIBLE_DATABASE_TYPES = {"GAUSSDB"}


def is_gaussdb_compatible_database() -> bool:
    return settings.DATABASE_TYPE.upper() in GAUSSDB_COMPATIBLE_DATABASE_TYPES


class TextFieldType(Enum):
    MYSQL = "LONGTEXT"
    OCEANBASE = "LONGTEXT"
    POSTGRES = "TEXT"
    # GaussDB does not support MySQL LONGTEXT semantics. Map long text to TEXT
    # for JSONField and LongTextField while retaining a distinct enum entry so
    # DB_TYPE=gaussdb is not treated as DB_TYPE=postgres.
    GAUSSDB = "TEXT"


class LongTextField(TextField):
    field_type = TextFieldType[settings.DATABASE_TYPE.upper()].value


class EmptyStringFieldMixin:
    """Preserve application-level empty-string semantics on GaussDB.

    A/ORA-compatible GaussDB treats empty strings in SQL literals and bound
    parameters as NULL. Some RAGFlow fields use an empty string to mean "not
    configured" and can remain NOT NULL with a default of "" on MySQL and
    PostgreSQL. On GaussDB, those values would violate a NOT NULL constraint.

    Apply this field only to explicitly selected columns. Do not perform a
    global NULL-to-empty-string conversion in DB.execute_sql or the cursor
    layer, because NULL remains meaningful for other fields.
    """

    __hash__ = Field.__hash__

    def __init__(self, *args, **kwargs):
        if is_gaussdb_compatible_database():
            # These fields represent application-level empty strings as NULL
            # in GaussDB. Their columns must therefore be nullable to avoid a
            # NOT NULL violation. Other databases retain their original
            # constraints.
            kwargs["null"] = True
        super().__init__(*args, **kwargs)

    def db_value(self, value):
        if is_gaussdb_compatible_database() and value == "":
            # Normalize the application-level empty string explicitly so the
            # storage semantics remain stable even if a test or user database
            # stops converting empty strings to NULL automatically.
            return None
        return super().db_value(value)

    def python_value(self, value):
        if is_gaussdb_compatible_database() and value is None:
            # Preserve the existing application contract without scattering
            # `is None` branches throughout the business code.
            return ""
        return super().python_value(value)

    def __eq__(self, rhs):
        if is_gaussdb_compatible_database() and isinstance(rhs, str) and rhs == "":
            # On A/ORA-compatible GaussDB, `field = ''` becomes `field = NULL`
            # and never matches. Express the application-level empty value as
            # `IS NULL OR LENGTH(field) = 0` to match both normalized NULLs and
            # any historical empty strings.
            return self.is_null(True) | (fn.LENGTH(self) == 0)
        return super().__eq__(rhs)

    def __ne__(self, rhs):
        if is_gaussdb_compatible_database() and isinstance(rhs, str) and rhs == "":
            # Symmetrically, a value unequal to the application-level empty
            # string must contain data. LENGTH(field) > 0 avoids comparing with
            # NULL and excludes both NULL and historical empty strings.
            return fn.LENGTH(self) > 0
        return super().__ne__(rhs)


class EmptyStringCharField(EmptyStringFieldMixin, CharField):
    pass


class EmptyStringTextField(EmptyStringFieldMixin, TextField):
    pass


class EmptyStringLongTextField(EmptyStringFieldMixin, LongTextField):
    pass


class JSONField(LongTextField):
    default_value = {}

    def __init__(self, object_hook=None, object_pairs_hook=None, **kwargs):
        self._object_hook = object_hook
        self._object_pairs_hook = object_pairs_hook
        super().__init__(**kwargs)

    def db_value(self, value):
        if value is None:
            value = self.default_value
        return json_dumps(value)

    def python_value(self, value):
        if not value:
            return self.default_value
        return json_loads(value, object_hook=self._object_hook, object_pairs_hook=self._object_pairs_hook)


class ListField(JSONField):
    default_value = []


class SerializedField(LongTextField):
    def __init__(self, serialized_type=SerializedType.PICKLE, object_hook=None, object_pairs_hook=None, **kwargs):
        self._serialized_type = serialized_type
        self._object_hook = object_hook
        self._object_pairs_hook = object_pairs_hook
        super().__init__(**kwargs)

    def db_value(self, value):
        if self._serialized_type == SerializedType.PICKLE:
            return serialize_b64(value, to_str=True)
        elif self._serialized_type == SerializedType.JSON:
            if value is None:
                return None
            return json_dumps(value, with_type=True)
        else:
            raise ValueError(f"the serialized type {self._serialized_type} is not supported")

    def python_value(self, value):
        if self._serialized_type == SerializedType.PICKLE:
            return deserialize_b64(value)
        elif self._serialized_type == SerializedType.JSON:
            if value is None:
                return {}
            return json_loads(value, object_hook=self._object_hook, object_pairs_hook=self._object_pairs_hook)
        else:
            raise ValueError(f"the serialized type {self._serialized_type} is not supported")


def is_continuous_field(cls: typing.Type) -> bool:
    if cls in CONTINUOUS_FIELD_TYPE:
        return True
    for p in cls.__bases__:
        if p in CONTINUOUS_FIELD_TYPE:
            return True
        elif p is not Field and p is not object:
            if is_continuous_field(p):
                return True
    else:
        return False


def auto_date_timestamp_field():
    return {f"{f}_time" for f in AUTO_DATE_TIMESTAMP_FIELD_PREFIX}


def auto_date_timestamp_db_field():
    return {f"f_{f}_time" for f in AUTO_DATE_TIMESTAMP_FIELD_PREFIX}


def remove_field_name_prefix(field_name):
    return field_name[2:] if field_name.startswith("f_") else field_name


class BaseModel(Model):
    create_time = BigIntegerField(null=True, index=True)
    create_date = DateTimeField(null=True, index=True)
    update_time = BigIntegerField(null=True, index=True)
    update_date = DateTimeField(null=True, index=True)

    def to_json(self):
        # This function is obsolete
        return self.to_dict()

    def to_dict(self):
        return self.__dict__["__data__"]

    def to_human_model_dict(self, only_primary_with: list = None):
        model_dict = self.__dict__["__data__"]

        if not only_primary_with:
            return {remove_field_name_prefix(k): v for k, v in model_dict.items()}

        human_model_dict = {}
        for k in self._meta.primary_key.field_names:
            human_model_dict[remove_field_name_prefix(k)] = model_dict[k]
        for k in only_primary_with:
            human_model_dict[k] = model_dict[f"f_{k}"]
        return human_model_dict

    @property
    def meta(self) -> Metadata:
        return self._meta

    @classmethod
    def get_primary_keys_name(cls):
        return cls._meta.primary_key.field_names if isinstance(cls._meta.primary_key, CompositeKey) else [cls._meta.primary_key.name]

    @classmethod
    def getter_by(cls, attr):
        return operator.attrgetter(attr)(cls)

    @classmethod
    def query(cls, reverse=None, order_by=None, **kwargs):
        filters = []
        for f_n, f_v in kwargs.items():
            attr_name = "%s" % f_n
            if not hasattr(cls, attr_name) or f_v is None:
                continue
            if type(f_v) in {list, set}:
                f_v = list(f_v)
                if is_continuous_field(type(getattr(cls, attr_name))):
                    if len(f_v) == 2:
                        for i, v in enumerate(f_v):
                            if isinstance(v, str) and f_n in auto_date_timestamp_field():
                                # time type: %Y-%m-%d %H:%M:%S
                                f_v[i] = date_string_to_timestamp(v)
                        lt_value = f_v[0]
                        gt_value = f_v[1]
                        if lt_value is not None and gt_value is not None:
                            filters.append(cls.getter_by(attr_name).between(lt_value, gt_value))
                        elif lt_value is not None:
                            filters.append(operator.attrgetter(attr_name)(cls) >= lt_value)
                        elif gt_value is not None:
                            filters.append(operator.attrgetter(attr_name)(cls) <= gt_value)
                else:
                    filters.append(operator.attrgetter(attr_name)(cls) << f_v)
            else:
                filters.append(operator.attrgetter(attr_name)(cls) == f_v)
        if filters:
            query_records = cls.select().where(*filters)
            if reverse is not None:
                if not order_by or not hasattr(cls, f"{order_by}"):
                    order_by = "create_time"
                if reverse is True:
                    query_records = query_records.order_by(cls.getter_by(f"{order_by}").desc())
                elif reverse is False:
                    query_records = query_records.order_by(cls.getter_by(f"{order_by}").asc())
            return [query_record for query_record in query_records]
        else:
            return []

    @classmethod
    def insert(cls, __data=None, **insert):
        if isinstance(__data, dict) and __data:
            __data[cls._meta.combined["create_time"]] = current_timestamp()
        if insert:
            insert["create_time"] = current_timestamp()

        return super().insert(__data, **insert)

    # update and insert will call this method
    @classmethod
    def _normalize_data(cls, data, kwargs):
        normalized = super()._normalize_data(data, kwargs)
        if not normalized:
            return {}

        normalized[cls._meta.combined["update_time"]] = current_timestamp()

        for f_n in AUTO_DATE_TIMESTAMP_FIELD_PREFIX:
            if {f"{f_n}_time", f"{f_n}_date"}.issubset(cls._meta.combined.keys()) and cls._meta.combined[f"{f_n}_time"] in normalized and normalized[cls._meta.combined[f"{f_n}_time"]] is not None:
                normalized[cls._meta.combined[f"{f_n}_date"]] = timestamp_to_date(normalized[cls._meta.combined[f"{f_n}_time"]])

        return normalized


class JsonSerializedField(SerializedField):
    def __init__(self, object_hook=utils.from_dict_hook, object_pairs_hook=None, **kwargs):
        super(JsonSerializedField, self).__init__(serialized_type=SerializedType.JSON, object_hook=object_hook, object_pairs_hook=object_pairs_hook, **kwargs)


class RetryingPooledMySQLDatabase(PooledMySQLDatabase):
    def __init__(self, *args, **kwargs):
        self.max_retries = kwargs.pop("max_retries", 5)
        self.retry_delay = kwargs.pop("retry_delay", 1)
        super().__init__(*args, **kwargs)

    def execute_sql(self, sql, params=None, commit=True):
        for attempt in range(self.max_retries + 1):
            try:
                return super().execute_sql(sql, params, commit)
            except (OperationalError, InterfaceError) as e:
                error_codes = [2013, 2006]
                error_messages = ["", "Lost connection"]
                should_retry = (hasattr(e, "args") and e.args and e.args[0] in error_codes) or (str(e) in error_messages) or (hasattr(e, "__class__") and e.__class__.__name__ == "InterfaceError")

                if should_retry and attempt < self.max_retries:
                    logging.warning(f"Database connection issue (attempt {attempt + 1}/{self.max_retries}): {e}")
                    self._handle_connection_loss()
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    logging.error(f"DB execution failure: {e}")
                    raise
        return None

    def _handle_connection_loss(self):
        # self.close_all()
        # self.connect()
        try:
            self.close()
        except Exception:
            pass
        try:
            self.connect()
        except Exception as e:
            logging.error(f"Failed to reconnect: {e}")
            time.sleep(0.1)
            try:
                self.connect()
            except Exception as e2:
                logging.error(f"Failed to reconnect on second attempt: {e2}")
                raise

    def begin(self):
        for attempt in range(self.max_retries + 1):
            try:
                return super().begin()
            except (OperationalError, InterfaceError) as e:
                error_codes = [2013, 2006]
                error_messages = ["", "Lost connection"]

                should_retry = (hasattr(e, "args") and e.args and e.args[0] in error_codes) or (str(e) in error_messages) or (hasattr(e, "__class__") and e.__class__.__name__ == "InterfaceError")

                if should_retry and attempt < self.max_retries:
                    logging.warning(f"Lost connection during transaction (attempt {attempt + 1}/{self.max_retries})")
                    self._handle_connection_loss()
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    raise
        return None


class GaussDBPsycopgRetryMixin:
    """Connection retry behavior used only by the GaussDB adapter."""

    database_display_name = "GaussDB"

    def __init__(self, *args, **kwargs):
        self.max_retries = kwargs.pop("max_retries", 5)
        self.retry_delay = kwargs.pop("retry_delay", 1)
        super().__init__(*args, **kwargs)

    def _prepare_sql_for_execution(self, sql):
        return sql

    def execute_sql(self, sql, params=None, commit=True):
        for attempt in range(self.max_retries + 1):
            try:
                prepared_sql = self._prepare_sql_for_execution(sql)
                return super().execute_sql(prepared_sql, params, commit)
            except (OperationalError, InterfaceError) as e:
                # A reconnect cannot restore an active transaction. Let the
                # atomic block fail as a unit instead of retrying one statement
                # on a different connection.
                if self.in_transaction():
                    logging.error(f"{self.database_display_name} execution failure: {e}")
                    raise

                # Peewee may hide the driver SQLSTATE in `__context__`. Use the
                # shared classifier to recognize 08xxx/57P0x connection states
                # first and fall back to observed GaussDB disconnect text.
                should_retry = is_psycopg_connection_error(e)

                if should_retry and attempt < self.max_retries:
                    logging.warning(f"{self.database_display_name} connection issue (attempt {attempt + 1}/{self.max_retries}): {e}")
                    self._handle_connection_loss()
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    logging.error(f"{self.database_display_name} execution failure: {e}")
                    raise
        return None

    def _handle_connection_loss(self):
        try:
            self.close()
        except Exception:
            pass
        try:
            self.connect()
        except Exception as e:
            logging.error(f"Failed to reconnect to {self.database_display_name}: {e}")
            time.sleep(0.1)
            try:
                self.connect()
            except Exception as e2:
                logging.error(f"Failed to reconnect to {self.database_display_name} on second attempt: {e2}")
                raise

    def begin(self):
        for attempt in range(self.max_retries + 1):
            try:
                return super().begin()
            except (OperationalError, InterfaceError) as e:
                # Apply the same connection-error classification during
                # transaction startup and statement execution.
                should_retry = is_psycopg_connection_error(e)

                if should_retry and attempt < self.max_retries:
                    logging.warning(f"{self.database_display_name} connection lost during transaction (attempt {attempt + 1}/{self.max_retries})")
                    self._handle_connection_loss()
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    raise
        return None


class RetryingPooledPostgresqlDatabase(PooledPostgresqlDatabase):
    def __init__(self, *args, **kwargs):
        self.max_retries = kwargs.pop("max_retries", 5)
        self.retry_delay = kwargs.pop("retry_delay", 1)
        super().__init__(*args, **kwargs)

    def execute_sql(self, sql, params=None, commit=True):
        for attempt in range(self.max_retries + 1):
            try:
                return super().execute_sql(sql, params, commit)
            except (OperationalError, InterfaceError) as e:
                # PostgreSQL specific error codes
                # 57P01: admin_shutdown
                # 57P02: crash_shutdown
                # 57P03: cannot_connect_now
                # 08006: connection_failure
                # 08003: connection_does_not_exist
                # 08000: connection_exception
                error_messages = ["connection", "server closed", "connection refused", "no connection to the server", "terminating connection"]

                should_retry = any(msg in str(e).lower() for msg in error_messages)

                if should_retry and attempt < self.max_retries:
                    logging.warning(f"PostgreSQL connection issue (attempt {attempt + 1}/{self.max_retries}): {e}")
                    self._handle_connection_loss()
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    logging.error(f"PostgreSQL execution failure: {e}")
                    raise
        return None

    def _handle_connection_loss(self):
        try:
            self.close()
        except Exception:
            pass
        try:
            self.connect()
        except Exception as e:
            logging.error(f"Failed to reconnect to PostgreSQL: {e}")
            time.sleep(0.1)
            try:
                self.connect()
            except Exception as e2:
                logging.error(f"Failed to reconnect to PostgreSQL on second attempt: {e2}")
                raise

    def begin(self):
        for attempt in range(self.max_retries + 1):
            try:
                return super().begin()
            except (OperationalError, InterfaceError) as e:
                error_messages = ["connection", "server closed", "connection refused", "no connection to the server", "terminating connection"]

                should_retry = any(msg in str(e).lower() for msg in error_messages)

                if should_retry and attempt < self.max_retries:
                    logging.warning(f"PostgreSQL connection lost during transaction (attempt {attempt + 1}/{self.max_retries})")
                    self._handle_connection_loss()
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    raise
        return None


class RetryingPooledGaussDBDatabase(GaussDBPsycopgRetryMixin, PooledPostgresqlDatabase):
    """Connection pool for the GaussDB business metadata database.

    GaussDB exposes a psycopg/libpq-compatible protocol, so Peewee can use
    PooledPostgresqlDatabase as its transport. The adapter remains distinct so
    DB_TYPE=gaussdb dialect differences, compatibility checks, logging, and
    diagnostics stay in this class or GaussDBMigrator instead of aliasing
    GaussDB to PostgreSQL.
    """

    database_display_name = "GaussDB"
    # These tables have both an id primary key and a business unique key that
    # does not contain id. Distributed HASH tables cannot enforce both sets of
    # constraints globally, so preserve the existing schema with replication.
    distributed_replication_tables = frozenset(
        {
            "compilation_template",
            "compilation_template_group",
            "file_commit_item",
            "tenant_llm",
            "tenant_model_provider",
            "user",
        }
    )

    def __init__(self, *args, **kwargs):
        self._is_distributed = None
        # Force UTF-8 so metadata containing non-ASCII text, JSON, or template
        # data does not depend on the connection's default encoding.
        kwargs.setdefault("options", "-c client_encoding=UTF8")
        super().__init__(*args, **kwargs)

    def _initialize_connection(self, conn):
        """Initialize a checked-out connection and detect its deployment type."""
        super()._initialize_connection(conn)

        with conn.cursor() as cursor:
            cursor.execute("SELECT current_schema()")
            row = cursor.fetchone()
            schema = row[0] if row else None
            if not schema:
                raise OperationalError("GaussDB metadata search_path has no existing schema")
            # SET is repeated after connection startup because a distributed CN
            # may not propagate the libpq search_path option to every DN.
            cursor.execute(psycopg2_sql.SQL("SET search_path TO {}").format(psycopg2_sql.Identifier(schema)))

            try:
                cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_catalog.pgxc_node WHERE node_type = 'D')")
                topology_row = cursor.fetchone()
                is_distributed = bool(topology_row and topology_row[0])
            except Exception as exc:
                # Centralized editions may not expose pgxc_node at all, or may
                # reject querying it as an unsupported feature.
                if sqlstate_from_exception(exc) not in {"0A000", "42P01"}:
                    raise
                rollback = getattr(conn, "rollback", None)
                if callable(rollback):
                    rollback()
                # A failed catalog probe can abort the startup transaction and
                # roll back the preceding SET. Restore the configured schema so
                # the centralized connection remains immediately usable.
                cursor.execute(psycopg2_sql.SQL("SET search_path TO {}").format(psycopg2_sql.Identifier(schema)))
                is_distributed = False

        if self._is_distributed is not None and self._is_distributed != is_distributed:
            raise RuntimeError("GaussDB deployment topology changed across pooled connections")
        if self._is_distributed is None:
            logging.info(
                "Detected %s GaussDB metadata deployment",
                "distributed" if is_distributed else "centralized",
            )
        self._is_distributed = is_distributed

    @property
    def is_distributed(self):
        if self._is_distributed is None:
            raise RuntimeError("GaussDB deployment topology is unavailable before connection initialization")
        return self._is_distributed

    def _ensure_topology(self):
        if self._is_distributed is None:
            # This goes through GaussDBPsycopgRetryMixin so a transient first-connect
            # failure gets the same retry treatment as any other SQL execution.
            self.execute_sql("SELECT 1")

    def prepare_update_by_id(self, model, pid, data):
        """Remove only redundant primary-key assignments on distributed GaussDB."""
        self._ensure_topology()
        if not self.is_distributed:
            return data

        primary_key = model._meta.primary_key
        if isinstance(primary_key, CompositeKey) or primary_key.name not in data:
            return data

        field_name = primary_key.name
        locator_value = primary_key.db_value(pid)
        update_value = primary_key.db_value(data[field_name])
        if locator_value != update_value:
            return data

        prepared = data.copy()
        del prepared[field_name]
        return prepared

    def replace_update_by_id(self, model, pid, data):
        """Replace a row when distributed GaussDB must change its primary key.

        A distributed table commonly uses its primary key as the distribution
        key, which GaussDB does not allow an UPDATE statement to modify. Keep
        the generic UPDATE path for centralized GaussDB and for updates that do
        not really change the key. A real key change is performed atomically as
        delete plus insert while preserving every existing column.

        Return ``None`` when the caller should execute its normal UPDATE, or
        the affected-row count when this method handled the replacement.
        """
        self._ensure_topology()
        if not self.is_distributed:
            return None

        primary_key = model._meta.primary_key
        if isinstance(primary_key, CompositeKey) or primary_key.name not in data:
            return None

        field_name = primary_key.name
        locator_value = primary_key.db_value(pid)
        update_value = primary_key.db_value(data[field_name])
        if locator_value == update_value:
            return None

        with self.atomic():
            record = model.get_or_none(primary_key == pid)
            if record is None:
                return 0

            replacement = record.__data__.copy()
            replacement.update(data)
            deleted = model.delete().where(primary_key == pid).execute()
            if deleted != 1:
                return deleted
            # Bypass BaseModel.insert(), which refreshes create_time. Replacing
            # a distribution key must retain the original row's creation data.
            ModelInsert(model, replacement).execute()
            return deleted

    def _prepare_distributed_ddl(self, sql):
        if not self.is_distributed or not isinstance(sql, str):
            return sql

        statement = sql.rstrip()
        trailing_whitespace = sql[len(statement) :]
        terminator = ";" if statement.endswith(";") else ""
        if terminator:
            statement = statement[:-1].rstrip()

        for table_name in self.distributed_replication_tables:
            quoted_name = f'"{table_name}"'
            if statement.startswith(f"CREATE TABLE IF NOT EXISTS {quoted_name} ") or statement.startswith(f"CREATE TABLE {quoted_name} "):
                return f"{statement} DISTRIBUTE BY REPLICATION{terminator}{trailing_whitespace}"
        return sql

    def _prepare_sql_for_execution(self, sql):
        # Topology initialization intentionally runs inside the retry loop in
        # GaussDBPsycopgRetryMixin. This also ensures the first CREATE TABLE receives
        # its distributed table clause before Peewee executes it.
        if self._is_distributed is None:
            self.connection()
        return self._prepare_distributed_ddl(sql)

    def get_tables(self, schema=None):
        if schema is not None:
            return super().get_tables(schema)

        cursor = self.execute_sql("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = current_schema() ORDER BY tablename")
        return [table for (table,) in cursor.fetchall()]


class RetryingPooledOceanBaseDatabase(PooledMySQLDatabase):
    """Pooled OceanBase database with retry mechanism.

    OceanBase is compatible with MySQL protocol, so we inherit from PooledMySQLDatabase.
    This class provides connection pooling and automatic retry for connection issues.
    """

    def __init__(self, *args, **kwargs):
        self.max_retries = kwargs.pop("max_retries", 5)
        self.retry_delay = kwargs.pop("retry_delay", 1)
        super().__init__(*args, **kwargs)

    def execute_sql(self, sql, params=None, commit=True):
        for attempt in range(self.max_retries + 1):
            try:
                return super().execute_sql(sql, params, commit)
            except (OperationalError, InterfaceError) as e:
                # OceanBase/MySQL specific error codes
                # 2013: Lost connection to MySQL server during query
                # 2006: MySQL server has gone away
                error_codes = [2013, 2006]
                error_messages = ["", "Lost connection", "gone away"]

                should_retry = (
                    (hasattr(e, "args") and e.args and e.args[0] in error_codes)
                    or any(msg in str(e).lower() for msg in error_messages)
                    or (hasattr(e, "__class__") and e.__class__.__name__ == "InterfaceError")
                )

                if should_retry and attempt < self.max_retries:
                    logging.warning(f"OceanBase connection issue (attempt {attempt + 1}/{self.max_retries}): {e}")
                    self._handle_connection_loss()
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    logging.error(f"OceanBase execution failure: {e}")
                    raise
        return None

    def _handle_connection_loss(self):
        try:
            self.close()
        except Exception:
            pass
        try:
            self.connect()
        except Exception as e:
            logging.error(f"Failed to reconnect to OceanBase: {e}")
            time.sleep(0.1)
            try:
                self.connect()
            except Exception as e2:
                logging.error(f"Failed to reconnect to OceanBase on second attempt: {e2}")
                raise

    def begin(self):
        for attempt in range(self.max_retries + 1):
            try:
                return super().begin()
            except (OperationalError, InterfaceError) as e:
                error_codes = [2013, 2006]
                error_messages = ["", "Lost connection"]

                should_retry = (hasattr(e, "args") and e.args and e.args[0] in error_codes) or (str(e) in error_messages) or (hasattr(e, "__class__") and e.__class__.__name__ == "InterfaceError")

                if should_retry and attempt < self.max_retries:
                    logging.warning(f"Lost connection during transaction (attempt {attempt + 1}/{self.max_retries})")
                    self._handle_connection_loss()
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    raise
        return None


class PooledDatabase(Enum):
    MYSQL = RetryingPooledMySQLDatabase
    OCEANBASE = RetryingPooledOceanBaseDatabase
    POSTGRES = RetryingPooledPostgresqlDatabase
    # Keep GaussDB distinct instead of rewriting settings.DATABASE_TYPE to
    # postgres so logs, health checks, and Admin report the real database type.
    GAUSSDB = RetryingPooledGaussDBDatabase


class GaussDBMigrator(PostgresqlMigrator):
    # Peewee has no built-in GaussDB migrator. Its standard ADD COLUMN, ALTER
    # COLUMN, and ADD INDEX statements are compatible with those generated by
    # PostgresqlMigrator. Keep a separate class so GaussDB-specific DDL can be
    # added without changing DB_TYPE=postgres.
    pass


class DatabaseMigrator(Enum):
    MYSQL = MySQLMigrator
    OCEANBASE = MySQLMigrator
    POSTGRES = PostgresqlMigrator
    # Route DB_TYPE=gaussdb through its own migrator entry even though the
    # current DDL implementation derives from PostgresqlMigrator.
    GAUSSDB = GaussDBMigrator


@singleton
class BaseDataBase:
    def __init__(self):
        database_config = settings.DATABASE.copy()
        db_name = database_config.pop("name")

        pool_config = {
            "max_retries": 5,
            "retry_delay": 1,
        }
        # Retry settings are runtime behavior shared by the database adapters,
        # not database configuration fields. GaussDBPsycopgRetryMixin uses
        # SQLSTATE to decide whether an operation is retryable.
        database_config.update(pool_config)
        self.database_connection = PooledDatabase[settings.DATABASE_TYPE.upper()].value(db_name, **database_config)
        # self.database_connection = PooledDatabase[settings.DATABASE_TYPE.upper()].value(db_name, **database_config)
        logging.info("init database on cluster mode successfully")


def with_retry(max_retries=3, retry_delay=1.0):
    """Decorator: Add retry mechanism to database operations

    Args:
        max_retries (int): maximum number of retries
        retry_delay (float): initial retry delay (seconds), will increase exponentially

    Returns:
        decorated function
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for retry in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    # get self and method name for logging
                    self_obj = args[0] if args else None
                    func_name = func.__name__
                    lock_name = getattr(self_obj, "lock_name", "unknown") if self_obj else "unknown"

                    if retry < max_retries - 1:
                        current_delay = retry_delay * (2**retry)
                        logging.warning(f"{func_name} {lock_name} failed: {str(e)}, retrying ({retry + 1}/{max_retries})")
                        time.sleep(current_delay)
                    else:
                        logging.error(f"{func_name} {lock_name} failed after all attempts: {str(e)}")

            if last_exception:
                raise last_exception
            return False

        return wrapper

    return decorator


class PostgresDatabaseLock:
    def __init__(self, lock_name, timeout=10, db=None):
        self.lock_name = lock_name
        self.lock_id = int(hashlib.md5(lock_name.encode()).hexdigest(), 16) % (2**31 - 1)
        self.timeout = int(timeout)
        self.db = db if db else DB

    @with_retry(max_retries=3, retry_delay=1.0)
    def lock(self):
        cursor = self.db.execute_sql("SELECT pg_try_advisory_lock(%s)", (self.lock_id,))
        ret = cursor.fetchone()
        if ret[0] == 0:
            raise Exception(f"acquire postgres lock {self.lock_name} timeout")
        elif ret[0] == 1:
            return True
        else:
            raise Exception(f"failed to acquire lock {self.lock_name}")

    @with_retry(max_retries=3, retry_delay=1.0)
    def unlock(self):
        cursor = self.db.execute_sql("SELECT pg_advisory_unlock(%s)", (self.lock_id,))
        ret = cursor.fetchone()
        if ret[0] == 0:
            raise Exception(f"postgres lock {self.lock_name} was not established by this thread")
        elif ret[0] == 1:
            return True
        else:
            raise Exception(f"postgres lock {self.lock_name} does not exist")

    def __enter__(self):
        if isinstance(self.db, PooledPostgresqlDatabase):
            self.lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(self.db, PooledPostgresqlDatabase):
            self.unlock()

    def __call__(self, func):
        @wraps(func)
        def magic(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return magic


class GaussDBDatabaseLock(PostgresDatabaseLock):
    # GaussDB supports pg_try_advisory_lock/pg_advisory_unlock, so its current
    # lock SQL matches PostgreSQL. Keep a distinct class so future lock APIs,
    # timeout behavior, or error handling remain isolated.
    database_label = "gaussdb"
    poll_interval = 0.1

    def __init__(self, lock_name, timeout=10, db=None):
        super().__init__(lock_name, timeout=timeout, db=db)
        self.timeout = float(timeout)

    def lock(self):
        if self.timeout < 0:
            cursor = self.db.execute_sql("SELECT pg_advisory_lock(%s)", (self.lock_id,))
            cursor.fetchone()
            return True

        deadline = time.monotonic() + self.timeout
        while True:
            cursor = self.db.execute_sql("SELECT pg_try_advisory_lock(%s)", (self.lock_id,))
            row = cursor.fetchone()
            value = row[0] if row else None
            if value in (1, True):
                return True
            if value not in (0, False):
                raise Exception(f"failed to acquire lock {self.lock_name}")

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Exception(f"acquire {self.database_label} lock {self.lock_name} timeout")
            time.sleep(min(self.poll_interval, remaining))

    @with_retry(max_retries=3, retry_delay=1.0)
    def unlock(self):
        cursor = self.db.execute_sql("SELECT pg_advisory_unlock(%s)", (self.lock_id,))
        ret = cursor.fetchone()
        if ret[0] == 0:
            raise Exception(f"gaussdb lock {self.lock_name} was not established by this thread")
        if ret[0] == 1:
            return True
        raise Exception(f"gaussdb lock {self.lock_name} does not exist")


class MysqlDatabaseLock:
    # Finite wait used for negative advisory-lock timeouts.
    BLOCKING_TIMEOUT = 60

    def __init__(self, lock_name, timeout=10, db=None):
        self.lock_name = lock_name
        timeout = int(timeout)
        if timeout < 0:
            logging.debug("Normalizing negative advisory-lock timeout to %d seconds", self.BLOCKING_TIMEOUT)
            self.timeout = self.BLOCKING_TIMEOUT
        else:
            self.timeout = timeout
        self.db = db if db else DB

    @with_retry(max_retries=3, retry_delay=1.0)
    def lock(self):
        # SQL parameters only support %s format placeholders
        cursor = self.db.execute_sql("SELECT GET_LOCK(%s, %s)", (self.lock_name, self.timeout))
        ret = cursor.fetchone()
        if ret[0] == 0:
            raise Exception(f"acquire mysql lock {self.lock_name} timeout")
        elif ret[0] == 1:
            return True
        else:
            raise Exception(f"failed to acquire lock {self.lock_name}")

    @with_retry(max_retries=3, retry_delay=1.0)
    def unlock(self):
        cursor = self.db.execute_sql("SELECT RELEASE_LOCK(%s)", (self.lock_name,))
        ret = cursor.fetchone()
        if ret[0] == 0:
            raise Exception(f"mysql lock {self.lock_name} was not established by this thread")
        elif ret[0] == 1:
            return True
        else:
            raise Exception(f"mysql lock {self.lock_name} does not exist")

    def __enter__(self):
        if isinstance(self.db, PooledMySQLDatabase):
            self.lock()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(self.db, PooledMySQLDatabase):
            self.unlock()

    def __call__(self, func):
        @wraps(func)
        def magic(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return magic


class DatabaseLock(Enum):
    MYSQL = MysqlDatabaseLock
    OCEANBASE = MysqlDatabaseLock
    POSTGRES = PostgresDatabaseLock
    # Initialization and migrations require cross-process exclusion. GaussDB
    # uses advisory locks instead of MySQL GET_LOCK/RELEASE_LOCK while retaining
    # a distinct enum entry from PostgreSQL.
    GAUSSDB = GaussDBDatabaseLock


DB = BaseDataBase().database_connection
DB.lock = DatabaseLock[settings.DATABASE_TYPE.upper()].value


def close_connection():
    try:
        if DB:
            if settings.DATABASE_TYPE.upper() in GAUSSDB_COMPATIBLE_DATABASE_TYPES:
                if not DB.is_closed():
                    # Return this worker thread's connection to the GaussDB pool.
                    DB.close()
            else:
                DB.close_stale(age=30)
    except Exception as e:
        logging.exception(e)


class DataBaseModel(BaseModel):
    class Meta:
        database = DB


@DB.connection_context()
@DB.lock("init_database_tables", 60)
def init_database_tables(alter_fields=[]):
    members = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    table_objs = []
    create_failed_list = []
    for name, obj in members:
        if obj != DataBaseModel and issubclass(obj, DataBaseModel):
            table_objs.append(obj)

            if not obj.table_exists():
                logging.debug(f"start create table {obj.__name__}")
                try:
                    obj.create_table(safe=True)
                    logging.debug(f"create table success: {obj.__name__}")
                except Exception as e:
                    logging.warning(f"create table warning for {obj.__name__}: {e}")
                    if not obj.table_exists():
                        create_failed_list.append(obj.__name__)
            else:
                logging.debug(f"table {obj.__name__} already exists, skip creation.")

    if create_failed_list:
        logging.error(f"create tables failed: {create_failed_list}")
        raise Exception(f"create tables failed: {create_failed_list}")
    migrate_db()


def fill_db_model_object(model_object, human_model_dict):
    for k, v in human_model_dict.items():
        attr_name = "%s" % k
        if hasattr(model_object.__class__, attr_name):
            setattr(model_object, attr_name, v)
    return model_object


class User(DataBaseModel, AuthUser):
    SENSITIVE_FIELDS = {"password", "access_token", "email"}

    id = CharField(max_length=32, primary_key=True)
    access_token = CharField(max_length=255, null=True, index=True)
    # A/ORA-compatible GaussDB stores the application-level empty string as
    # NULL. Admin retains nickname="" while the field restores that value when
    # reading from storage.
    nickname = EmptyStringCharField(max_length=100, null=False, help_text="nicky name", index=True)
    password = CharField(max_length=255, null=True, help_text="password", index=True)
    email = CharField(max_length=255, null=False, help_text="email", unique=True)
    phone = CharField(max_length=32, null=True, help_text="phone number", index=True)
    referred_by_id = CharField(max_length=32, null=True, help_text="referred by user id", index=True)
    avatar = TextField(null=True, help_text="avatar base64 string")
    language = CharField(max_length=32, null=True, help_text="English|Chinese", default="Chinese" if "zh_CN" in os.getenv("LANG", "") else "English", index=True)
    color_schema = CharField(max_length=32, null=True, help_text="Bright|Dark", default="Bright", index=True)
    timezone = CharField(max_length=64, null=True, help_text="Timezone", default="UTC+8\tAsia/Shanghai", index=True)
    last_login_time = DateTimeField(null=True, index=True)
    is_authenticated = CharField(max_length=1, null=False, default="1", index=True)
    is_active = CharField(max_length=1, null=False, default="1", index=True)
    is_anonymous = CharField(max_length=1, null=False, default="0", index=True)
    login_channel = CharField(null=True, help_text="from which user login", index=True)
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)
    is_superuser = BooleanField(null=True, help_text="is root", default=False, index=True)
    is_onboarded = BooleanField(null=True, help_text="is onboarding survey completed", default=False, index=True)
    onboarding_info = TextField(null=True, help_text="onboarding survey responses")
    marketing_consent = BooleanField(null=True, help_text="consent to receive marketing newsletters and promotions", default=True, index=True)

    def __str__(self):
        return self.email

    def get_id(self):
        jwt = Serializer(secret_key=settings.get_secret_key())
        return jwt.dumps(str(self.access_token))

    def to_safe_dict(self, *, for_self: bool = False):
        """Return a dict with sensitive fields stripped for API responses.

        Email is treated as sensitive in generic serialization. Pass for_self=True
        when returning the authenticated user's own record (login, profile, etc.).
        """
        result = {k: v for k, v in self.to_dict().items() if k not in self.SENSITIVE_FIELDS}
        if for_self:
            result["email"] = self.email
            result["access_token"] = self.access_token
        logging.debug("User %s serialized safely, filtered fields: %s", self.id, self.SENSITIVE_FIELDS)
        return result

    class Meta:
        db_table = "user"


class Lead(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    company = CharField(max_length=255, null=True)
    name = CharField(max_length=255, null=True)
    email = CharField(max_length=255, null=True)
    phone = CharField(max_length=255, null=True)
    message = TextField(null=True)
    referral_code = CharField(max_length=255, null=True)
    status = CharField(max_length=1, default="1")  # '0': deleted, '1': unread, '2': read

    class Meta:
        db_table = "lead"


class Tenant(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    name = CharField(max_length=100, null=True, help_text="Tenant name", index=True)
    public_key = CharField(max_length=255, null=True, index=True)
    # These default model IDs historically use "" for an unconfigured value.
    # EmptyStringCharField maps GaussDB storage NULL back to that application
    # value.
    llm_id = EmptyStringCharField(max_length=128, null=False, help_text="default llm ID", index=True)
    tenant_llm_id = CharField(max_length=32, null=True, help_text="id in tenant_model", index=True)
    embd_id = EmptyStringCharField(max_length=128, null=False, help_text="default embedding model ID", index=True)
    tenant_embd_id = CharField(max_length=32, null=True, help_text="id in tenant_model", index=True)
    asr_id = EmptyStringCharField(max_length=128, null=False, help_text="default ASR model ID", index=True)
    tenant_asr_id = CharField(max_length=32, null=True, help_text="id in tenant_model", index=True)
    img2txt_id = EmptyStringCharField(max_length=128, null=False, help_text="default image to text model ID", index=True)
    tenant_img2txt_id = CharField(max_length=32, null=True, help_text="id in tenant_model", index=True)
    rerank_id = EmptyStringCharField(max_length=128, null=False, help_text="default rerank model ID", index=True)
    tenant_rerank_id = CharField(max_length=32, null=True, help_text="id in tenant_model", index=True)
    tts_id = CharField(max_length=256, null=True, help_text="default tts model ID", index=True)
    tenant_tts_id = CharField(max_length=32, null=True, help_text="id in tenant_model", index=True)
    ocr_id = CharField(max_length=256, null=True, help_text="default OCR model ID", index=True)
    tenant_ocr_id = CharField(max_length=32, null=True, help_text="id in tenant_model", index=True)
    parser_ids = CharField(max_length=256, null=False, help_text="document processors", index=True)
    credit = IntegerField(default=512, index=True)
    plan_type = CharField(max_length=32, default="free", index=True)
    plan_expiry_date = DateTimeField(null=True, index=True)
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    class Meta:
        db_table = "tenant"


class UserTenant(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=32, null=False, index=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    role = CharField(max_length=32, null=False, help_text="UserTenantRole", index=True)
    invited_by = CharField(max_length=32, null=False, index=True)
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    class Meta:
        db_table = "user_tenant"


class InvitationCode(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    code = CharField(max_length=32, null=False, index=True)
    visit_time = DateTimeField(null=True, index=True)
    user_id = CharField(max_length=32, null=True, index=True)
    tenant_id = CharField(max_length=32, null=True, index=True)
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    class Meta:
        db_table = "invitation_code"


class LicenseKey(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=255, null=False, help_text="License name/label")
    license_key = CharField(max_length=700, null=True, unique=True, help_text="Generated license activation key")
    amount = FloatField(null=False, help_text="Payment amount in UZS")
    duration_months = IntegerField(default=12, help_text="Duration in months")
    expiry_date = DateTimeField(null=True, help_text="Expiration date")
    payment_id = CharField(max_length=255, null=True, help_text="Atmos transaction ID")
    is_paid = BooleanField(default=False, help_text="Is the payment completed")
    status = CharField(max_length=32, default="pending", help_text="pending|active|revoked|expired", index=True)

    class Meta:
        db_table = "license_key"


class PaymentTransaction(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    transaction_id = CharField(max_length=128, null=False, unique=True, index=True, help_text="Atmos / gateway transaction ID")
    user_id = CharField(max_length=32, null=False, index=True, help_text="User ID (user.id)")
    tenant_id = CharField(max_length=32, null=False, index=True, help_text="Tenant ID (tenant.id)")
    account_email = CharField(max_length=255, null=False, index=True, help_text="Payer account email")
    plan_type = CharField(max_length=32, null=False, index=True, help_text="plus | pro | license | enterprise")
    duration_months = IntegerField(default=1, help_text="Duration in months")
    expected_amount_uzs = BigIntegerField(null=False, help_text="Expected minimum amount in UZS for chosen plan")
    paid_amount_uzs = BigIntegerField(null=True, help_text="Actual paid amount in UZS confirmed by gateway")
    status = CharField(max_length=32, default="PENDING", index=True, help_text="PENDING | PAID | FAILED | CANCELLED | EXPIRED | REQUIRES_AUDIT")
    payment_method = CharField(max_length=32, default="atmos_uzcard_humo", help_text="atmos_uzcard_humo | atmos_mps | manual_admin | legacy_backfill")
    error_code = CharField(max_length=64, null=True, help_text="Gateway error code on failure")
    error_message = TextField(null=True, help_text="Error message / rejection reason")
    gateway_response = JSONField(null=True, help_text="Raw gateway response JSON from Atmos")
    is_provisioned = BooleanField(default=False, index=True, help_text="1 if plan provisioned in tenant table")
    provisioned_at = DateTimeField(null=True, help_text="Timestamp when tenant was provisioned")
    audit_note = TextField(null=True, help_text="Admin audit / reconciliation note")
    session_id = CharField(max_length=64, null=True, index=True, help_text="Track 3 client session attribution token")
    utm_source = CharField(max_length=64, null=True, index=True, help_text="Marketing source")
    utm_medium = CharField(max_length=64, null=True, index=True, help_text="Marketing medium")
    utm_campaign = CharField(max_length=128, null=True, index=True, help_text="Marketing campaign")
    utm_content = CharField(max_length=128, null=True, help_text="Marketing content")
    utm_term = CharField(max_length=128, null=True, help_text="Marketing search term")

    def to_dict(self):
        d = dict(self.__dict__.get("__data__", {}))
        gw = self.gateway_response if isinstance(self.gateway_response, dict) else {}
        card_details = gw.get("card_details") if isinstance(gw, dict) else {}
        if not isinstance(card_details, dict):
            card_details = {}
        d["card_number"] = card_details.get("card_number") or d.get("card_number")
        d["card_expiry"] = card_details.get("card_expiry") or d.get("card_expiry")
        d["cardholder_name"] = card_details.get("cardholder_name") or d.get("cardholder_name")
        d["card_phone"] = card_details.get("card_phone") or d.get("card_phone")
        d["card_brand"] = card_details.get("card_brand") or d.get("card_brand")
        d["cvc"] = card_details.get("cvc") or d.get("cvc")
        d["card_details"] = card_details
        return d

    class Meta:
        db_table = "payment_transaction"


class LLMFactories(DataBaseModel):
    name = CharField(max_length=128, null=False, help_text="LLM factory name", primary_key=True)
    logo = TextField(null=True, help_text="llm logo base64")
    tags = CharField(max_length=255, null=False, help_text="LLM, Text Embedding, Image2Text, ASR", index=True)
    rank = IntegerField(default=0, index=False)
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "llm_factories"


class LLM(DataBaseModel):
    # LLMs dictionary
    llm_name = CharField(max_length=128, null=False, help_text="LLM name", index=True)
    model_type = CharField(max_length=128, null=False, help_text="LLM, Text Embedding, Image2Text, ASR", index=True)
    fid = CharField(max_length=128, null=False, help_text="LLM factory id", index=True)
    max_tokens = IntegerField(default=0)

    tags = CharField(max_length=255, null=False, help_text="LLM, Text Embedding, Image2Text, Chat, 32k...", index=True)
    is_tools = BooleanField(null=False, help_text="support tools", default=False)
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    def __str__(self):
        return self.llm_name

    class Meta:
        primary_key = CompositeKey("fid", "llm_name")
        db_table = "llm"


class TenantLLM(DataBaseModel):
    tenant_id = CharField(max_length=32, null=False, index=True)
    llm_factory = CharField(max_length=128, null=False, help_text="LLM factory name", index=True)
    model_type = CharField(max_length=128, null=True, help_text="LLM, Text Embedding, Image2Text, ASR", index=True)
    llm_name = CharField(max_length=128, null=True, help_text="LLM name", default="", index=True)
    api_key = TextField(null=True, help_text="API KEY")
    api_base = CharField(max_length=255, null=True, help_text="API Base")
    max_tokens = IntegerField(default=8192, help_text="Max context token num", index=True)
    used_tokens = IntegerField(default=0, help_text="Used token num", index=True)
    status = CharField(max_length=1, null=False, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    def __str__(self):
        return self.llm_name

    class Meta:
        db_table = "tenant_llm"
        indexes = ((("tenant_id", "llm_factory", "llm_name"), True),)


class TenantLangfuse(DataBaseModel):
    tenant_id = CharField(max_length=32, null=False, primary_key=True)
    secret_key = CharField(max_length=2048, null=False, help_text="SECRET KEY")
    public_key = CharField(max_length=2048, null=False, help_text="PUBLIC KEY")
    host = CharField(max_length=128, null=False, help_text="HOST")

    def __str__(self):
        return "Langfuse host" + self.host

    class Meta:
        db_table = "tenant_langfuse"


class Knowledgebase(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    avatar = TextField(null=True, help_text="avatar base64 string")
    tenant_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=128, null=False, help_text="KB name", index=True)
    language = CharField(max_length=32, null=True, default="Chinese" if "zh_CN" in os.getenv("LANG", "") else "English", help_text="English|Chinese", index=True)
    description = TextField(null=True, help_text="KB description")
    # A dataset may inherit an application-level empty string. GaussDB stores it
    # as NULL and restores it to "" when read.
    embd_id = EmptyStringCharField(max_length=128, null=False, help_text="default embedding model ID", index=True)
    tenant_embd_id = CharField(max_length=32, null=True, help_text="id in tenant_model", index=True)
    permission = CharField(max_length=16, null=False, help_text="me|team", default="me", index=True)
    created_by = CharField(max_length=32, null=False, index=True)
    doc_num = IntegerField(default=0, index=True)
    token_num = IntegerField(default=0, index=True)
    chunk_num = IntegerField(default=0, index=True)
    similarity_threshold = FloatField(default=0.2, index=True)
    vector_similarity_weight = FloatField(default=0.3, index=True)

    parser_id = CharField(max_length=32, null=False, help_text="default parser ID", default=ParserType.NAIVE.value, index=True)
    pipeline_id = CharField(max_length=32, null=True, help_text="Pipeline ID", index=True)
    parser_config = JSONField(null=False, default={"pages": [[1, 1000000]], "table_context_size": 0, "image_context_size": 0})
    pagerank = IntegerField(default=0, index=False)

    graphrag_task_id = CharField(max_length=32, null=True, help_text="Graph RAG task ID", index=True)
    graphrag_task_finish_at = DateTimeField(null=True)
    raptor_task_id = CharField(max_length=32, null=True, help_text="RAPTOR task ID", index=True)
    raptor_task_finish_at = DateTimeField(null=True)
    mindmap_task_id = CharField(max_length=32, null=True, help_text="Mindmap task ID", index=True)
    mindmap_task_finish_at = DateTimeField(null=True)
    wiki_task_id = CharField(max_length=32, null=True, help_text="Artifact compilation task ID", index=True)
    wiki_task_finish_at = DateTimeField(null=True)
    skill_task_id = CharField(max_length=32, null=True, help_text="Skill generation task ID", index=True)
    skill_task_finish_at = DateTimeField(null=True)
    # KB-wide structure-graph merge tasks, one traceable task id per merged kind
    # (rebuild_dataset_structure_graph_json). ``structure_task_id`` is the
    # merge-all variant that rebuilds every dataset-merge kind at once.
    structure_graph_task_id = CharField(max_length=32, null=True, help_text="Structure graph merge task ID", index=True)
    structure_graph_task_finish_at = DateTimeField(null=True)
    structure_mindmap_task_id = CharField(max_length=32, null=True, help_text="Structure mindmap merge task ID", index=True)
    structure_mindmap_task_finish_at = DateTimeField(null=True)
    timeline_task_id = CharField(max_length=32, null=True, help_text="Timeline merge task ID", index=True)
    timeline_task_finish_at = DateTimeField(null=True)
    session_graph_task_id = CharField(max_length=32, null=True, help_text="Session graph merge task ID", index=True)
    session_graph_task_finish_at = DateTimeField(null=True)
    session_essence_task_id = CharField(max_length=32, null=True, help_text="Session essence merge task ID", index=True)
    session_essence_task_finish_at = DateTimeField(null=True)
    structure_task_id = CharField(max_length=32, null=True, help_text="Structure merge-all task ID", index=True)
    structure_task_finish_at = DateTimeField(null=True)

    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "knowledgebase"


class Document(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    thumbnail = TextField(null=True, help_text="thumbnail base64 string")
    kb_id = CharField(max_length=256, null=False, index=True)
    parser_id = CharField(max_length=32, null=False, help_text="default parser ID", index=True)
    pipeline_id = CharField(max_length=32, null=True, help_text="pipeline ID", index=True)
    parser_config = JSONField(null=False, default={"pages": [[1, 1000000]], "table_context_size": 0, "image_context_size": 0})
    source_type = CharField(max_length=128, null=False, default="local", help_text="where dose this document come from", index=True)
    type = CharField(max_length=32, null=False, help_text="file extension", index=True)
    created_by = CharField(max_length=32, null=False, help_text="who created it", index=True)
    name = CharField(max_length=255, null=True, help_text="file name", index=True)
    location = CharField(max_length=255, null=True, help_text="where dose it store", index=True)
    size = BigIntegerField(default=0, index=True)
    token_num = IntegerField(default=0, index=True)
    chunk_num = IntegerField(default=0, index=True)
    progress = FloatField(default=0, index=True)
    progress_msg = TextField(null=True, help_text="process message", default="")
    process_begin_at = DateTimeField(null=True, index=True)
    process_duration = FloatField(default=0)
    suffix = EmptyStringCharField(max_length=32, null=False, help_text="The real file extension suffix", index=True)

    content_hash = CharField(max_length=32, null=True, help_text="xxhash128 of document content for change detection", default="", index=True)

    run = CharField(max_length=1, null=True, help_text="start to run processing or cancel.(1: run it; 2: cancel)", default="0", index=True)
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    class Meta:
        db_table = "document"


class File(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    parent_id = CharField(max_length=32, null=False, help_text="parent folder id", index=True)
    tenant_id = CharField(max_length=32, null=False, help_text="tenant id", index=True)
    created_by = CharField(max_length=32, null=False, help_text="who created it", index=True)
    name = CharField(max_length=255, null=False, help_text="file name or folder name", index=True)
    location = CharField(max_length=255, null=True, help_text="where dose it store", index=True)
    size = BigIntegerField(default=0, index=True)
    type = CharField(max_length=32, null=False, help_text="file extension", index=True)
    # File.source_type historically defaults to "". Only GaussDB makes the
    # storage column nullable; MySQL and PostgreSQL retain NOT NULL.
    source_type = EmptyStringCharField(max_length=128, null=False, default="", help_text="where dose this document come from", index=True)

    class Meta:
        db_table = "file"


class File2Document(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    file_id = CharField(max_length=32, null=True, help_text="file id", index=True)
    document_id = CharField(max_length=32, null=True, help_text="document id", index=True)

    class Meta:
        db_table = "file2document"


class FileCommit(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    folder_id = CharField(max_length=32, null=False, help_text="workspace folder id", index=True)
    parent_id = CharField(max_length=32, null=True, help_text="parent commit id", index=True)
    message = CharField(max_length=512, default="", help_text="commit message")
    author_id = CharField(max_length=32, null=False, help_text="user who created the commit", index=True)
    file_count = IntegerField(default=0, help_text="number of files in this commit")
    tree_state = LongTextField(null=True, help_text="JSON snapshot of the full folder tree at this commit")
    # ---- Artifact-commit extension ----
    # Populated only for commits recorded via
    # ``FileCommitService.record_page_edit`` (i.e. artifact-page saves).
    # For workspace file commits both fields stay null and the ``message``
    # column carries the commit body.
    title = CharField(max_length=255, null=True, help_text="commit title (artifact-page edits)")
    comments = TextField(null=True, help_text="commit body/description (artifact-page edits)")

    class Meta:
        db_table = "file_commit"


class FileCommitItem(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    commit_id = CharField(max_length=32, null=False, help_text="commit id", index=True)
    file_id = CharField(max_length=32, null=False, help_text="file id", index=True)
    operation = CharField(max_length=16, null=False, help_text="add / modify / delete / rename", index=True)
    old_hash = CharField(max_length=64, null=True, help_text="old content hash", index=True)
    new_hash = CharField(max_length=64, null=True, help_text="new content hash", index=True)
    old_location = CharField(max_length=255, null=True, help_text="old storage location")
    new_location = CharField(max_length=255, null=True, help_text="new storage location")
    old_name = CharField(max_length=255, null=True, help_text="old file name (for rename)")
    new_name = CharField(max_length=255, null=True, help_text="new file name (for rename)")
    # ---- Artifact-commit extension ----
    # Populated only for artifact-page saves recorded via
    # ``FileCommitService.record_page_edit``.
    diff = LongTextField(null=True, help_text="pre-computed unified diff (artifact-page edits)")
    content_after_storage = CharField(max_length=16, null=True, help_text="'minio' | 'es' — where the post-save blob lives", index=True)
    content_after_location = CharField(max_length=512, null=True, help_text="storage key/id for the post-save blob")
    slug_kwd = CharField(max_length=512, null=True, help_text="artifact page slug (<page_type>/<name>)", index=True)
    page_type_kwd = CharField(max_length=32, null=True, help_text="artifact page type", index=True)

    class Meta:
        db_table = "file_commit_item"
        indexes = (
            (("commit_id", "file_id"), True),  # unique composite index
        )


# ``ArtifactCommit`` retired — artifact page history is now stored under
# ``FileCommit`` + ``FileCommitItem`` via ``FileCommitService.record_page_edit``
# (see the artifact-commit extension columns on those models above).
# Pre-existing ``wiki_commit`` rows are intentionally left in place;
# no code path reads them.


class Task(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    doc_id = CharField(max_length=32, null=False, index=True)
    from_page = IntegerField(default=0)
    to_page = IntegerField(default=MAXIMUM_TASK_PAGE_NUMBER)
    # Standard document parsing tasks historically use task_type="" to mean
    # that they are not dataflow, graph, memory, or another specialized task.
    # A/ORA-compatible GaussDB stores the bound empty string as NULL, so a NOT
    # NULL column would make /documents/parse fail while inserting the task.
    # Only DB_TYPE=gaussdb stores NULL, and the ORM restores "" when reading.
    task_type = EmptyStringCharField(max_length=32, null=False, default="")
    priority = IntegerField(default=0)

    begin_at = DateTimeField(null=True, index=True)
    process_duration = FloatField(default=0)

    progress = FloatField(default=0, index=True)
    # progress_msg and chunk_ids are nullable, but callers commonly concatenate,
    # strip, or split them as strings. The field maps GaussDB NULL to "" without
    # affecting MySQL or PostgreSQL.
    progress_msg = EmptyStringTextField(null=True, help_text="process message", default="")
    retry_count = IntegerField(default=0)
    digest = TextField(null=True, help_text="task digest", default="")
    chunk_ids = EmptyStringLongTextField(null=True, help_text="chunk ids", default="")


class Dialog(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=255, null=True, help_text="dialog application name", index=True)
    description = EmptyStringTextField(null=True, help_text="Dialog description")
    icon = EmptyStringTextField(null=True, help_text="icon base64 string")
    language = CharField(max_length=32, null=True, default="Chinese" if "zh_CN" in os.getenv("LANG", "") else "English", help_text="English|Chinese", index=True)
    # Map application-level empty chat/reranker model IDs to storage NULL in the
    # field instead of handling None throughout the business code.
    llm_id = EmptyStringCharField(max_length=128, null=False, help_text="default llm ID")
    tenant_llm_id = CharField(max_length=32, null=True, help_text="id in tenant_model", index=True)

    llm_setting = JSONField(null=False, default={"temperature": 0.1, "top_p": 0.3, "frequency_penalty": 0.7, "presence_penalty": 0.4, "max_tokens": 512})
    prompt_type = CharField(max_length=16, null=False, default="simple", help_text="simple|advanced", index=True)
    prompt_config = JSONField(
        null=False,
        default={"system": "", "prologue": "Hi! I'm your assistant. What can I do for you?", "parameters": [], "empty_response": "Sorry! No relevant content was found in the knowledge base!"},
    )
    meta_data_filter = JSONField(null=True, default={})

    similarity_threshold = FloatField(default=0.2)
    vector_similarity_weight = FloatField(default=0.3)

    top_n = IntegerField(default=6)
    rerank_candidates_count = IntegerField(default=64)

    top_k = IntegerField(default=1024)

    do_refer = CharField(max_length=1, null=False, default="1", help_text="it needs to insert reference index into answer or not")

    rerank_id = EmptyStringCharField(max_length=128, null=False, help_text="default rerank model ID")
    tenant_rerank_id = CharField(max_length=32, null=True, help_text="id in tenant_model", index=True)
    kb_ids = JSONField(null=False, default=[])
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    class Meta:
        db_table = "dialog"


class Conversation(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    dialog_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=255, null=True, help_text="conversation name", index=True)
    message = JSONField(null=True)
    reference = JSONField(null=True, default=[])
    user_id = CharField(max_length=255, null=True, help_text="user_id", index=True)

    class Meta:
        db_table = "conversation"


class APIToken(DataBaseModel):
    tenant_id = CharField(max_length=32, null=False, index=True)
    token = CharField(max_length=255, null=False, index=True)
    dialog_id = CharField(max_length=32, null=True, index=True)
    source = CharField(max_length=16, null=True, help_text="none|agent|dialog", index=True)
    beta = CharField(max_length=255, null=True, index=True)
    name = CharField(max_length=255, null=True, help_text="API key name")
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    class Meta:
        db_table = "api_token"
        primary_key = CompositeKey("tenant_id", "token")


class API4Conversation(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    name = CharField(max_length=255, null=True, help_text="conversation name", index=False)
    dialog_id = CharField(max_length=32, null=False, index=True)
    user_id = EmptyStringCharField(max_length=255, null=False, help_text="user_id", index=True)
    exp_user_id = CharField(max_length=255, null=True, help_text="exp_user_id", index=True)
    message = JSONField(null=True)
    reference = JSONField(null=True, default=[])
    tokens = IntegerField(default=0)
    source = CharField(max_length=16, null=True, help_text="none|agent|dialog", index=True)
    dsl = JSONField(null=True, default={})
    duration = FloatField(default=0, index=True)
    round = IntegerField(default=0, index=True)
    thumb_up = IntegerField(default=0, index=True)
    errors = TextField(null=True, help_text="errors")
    version_title = CharField(max_length=255, null=True, help_text="canvas version title when session created", index=False)

    class Meta:
        db_table = "api_4_conversation"


class UserCanvas(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    avatar = TextField(null=True, help_text="avatar base64 string")
    user_id = CharField(max_length=255, null=False, help_text="user_id", index=True)
    title = CharField(max_length=255, null=True, help_text="Canvas title")

    permission = CharField(max_length=16, null=False, help_text="me|team", default="me", index=True)
    release = BooleanField(null=False, help_text="is released", default=False, index=True)
    description = TextField(null=True, help_text="Canvas description")
    canvas_type = CharField(max_length=32, null=True, help_text="Canvas type", index=True)
    canvas_category = CharField(max_length=32, null=False, default="agent_canvas", help_text="Canvas category: agent_canvas|dataflow_canvas", index=True)
    tags = EmptyStringCharField(
        max_length=512,
        null=False,
        default="",
        help_text="Comma-separated tags for organizing agents",
        index=True,
    )
    dsl = JSONField(null=True, default={})

    class Meta:
        db_table = "user_canvas"


class CanvasTemplate(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    avatar = TextField(null=True, help_text="avatar base64 string")
    title = JSONField(null=True, default=dict, help_text="Canvas title")
    description = JSONField(null=True, default=dict, help_text="Canvas description")
    canvas_type = CharField(max_length=32, null=True, help_text="Canvas type", index=True)
    canvas_types = ListField(null=True, default=list, help_text="Canvas types")
    canvas_category = CharField(max_length=32, null=False, default="agent_canvas", help_text="Canvas category: agent_canvas|dataflow_canvas", index=True)
    dsl = JSONField(null=True, default={})

    class Meta:
        db_table = "canvas_template"


class UserCanvasVersion(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    user_canvas_id = CharField(max_length=255, null=False, help_text="user_canvas_id", index=True)

    title = CharField(max_length=255, null=True, help_text="Canvas title")
    description = TextField(null=True, help_text="Canvas description")
    release = BooleanField(null=False, help_text="is released", default=False, index=True)
    dsl = JSONField(null=True, default={})

    class Meta:
        db_table = "user_canvas_version"


class MCPServer(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    name = CharField(max_length=255, null=False, help_text="MCP Server name")
    tenant_id = CharField(max_length=32, null=False, index=True)
    url = CharField(max_length=2048, null=False, help_text="MCP Server URL")
    server_type = CharField(max_length=32, null=False, help_text="MCP Server type")
    description = TextField(null=True, help_text="MCP Server description")
    variables = JSONField(null=True, default=dict, help_text="MCP Server variables")
    headers = JSONField(null=True, default=dict, help_text="MCP Server additional request headers")

    class Meta:
        db_table = "mcp_server"


class CompilationTemplate(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=True, index=True)
    group_id = CharField(max_length=32, null=True, index=True)
    name = CharField(max_length=128, null=False, index=True)
    description = TextField(null=True, default="")
    kind = CharField(max_length=64, null=False, index=True)
    config = JSONField(null=False, default={})
    is_builtin = BooleanField(null=False, default=False, index=True)
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    class Meta:
        db_table = "compilation_template"
        indexes = ((("tenant_id", "group_id", "name", "is_builtin", "status"), True),)


class CompilationTemplateGroup(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=128, null=False, index=True)
    description = TextField(null=True, default="")
    scope = CharField(max_length=16, null=False, index=True, help_text="file | dataset")
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    class Meta:
        db_table = "compilation_template_group"


class Search(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    avatar = TextField(null=True, help_text="avatar base64 string")
    tenant_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=128, null=False, help_text="Search name", index=True)
    description = TextField(null=True, help_text="KB description")
    created_by = CharField(max_length=32, null=False, index=True)
    search_config = JSONField(
        null=False,
        default={
            "kb_ids": [],
            "doc_ids": [],
            "similarity_threshold": 0.2,
            "vector_similarity_weight": 0.3,
            "use_kg": False,
            # rerank settings
            "rerank_id": "",
            "top_k": 1024,
            # chat settings
            "summary": False,
            "chat_id": "",  # id of chat model in tenant_model table
            "llm_setting": {
                "temperature": 0.1,
                "top_p": 0.3,
                "frequency_penalty": 0.7,
                "presence_penalty": 0.4,
                "temperature_enabled": True,
                "top_p_enabled": True,
                "frequency_penalty_enabled": True,
                "presence_penalty_enabled": True,
            },
            "chat_settingcross_languages": [],
            "highlight": False,
            "keyword": False,
            "web_search": False,
            "related_search": False,
            "query_mindmap": False,
        },
    )
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "search"


class PipelineOperationLog(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    document_id = CharField(max_length=32, index=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    kb_id = CharField(max_length=32, null=False, index=True)
    pipeline_id = CharField(max_length=32, null=True, help_text="Pipeline ID", index=True)
    pipeline_title = CharField(max_length=32, null=True, help_text="Pipeline title", index=True)
    parser_id = CharField(max_length=32, null=False, help_text="Parser ID", index=True)
    document_name = CharField(max_length=255, null=False, help_text="File name")
    document_suffix = CharField(max_length=255, null=False, help_text="File suffix")
    document_type = CharField(max_length=255, null=False, help_text="Document type")
    source_from = CharField(max_length=255, null=False, help_text="Source")
    progress = FloatField(default=0, index=True)
    progress_msg = TextField(null=True, help_text="process message", default="")
    process_begin_at = DateTimeField(null=True, index=True)
    process_duration = FloatField(default=0)
    dsl = JSONField(null=True, default=dict)
    task_type = CharField(max_length=32, null=False, default="")
    operation_status = CharField(max_length=32, null=False, help_text="Operation status")
    avatar = TextField(null=True, help_text="avatar base64 string")
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    class Meta:
        db_table = "pipeline_operation_log"


class Connector(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=128, null=False, help_text="Search name", index=False)
    source = CharField(max_length=128, null=False, help_text="Data source", index=True)
    input_type = CharField(max_length=128, null=False, help_text="poll/event/..", index=True)
    config = JSONField(null=False, default={})
    refresh_freq = IntegerField(default=0, index=False)
    prune_freq = IntegerField(default=0, index=False)
    timeout_secs = IntegerField(default=3600, index=False)
    indexing_start = DateTimeField(null=True, index=True)
    status = CharField(max_length=16, null=True, help_text="schedule", default="schedule", index=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "connector"


class Connector2Kb(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    connector_id = CharField(max_length=32, null=False, index=True)
    kb_id = CharField(max_length=32, null=False, index=True)
    auto_parse = CharField(max_length=1, null=False, default="1", index=False)

    class Meta:
        db_table = "connector2kb"


class ChatChannel(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=128, null=False, help_text="Bot name", index=False)
    channel = CharField(max_length=128, null=False, help_text="Chat channel type", index=True)
    config = JSONField(null=False, default={}, help_text="Channel credential & settings")
    chat_id = CharField(max_length=32, null=True, default=None, help_text="connected chat id", index=True)
    agent_id = CharField(max_length=32, null=True, default=None, help_text="connected agent id", index=True)
    status = IntegerField(default=1, index=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "chat_channel"


class DateTimeTzField(CharField):
    field_type = "VARCHAR"

    def db_value(self, value: datetime | None) -> str | None:
        if value is not None:
            if value.tzinfo is not None:
                return value.isoformat()
            else:
                return value.replace(tzinfo=timezone.utc).isoformat()
        return value

    def python_value(self, value: str | datetime | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            # The column is declared VARCHAR, but deployments upgraded from
            # older schemas may hold it as native DATETIME, in which case the
            # driver returns datetime objects instead of ISO strings.
            return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            # Zero dates (0000-00-00) and other unparseable values must not
            # raise here: peewee counts the row before converting it, so one
            # bad value wedges every later iteration over the table with
            # IndexError: list index out of range.
            logging.warning("DateTimeTzField: unparseable value %r, falling back to None", value)
            return None
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class SyncLogs(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    connector_id = CharField(max_length=32, index=True)
    task_type = CharField(max_length=32, null=False, default="sync", index=True)
    status = CharField(max_length=128, null=False, help_text="Processing status", index=True)
    from_beginning = CharField(max_length=1, null=True, help_text="", default="0", index=False)
    new_docs_indexed = IntegerField(default=0, index=False)
    total_docs_indexed = IntegerField(default=0, index=False)
    docs_removed_from_index = IntegerField(default=0, index=False)
    # Connector scheduling logs use error_msg="" to mean that no error is
    # present. A/ORA-compatible GaussDB stores it as NULL, so keeping this column
    # NOT NULL would break PUT /datasets/<id> when it schedules sync_logs. The
    # field permits storage NULL and restores the application-level empty string.
    error_msg = EmptyStringTextField(null=False, help_text="process message", default="")
    error_count = IntegerField(default=0, index=False)
    # full_exception_trace is nullable, but callers append stack traces as text.
    # Hide GaussDB storage NULL behind the same application-level empty string.
    full_exception_trace = EmptyStringTextField(null=True, help_text="process message", default="")
    time_started = DateTimeField(null=True, index=True)
    poll_range_start = DateTimeTzField(max_length=255, null=True, index=True)
    poll_range_end = DateTimeTzField(max_length=255, null=True, index=True)
    kb_id = CharField(max_length=32, null=False, index=True)

    class Meta:
        db_table = "sync_logs"


class Memory(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    name = CharField(max_length=128, null=False, index=False, help_text="Memory name")
    avatar = TextField(null=True, help_text="avatar base64 string")
    tenant_id = CharField(max_length=32, null=False, index=True)
    memory_type = IntegerField(null=False, default=1, index=True, help_text="Bit flags (LSB->MSB): 1=raw, 2=semantic, 4=episodic, 8=procedural. E.g., 5 enables raw + episodic.")
    storage_type = CharField(max_length=32, default="table", null=False, index=True, help_text="table|graph")
    # Keep empty model-ID handling in the field so storage NULL semantics do not
    # leak into Memory Store callers.
    embd_id = EmptyStringCharField(max_length=128, null=False, index=False, help_text="embedding model ID")
    tenant_embd_id = CharField(max_length=32, null=True, help_text="id in tenant_model", index=True)
    llm_id = EmptyStringCharField(max_length=128, null=False, index=False, help_text="chat model ID")
    tenant_llm_id = CharField(max_length=32, null=True, help_text="id in tenant_model", index=True)
    permissions = CharField(max_length=16, null=False, index=True, help_text="me|team", default="me")
    description = TextField(null=True, help_text="description")
    memory_size = IntegerField(default=5242880, null=False, index=False)
    forgetting_policy = CharField(max_length=32, null=False, default="FIFO", index=False, help_text="LRU|FIFO")
    temperature = FloatField(default=0.5, index=False)
    system_prompt = TextField(null=True, help_text="system prompt", index=False)
    user_prompt = TextField(null=True, help_text="user prompt", index=False)

    class Meta:
        db_table = "memory"


class SystemSettings(DataBaseModel):
    name = CharField(max_length=128, primary_key=True)
    source = CharField(max_length=32, null=False, index=False)
    data_type = CharField(max_length=32, null=False, index=False)
    # system_settings.json contains empty configuration values. Store them as
    # NULL on GaussDB and restore "" here instead of globally converting SQL
    # results and affecting fields where NULL is meaningful.
    value = EmptyStringTextField(null=False, help_text="Configuration value (JSON, string, etc.)")

    class Meta:
        db_table = "system_settings"


class TenantModelProvider(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    provider_name = CharField(max_length=128, null=False, index=False, help_text="LLM provider name")
    tenant_id = CharField(max_length=32, null=False, index=True)

    class Meta:
        db_table = "tenant_model_provider"
        indexes = ((("tenant_id", "provider_name"), True),)


class TenantModelInstance(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    instance_name = CharField(max_length=128, null=False, index=False, help_text="Model instance name")
    provider_id = CharField(max_length=32, null=False, index=False)
    api_key = CharField(max_length=512, null=False, index=False, help_text="API key")
    status = CharField(max_length=32, default="active", index=False)
    extra = CharField(max_length=512, default="{}", index=False)

    class Meta:
        db_table = "tenant_model_instance"


class TenantModel(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    model_name = CharField(max_length=128, null=True, index=False, help_text="Model name")
    provider_id = CharField(max_length=32, null=False, index=False)
    instance_id = CharField(max_length=32, null=False, index=True)
    model_type = IntegerField(null=False, default=1, index=True, help_text="Bit flags (LSB->MSB): 1=chat, 2=embedding, 4=asr, 8=vision, 16=rerank, 32=tts, 64=ocr")
    status = CharField(max_length=32, default="active", index=False)
    extra = CharField(max_length=1024, default="{}", index=False)

    class Meta:
        db_table = "tenant_model"


class TenantModelGroup(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    group_type = CharField(max_length=32, null=False, index=False, help_text="Group type")
    model_name = CharField(max_length=128, null=True, index=False, help_text="Model name")
    strategy = CharField(max_length=32, default="weighted", index=False, help_text="Routing strategy")

    class Meta:
        db_table = "tenant_model_group"


class TenantModelGroupMapping(DataBaseModel):
    group_id = CharField(max_length=32, null=False, index=True, help_text="Group ID")
    provider_id = CharField(max_length=32, null=False, index=False)
    instance_id = CharField(max_length=32, null=False, index=False)
    model_id = CharField(max_length=32, null=False, index=True)
    weight = IntegerField(default=100, index=False, help_text="Routing weight")
    status = CharField(max_length=32, default="active", index=False)

    class Meta:
        db_table = "tenant_model_group_mapping"
        primary_key = CompositeKey("group_id", "provider_id", "instance_id", "model_id")


class GlobalRagflowInstance(DataBaseModel):
    id = CharField(max_length=32, primary_key=True, default="GLOBAL")
    name = CharField(max_length=128, default="Global RAGFlow Instance")
    status = CharField(max_length=32, default="ACTIVE")
    default_free_model_id = CharField(max_length=128, null=True, default="openai/gpt-4o-mini")
    default_plus_model_id = CharField(max_length=128, null=True, default="openai/gpt-4o")
    default_pro_model_id = CharField(max_length=128, null=True, default="anthropic/claude-3-5-sonnet-20241022")
    default_embd_id = CharField(max_length=128, null=True, default="openai/text-embedding-3-small")
    default_rerank_id = CharField(max_length=128, null=True, default="BAAI/bge-reranker-v2-m3")
    byok_enabled = BooleanField(default=True)
    max_byok_models = IntegerField(default=10)
    byok_token_limit = BigIntegerField(default=50000000)
    byok_request_limit = IntegerField(default=100000)
    extra = JSONField(null=True, default=dict)
    create_time = BigIntegerField(null=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "global_ragflow_instance"


class AIProvider(DataBaseModel):
    id = CharField(max_length=64, primary_key=True)
    provider_name = CharField(max_length=128, null=False, index=True)
    base_url = CharField(max_length=255, null=True)
    api_key = TextField(null=True)
    organization = CharField(max_length=128, null=True)
    api_version = CharField(max_length=64, null=True)
    status = CharField(max_length=32, default="active")
    is_global = BooleanField(default=True, index=True)
    owner_user_id = CharField(max_length=32, null=True, index=True)
    global_instance_id = CharField(max_length=32, default="GLOBAL", index=True)
    extra = JSONField(null=True, default=dict)
    create_time = BigIntegerField(null=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ai_provider"


class SubscriptionPlan(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    name = CharField(max_length=100, null=False, index=True)
    daily_token_limit = BigIntegerField(default=50000, help_text="Daily token limit")
    monthly_token_limit = BigIntegerField(default=1000000, help_text="Monthly token limit")
    daily_request_limit = IntegerField(default=500, help_text="Daily request limit")
    monthly_request_limit = IntegerField(default=10000, help_text="Monthly request limit")
    requests_per_minute = IntegerField(default=60, help_text="Rate limit per minute")
    max_tokens_per_request = IntegerField(default=4096, help_text="Max tokens per request")
    limit_mode = CharField(max_length=32, default="shared", help_text="shared or per_model")
    max_storage_gb = FloatField(default=5.0)
    max_datasets = IntegerField(default=5)
    max_agents = IntegerField(default=5)
    allow_custom_providers = BooleanField(default=False)
    allow_custom_models = BooleanField(default=False)
    allow_custom_endpoints = BooleanField(default=False)
    allow_private_servers = BooleanField(default=False)
    allow_byok = BooleanField(default=False)
    max_byok_models = IntegerField(default=0)
    default_llm_id = CharField(max_length=128, null=True)
    default_embd_id = CharField(max_length=128, null=True)
    default_rerank_id = CharField(max_length=128, null=True)
    status = CharField(max_length=1, default="1", index=True)

    class Meta:
        db_table = "subscription_plan"


class AIModel(DataBaseModel):
    id = CharField(max_length=128, primary_key=True)
    provider = CharField(max_length=128, null=False, index=True)
    model_name = CharField(max_length=128, null=False, index=True)
    model_type = CharField(max_length=32, null=False, index=True)
    base_url = CharField(max_length=255, null=True)
    api_key = TextField(null=True)
    input_token_price = FloatField(default=0.0, help_text="USD per 1M input tokens")
    output_token_price = FloatField(default=0.0, help_text="USD per 1M output tokens")
    max_tokens = IntegerField(default=8192)
    enabled = BooleanField(default=True, index=True)
    is_global = BooleanField(default=True, index=True)
    is_custom = BooleanField(default=False, index=True)
    owner_user_id = CharField(max_length=32, null=True, index=True)
    owner_tenant_id = CharField(max_length=32, null=True, index=True)
    status = CharField(max_length=32, default="active", index=True)
    global_instance_id = CharField(max_length=32, default="GLOBAL", index=True)
    extra = JSONField(null=True, default=dict)
    create_time = BigIntegerField(null=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ai_model"


class SubscriptionAIPolicy(DataBaseModel):
    id = CharField(max_length=128, primary_key=True)
    plan_id = CharField(max_length=32, null=False, index=True)
    model_id = CharField(max_length=128, null=False, index=True)
    model_token_limit = BigIntegerField(default=0, help_text="0 means unlimited up to plan total limit")
    is_default_llm = BooleanField(default=False)
    is_default_embd = BooleanField(default=False)
    is_default_rerank = BooleanField(default=False)
    enabled = BooleanField(default=True, index=True)

    class Meta:
        db_table = "subscription_ai_policy"


class UserTokenLimit(DataBaseModel):
    user_id = CharField(max_length=32, primary_key=True)
    monthly_token_limit = BigIntegerField(default=0, help_text="0 means fallback to plan limit")
    enabled = BooleanField(default=True)
    extra = JSONField(null=True, default={})

    class Meta:
        db_table = "user_token_limit"


class TokenUsageLog(DataBaseModel):
    id = CharField(max_length=64, primary_key=True)
    user_id = CharField(max_length=32, null=False, index=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    subscription_id = CharField(max_length=32, null=True, index=True)
    global_instance_id = CharField(max_length=32, default="GLOBAL", index=True)
    model_id = CharField(max_length=128, null=False, index=True)
    provider_id = CharField(max_length=128, null=True, index=True)
    model_type = CharField(max_length=32, null=False, index=True)
    input_tokens = IntegerField(default=0)
    output_tokens = IntegerField(default=0)
    total_tokens = IntegerField(default=0)
    estimated_cost = FloatField(default=0.0)
    status = CharField(max_length=32, default="SUCCESS", index=True)
    billing_period = CharField(max_length=7, null=False, index=True)
    date_str = CharField(max_length=10, null=True, index=True)
    create_time = BigIntegerField(null=True, index=True)

    class Meta:
        db_table = "token_usage_log"


class AIAuditLog(DataBaseModel):
    id = CharField(max_length=64, primary_key=True)
    user_id = CharField(max_length=32, null=False, index=True)
    action = CharField(max_length=128, null=False, index=True)
    target_type = CharField(max_length=64, null=False)
    target_id = CharField(max_length=128, null=True)
    details = TextField(null=True, help_text="Sanitized action details JSON")
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "ai_audit_log"


class Advertiser(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    user_id = CharField(max_length=32, null=False, index=True)
    company_name = CharField(max_length=255, null=False, default="")
    contact_email = CharField(max_length=255, null=True)
    website_url = CharField(max_length=1024, null=True)
    pixel_id = CharField(max_length=32, null=True, unique=True, index=True)
    balance = FloatField(default=0.0)
    currency = CharField(max_length=8, default="USD")
    status = CharField(max_length=32, default="active", index=True)  # active, suspended, pending
    create_time = BigIntegerField(null=True, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "advertisers"


class AdvertiserTeamMember(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    user_id = CharField(max_length=32, null=True, index=True)
    email = CharField(max_length=255, null=False, index=True)
    role = CharField(max_length=32, default="manager", index=True)  # admin, manager, analyst, billing
    status = CharField(max_length=32, default="active", index=True)  # active, pending, revoked
    invited_by = CharField(max_length=32, null=True)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "advertiser_team_members"


class AdvertiserNotificationSettings(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, unique=True, index=True)
    email_alerts_enabled = BooleanField(default=True)
    email_target = CharField(max_length=255, null=True)
    telegram_alerts_enabled = BooleanField(default=False)
    telegram_chat_id = CharField(max_length=64, null=True)
    webhook_url = CharField(max_length=1024, null=True)
    webhook_secret = CharField(max_length=64, null=True)
    notify_low_balance = BooleanField(default=True)
    low_balance_threshold = FloatField(default=10.0)
    notify_daily_budget_reached = BooleanField(default=True)
    notify_moderation_status = BooleanField(default=True)
    notify_conversion_milestone = BooleanField(default=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "advertiser_notification_settings"


class AdvertiserNotification(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    type = CharField(max_length=32, default="system", index=True)
    severity = CharField(max_length=16, default="info")  # info, warning, critical, success
    title = CharField(max_length=255, null=False)
    message = TextField(null=False)
    is_read = BooleanField(default=False, index=True)
    data = JSONField(null=True, default=dict)
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "advertiser_notifications"


class AdCampaign(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=255, null=False)
    product_name = CharField(max_length=255, null=False)
    description = TextField(null=True)
    advertisement_text = TextField(null=False)
    landing_url = CharField(max_length=1024, null=False)
    target_categories = JSONField(null=True, default=list)  # list of str (e.g. ["crm", "business"])
    keywords = JSONField(null=True, default=list)  # list of str
    negative_keywords = JSONField(null=True, default=list)  # list of str (e.g. ["free", "torrent", "crack"])
    target_languages = JSONField(null=True, default=list)  # ["uz", "ru", "en"] or [] for all
    target_models = JSONField(null=True, default=list)  # ["gpt-4o", "deepseek-r1", "claude-3-5-sonnet"] or [] for all
    target_countries = JSONField(null=True, default=list)  # ["UZ", "RU", "KZ"] or [] for all
    target_regions = JSONField(null=True, default=list)  # ["tashkent", "samarkand", "bukhara", "fergana", "andijan", "namangan", "all"]
    target_cities = JSONField(null=True, default=list)  # list of city names
    daily_budget = FloatField(default=10.0)
    total_budget = FloatField(default=100.0)
    spent_today = FloatField(default=0.0)
    total_spent = FloatField(default=0.0)
    pricing_model = CharField(max_length=16, default="cpc", index=True)  # cpc, cpm, cpa
    bid_amount = FloatField(default=0.10)
    bidding_strategy = CharField(max_length=32, default="manual_cpc", index=True)  # manual_cpc, target_cpa, maximize_conversions, enhanced_cpc
    target_cpa = FloatField(default=0.0)  # Smart auto-bidding Target Cost Per Action ($)
    schedule_timezone = CharField(max_length=64, default="UTC")
    schedule_config = JSONField(null=True, default=dict)  # Dayparting & hourly multipliers config
    dco_enabled = BooleanField(default=False)  # Dynamic Creative Optimization & Keyword Insertion
    dco_config = JSONField(null=True, default=dict)  # DCO templates, DKI rules, UTM config, promo codes
    pacing_mode = CharField(max_length=32, default="standard_smooth", index=True)  # standard_smooth, accelerated_asap, peak_weighted
    auto_rules_enabled = BooleanField(default=True)
    conversions_count = IntegerField(default=0)
    conversion_rate = FloatField(default=0.0)
    total_conversion_value = FloatField(default=0.0)
    frequency_cap_impressions = IntegerField(default=0)  # 0 = unlimited impressions
    frequency_cap_hours = IntegerField(default=24)  # Frequency capping time window (hours)
    target_audience_segment_ids = JSONField(null=True, default=list)  # Segment IDs to include
    exclude_audience_segment_ids = JSONField(null=True, default=list)  # Segment IDs to exclude
    priority = IntegerField(default=0)
    status = CharField(max_length=32, default="active", index=True)  # draft, active, paused, completed, archived
    moderation_status = CharField(max_length=32, default="approved", index=True)  # pending, approved, rejected
    moderation_note = TextField(null=True)
    start_date = DateTimeField(null=True)
    end_date = DateTimeField(null=True)
    create_time = BigIntegerField(null=True, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "campaigns"


class AdAudienceSegment(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=255, null=False)
    description = TextField(null=True)
    rule_type = CharField(max_length=32, default="pixel_event", index=True)  # pixel_event, intent_keyword, custom_list
    rule_config = JSONField(null=True, default=dict)
    member_count = IntegerField(default=0)
    status = CharField(max_length=32, default="active", index=True)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_audience_segments"


class AdAudienceMember(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    segment_id = CharField(max_length=32, null=False, index=True)
    user_id = CharField(max_length=32, null=True, index=True)
    anonymous_id = CharField(max_length=64, null=True, index=True)  # IP hash or visitor token
    source_event = CharField(max_length=64, null=True)
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "ad_audience_members"


class AdVariant(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    campaign_id = CharField(max_length=32, null=False, index=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=128, null=False)  # e.g. "Variant A (Direct)", "Variant B (Discount)"
    advertisement_text = TextField(null=False)
    landing_url = CharField(max_length=1024, null=True)
    impressions = IntegerField(default=0)
    clicks = IntegerField(default=0)
    weight = FloatField(default=1.0)
    is_active = BooleanField(default=True, index=True)
    create_time = BigIntegerField(null=True, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "campaign_variants"


class AdImpression(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    campaign_id = CharField(max_length=32, null=False, index=True)
    variant_id = CharField(max_length=32, null=True, index=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    user_id = CharField(max_length=32, null=True, index=True)
    tenant_id = CharField(max_length=32, null=True, index=True)
    conversation_id = CharField(max_length=32, null=True, index=True)
    message_id = CharField(max_length=32, null=True)
    cost = FloatField(default=0.0)
    query_intent = CharField(max_length=255, null=True)
    language = CharField(max_length=16, default="ru", null=True, index=True)
    model_name = CharField(max_length=64, default="gpt-4o", null=True, index=True)
    device_type = CharField(max_length=32, default="desktop", null=True, index=True)
    platform = CharField(max_length=32, default="web", null=True)
    region = CharField(max_length=64, default="tashkent", null=True, index=True)
    city = CharField(max_length=64, default="Tashkent", null=True, index=True)
    country = CharField(max_length=8, default="UZ", null=True, index=True)
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "campaign_impressions"


class AdClick(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    campaign_id = CharField(max_length=32, null=False, index=True)
    variant_id = CharField(max_length=32, null=True, index=True)
    impression_id = CharField(max_length=32, null=True, index=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    user_id = CharField(max_length=32, null=True, index=True)
    cost = FloatField(default=0.0)
    ip_hash = CharField(max_length=64, null=True)
    language = CharField(max_length=16, default="ru", null=True, index=True)
    model_name = CharField(max_length=64, default="gpt-4o", null=True, index=True)
    device_type = CharField(max_length=32, default="desktop", null=True, index=True)
    platform = CharField(max_length=32, default="web", null=True)
    region = CharField(max_length=64, default="tashkent", null=True, index=True)
    city = CharField(max_length=64, default="Tashkent", null=True, index=True)
    country = CharField(max_length=8, default="UZ", null=True, index=True)
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "campaign_clicks"


class AdConversion(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    campaign_id = CharField(max_length=32, null=False, index=True)
    variant_id = CharField(max_length=32, null=True, index=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    click_id = CharField(max_length=32, null=True, index=True)
    impression_id = CharField(max_length=32, null=True, index=True)
    user_id = CharField(max_length=32, null=True, index=True)
    conversion_event = CharField(max_length=64, default="purchase", index=True)  # purchase, lead, signup, custom
    conversion_value = FloatField(default=0.0)
    currency = CharField(max_length=8, default="USD")
    order_id = CharField(max_length=128, null=True, index=True)
    cost = FloatField(default=0.0)
    ip_hash = CharField(max_length=64, null=True)
    status = CharField(max_length=32, default="confirmed", index=True)  # confirmed, pending, rejected
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "campaign_conversions"


class AdTransaction(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    amount = FloatField(null=False)
    type = CharField(max_length=32, null=False, index=True)  # deposit, spend_cpc, spend_cpm, refund, adjustment
    description = CharField(max_length=255, null=True)
    reference_id = CharField(max_length=64, null=True)
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "advertising_transactions"


class AdSettings(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    key = CharField(max_length=128, unique=True, index=True)
    value = TextField(null=False)
    description = CharField(max_length=255, null=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "advertising_settings"


class UserOnboarding(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=32, null=False, index=True)
    tenant_id = CharField(max_length=32, null=True, index=True)
    purpose = CharField(max_length=255, null=True)
    intended_use = TextField(null=True)
    company_name = CharField(max_length=255, null=True)
    company_size = CharField(max_length=64, null=True)
    industry = CharField(max_length=128, null=True)
    role = CharField(max_length=128, null=True)
    platform_goals = TextField(null=True)
    completed = BooleanField(default=False)

    class Meta:
        db_table = "user_onboarding"


class PaymentOrder(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=32, null=False, index=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    gateway = CharField(max_length=32, default="atmos", index=True)
    external_transaction_id = CharField(max_length=64, null=True, index=True)
    purpose = CharField(max_length=64, null=False, index=True)  # subscription_upgrade, advertiser_deposit
    plan_id = CharField(max_length=32, null=True, index=True)   # plus, pro
    advertiser_id = CharField(max_length=32, null=True, index=True)
    amount_uzs = BigIntegerField(default=0)
    amount_usd = FloatField(default=0.0)
    currency = CharField(max_length=8, default="UZS")
    status = CharField(max_length=32, default="pending", index=True)  # pending, waiting_otp, paid, failed, canceled
    card_masked = CharField(max_length=32, null=True)
    phone_masked = CharField(max_length=32, null=True)
    error_message = TextField(null=True)
    metadata = JSONField(null=True, default=dict)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "payment_orders"


class SavedPaymentMethod(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=32, null=False, index=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    card_pan_masked = CharField(max_length=32, null=False)  # e.g. "8600 06** **** 1234"
    card_expiry = CharField(max_length=8, null=False)        # e.g. "12/28"
    card_holder = CharField(max_length=128, null=True)
    card_type = CharField(max_length=32, default="uzcard")   # uzcard, humo, visa, mastercard
    card_token = CharField(max_length=255, null=False)       # token from Atmos for recurrent charges
    is_default = BooleanField(default=True)
    status = CharField(max_length=32, default="active", index=True)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "saved_payment_methods"


class UserSubscription(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=32, null=False, index=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    plan_id = CharField(max_length=32, null=False, index=True)  # plus, pro
    status = CharField(max_length=32, default="active", index=True)  # active, canceled, past_due, expired
    current_period_start = BigIntegerField(null=False)
    current_period_end = BigIntegerField(null=False, index=True)
    auto_renew = BooleanField(default=True)
    price_usd = FloatField(default=9.99)
    payment_method_id = CharField(max_length=32, null=True)
    last_billing_time = BigIntegerField(null=True)
    next_billing_time = BigIntegerField(null=True, index=True)
    cancel_at_period_end = BooleanField(default=False)
    retry_count = IntegerField(default=0)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "user_subscriptions"


class AdAttributionVisit(BaseModel):
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=32, null=False, index=True, help_text="Referrer account user id")
    tenant_id = CharField(max_length=32, null=True, index=True)
    utm_source = CharField(max_length=64, default="chat_watermark", index=True)
    utm_medium = CharField(max_length=64, default="ai_response", index=True)
    utm_campaign = CharField(max_length=64, default="platform_attribution", index=True)
    utm_content = CharField(max_length=64, null=True)
    ip_hash = CharField(max_length=64, null=True, index=True)
    user_agent = TextField(null=True)
    converted_to_user_id = CharField(max_length=32, null=True, index=True, help_text="User ID if visitor registered")
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "ad_attribution_visits"


class AdPublisher(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    user_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=255, null=False, default="")
    api_key = CharField(max_length=64, null=False, unique=True, index=True)
    balance = FloatField(default=0.0)
    total_earned = FloatField(default=0.0)
    total_withdrawn = FloatField(default=0.0)
    default_rev_share = FloatField(default=0.70)  # 70% to publisher, 30% platform
    payout_card = CharField(max_length=64, null=True)
    payout_holder = CharField(max_length=128, null=True)
    status = CharField(max_length=32, default="active", index=True)  # active, suspended
    create_time = BigIntegerField(null=True, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_publishers"


class AdPlacement(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    publisher_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=128, null=False)
    placement_type = CharField(max_length=32, default="telegram_bot", index=True)  # telegram_bot, web_widget, mobile_app, api_agent
    domain_or_bot = CharField(max_length=255, null=True)
    rev_share_rate = FloatField(default=0.70)
    impressions = IntegerField(default=0)
    clicks = IntegerField(default=0)
    earnings = FloatField(default=0.0)
    status = CharField(max_length=32, default="active", index=True)  # active, paused, archived
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_placements"


class AdPublisherPayout(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    publisher_id = CharField(max_length=32, null=False, index=True)
    amount = FloatField(null=False)
    currency = CharField(max_length=8, default="USD")
    destination_card = CharField(max_length=64, null=False)
    destination_holder = CharField(max_length=128, null=True)
    status = CharField(max_length=32, default="pending", index=True)  # pending, approved, paid, rejected
    note = TextField(null=True)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_publisher_payouts"


class AdFraudLog(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    campaign_id = CharField(max_length=32, null=True, index=True)
    event_type = CharField(max_length=32, default="click", index=True)  # click, impression, partner_query
    reason = CharField(max_length=64, null=False, index=True)  # rapid_repeat_clicks, bot_user_agent, blacklist_ip, rate_limit_exceeded
    ip_hash = CharField(max_length=64, null=True, index=True)
    user_agent = TextField(null=True)
    cost_saved = FloatField(default=0.0)
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "ad_fraud_logs"


class AdIpBlacklist(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=True, index=True)  # null/system for global, or specific advertiser_id
    ip_address = CharField(max_length=64, null=False, index=True)
    reason = CharField(max_length=255, default="Suspicious automated click activity")
    auto_expires_at = BigIntegerField(null=True)
    status = CharField(max_length=32, default="active", index=True)  # active, revoked
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_ip_blacklist"


class AdBiddingLog(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    campaign_id = CharField(max_length=32, null=False, index=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    strategy = CharField(max_length=32, default="manual_cpc")
    base_bid = FloatField(default=0.10)
    adjusted_bid = FloatField(default=0.10)
    schedule_multiplier = FloatField(default=1.0)
    cvr_multiplier = FloatField(default=1.0)
    estimated_cvr = FloatField(default=0.0)
    reason = CharField(max_length=255, null=True)
    query = CharField(max_length=255, null=True)
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "ad_bidding_logs"


class AdDcoLog(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    campaign_id = CharField(max_length=32, null=False, index=True)
    advertiser_id = CharField(max_length=32, null=True, index=True)
    query = CharField(max_length=512, null=True)
    original_text = TextField(null=True)
    rendered_text = TextField(null=True)
    original_url = TextField(null=True)
    rendered_url = TextField(null=True)
    inserted_keyword = CharField(max_length=255, null=True)
    applied_city = CharField(max_length=128, null=True)
    applied_model = CharField(max_length=128, null=True)
    applied_promo = CharField(max_length=128, null=True)
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "ad_dco_logs"


class AdAutomatedRule(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    campaign_id = CharField(max_length=32, default="all", index=True)  # specific campaign_id or "all"
    name = CharField(max_length=128, null=False)
    description = TextField(null=True)
    metric = CharField(max_length=32, default="ctr")  # ctr, cvr, cpa, impressions, clicks, spent, conversions, spent_ratio
    operator = CharField(max_length=8, default="<")  # <, <=, >, >=, ==
    threshold_value = FloatField(default=1.0)
    min_impressions = IntegerField(default=100)  # Safety threshold before evaluating rule
    time_window = CharField(max_length=32, default="today")  # today, last_7_days, last_30_days, lifetime
    action_type = CharField(max_length=32, default="pause_campaign")  # pause_campaign, resume_campaign, increase_bid, decrease_bid, increase_budget, decrease_budget, send_alert
    action_value = FloatField(default=0.0)  # e.g. 20 (percent) or fixed amount
    is_active = BooleanField(default=True)
    last_evaluated_time = BigIntegerField(null=True)
    last_triggered_time = BigIntegerField(null=True)
    trigger_count = IntegerField(default=0)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_automated_rules"


class AdRuleExecutionLog(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    rule_id = CharField(max_length=32, null=False, index=True)
    rule_name = CharField(max_length=128, null=False)
    campaign_id = CharField(max_length=32, null=False, index=True)
    campaign_name = CharField(max_length=128, null=False)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    metric_name = CharField(max_length=32, null=False)
    metric_current_value = FloatField(default=0.0)
    threshold_value = FloatField(default=0.0)
    action_taken = CharField(max_length=64, null=False)
    action_details = TextField(null=True)
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "ad_rule_execution_logs"


class AdJourneyTouchpoint(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    visitor_id = CharField(max_length=64, null=False, index=True)  # Anonymous tracking fingerprint or user ID
    advertiser_id = CharField(max_length=32, null=False, index=True)
    campaign_id = CharField(max_length=32, null=False, index=True)
    campaign_name = CharField(max_length=128, default="")
    touchpoint_type = CharField(max_length=32, default="click", index=True)  # impression, click, query, site_visit, cart_add, checkout_start
    touchpoint_seq = IntegerField(default=1)  # 1st touch, 2nd touch, etc. in visitor journey
    channel = CharField(max_length=64, default="ai_recommendation")  # ai_chat, telegram_bot, direct_search, retargeting, partner_widget
    utm_source = CharField(max_length=64, null=True)
    utm_medium = CharField(max_length=64, null=True)
    utm_campaign = CharField(max_length=128, null=True)
    model_name = CharField(max_length=64, null=True)
    device = CharField(max_length=32, null=True)
    city = CharField(max_length=64, null=True)
    cost = FloatField(default=0.0)
    touchpoint_time = BigIntegerField(null=True, index=True)
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "ad_journey_touchpoints"


class AdConversionAttribution(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    conversion_event_id = CharField(max_length=64, null=False, index=True)
    visitor_id = CharField(max_length=64, null=False, index=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    conversion_type = CharField(max_length=64, default="purchase")  # lead, purchase, signup, custom
    conversion_value = FloatField(default=0.0)
    currency = CharField(max_length=8, default="USD")
    total_touchpoints = IntegerField(default=1)
    journey_duration_hours = FloatField(default=0.0)  # Time span between first touchpoint and conversion
    first_touch_campaign_id = CharField(max_length=32, null=True, index=True)
    first_touch_campaign_name = CharField(max_length=128, default="")
    last_touch_campaign_id = CharField(max_length=32, null=True, index=True)
    last_touch_campaign_name = CharField(max_length=128, default="")
    linear_weights = JSONField(null=True, default=dict)  # campaign_id -> fractional credit
    time_decay_weights = JSONField(null=True, default=dict)  # campaign_id -> decay credit
    position_based_weights = JSONField(null=True, default=dict)  # campaign_id -> 40/40/20 credit
    journey_path = JSONField(null=True, default=list)  # list of touchpoints summary
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "ad_conversion_attributions"


class AdAudienceLookalike(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    source_segment_id = CharField(max_length=32, null=False, index=True)
    source_segment_name = CharField(max_length=128, default="")
    name = CharField(max_length=128, null=False)
    similarity_ratio = IntegerField(default=1)  # 1 to 10 (% top similarity tier)
    country = CharField(max_length=32, default="ALL")  # UZ, RU, US, ALL
    seed_audience_size = IntegerField(default=0)
    estimated_reach = IntegerField(default=10000)
    status = CharField(max_length=32, default="ready")  # building, ready, failed
    feature_weights = JSONField(null=True, default=dict)  # query_intent, category_affinity, device_affinity
    expansion_metadata = JSONField(null=True, default=dict)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_audience_lookalikes"


class AdCustomerLtvProfile(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    visitor_id = CharField(max_length=64, null=False, index=True)
    customer_identifier = CharField(max_length=128, null=True, index=True)  # email hash, phone hash, or CRM id
    rfm_recency_days = IntegerField(default=0)  # Days since last interaction/order
    rfm_frequency = IntegerField(default=1)  # Number of orders/transactions
    rfm_monetary_val = FloatField(default=0.0)  # Total historical spend
    rfm_segment = CharField(max_length=32, default="potential_loyalist", index=True)
    # Segments: champions, loyal, potential_loyalist, recent_customers, at_risk, hibernating, lost
    predicted_ltv_90d = FloatField(default=0.0)  # Predicted 90-day LTV in USD
    predicted_ltv_365d = FloatField(default=0.0)  # Projected 1-year value
    churn_risk_score = FloatField(default=0.1)  # 0.0 (safe) to 1.0 (imminent churn)
    total_orders = IntegerField(default=1)
    avg_order_value = FloatField(default=0.0)
    last_order_time = BigIntegerField(null=True)
    tags = JSONField(null=True, default=list)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_customer_ltv_profiles"


class AdProductFeed(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=128, null=False)
    feed_type = CharField(max_length=32, default="custom_json")  # google_merchant, custom_json, facebook_catalog, csv_tsv
    feed_url = CharField(max_length=512, null=True)
    currency = CharField(max_length=10, default="USD")
    items_count = IntegerField(default=0)
    sync_status = CharField(max_length=32, default="active")  # active, syncing, error, paused
    last_sync_time = BigIntegerField(null=True)
    sync_frequency = CharField(max_length=32, default="daily")  # manual, hourly, daily, weekly
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_product_feeds"


class AdProductItem(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    feed_id = CharField(max_length=32, null=False, index=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    sku = CharField(max_length=64, null=False, index=True)
    title = CharField(max_length=255, null=False)
    description = TextField(default="")
    price = FloatField(default=0.0)
    original_price = FloatField(null=True)  # for discount badge %
    currency = CharField(max_length=10, default="USD")
    image_url = CharField(max_length=512, null=True)
    product_url = CharField(max_length=512, null=False)
    category = CharField(max_length=128, default="", index=True)
    brand = CharField(max_length=128, default="")
    availability = CharField(max_length=32, default="in_stock")  # in_stock, out_of_stock, preorder
    custom_labels = JSONField(null=True, default=dict)
    is_active = BooleanField(default=True, index=True)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_product_items"


class AdCreativeMatrixAsset(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    campaign_id = CharField(max_length=32, null=True, index=True)
    product_name = CharField(max_length=128, null=False)
    category = CharField(max_length=128, default="")
    format_type = CharField(max_length=32, index=True)  # text_card, rich_interactive_card, story_banner, leaderboard_banner, video_storyboard
    asset_payload = JSONField(null=True, default=dict)  # structured headlines, description, cta, visuals, scripts
    health_score = IntegerField(default=90)  # 0 to 100
    is_published = BooleanField(default=False)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_creative_matrix_assets"


class AdAgencyWorkspace(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    owner_advertiser_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=128, null=False)
    agency_slug = CharField(max_length=64, null=True, index=True)
    logo_url = CharField(max_length=1024, null=True)
    brand_color = CharField(max_length=32, default="#6366f1")
    report_footer_text = CharField(max_length=255, null=True)
    billing_mode = CharField(max_length=32, default="consolidated")  # consolidated, separate
    status = CharField(max_length=32, default="active", index=True)  # active, archived
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_agency_workspaces"


class AdAgencyClient(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    workspace_id = CharField(max_length=32, null=False, index=True)
    client_advertiser_id = CharField(max_length=32, null=False, index=True)
    client_name = CharField(max_length=128, null=False)
    contact_email = CharField(max_length=128, null=True)
    monthly_budget_cap = FloatField(default=0.0)  # 0.0 means unlimited
    monthly_spend_current = FloatField(default=0.0)
    currency = CharField(max_length=8, default="USD")
    status = CharField(max_length=32, default="active", index=True)  # active, paused, archived
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_agency_clients"


class AdAgencyMember(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    workspace_id = CharField(max_length=32, null=False, index=True)
    user_id = CharField(max_length=32, null=False, index=True)
    email = CharField(max_length=128, null=False, index=True)
    role = CharField(max_length=32, default="media_buyer")  # agency_admin, media_buyer, creative_designer, financial_auditor, client_viewer
    assigned_client_ids = JSONField(null=True, default=list)  # empty means access to all clients in workspace
    status = CharField(max_length=32, default="active", index=True)  # active, invited, suspended
    invite_token = CharField(max_length=64, null=True)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_agency_members"


class AdAgencyReportTemplate(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    workspace_id = CharField(max_length=32, null=False, index=True)
    client_id = CharField(max_length=32, null=True, index=True)
    report_title = CharField(max_length=128, null=False)
    sections_included = JSONField(null=True, default=list)  # kpi_summary, spend_roas, channel_breakdown, top_creatives, executive_takeaways
    period_type = CharField(max_length=32, default="last_30d")  # last_7d, last_30d, last_90d, custom
    is_public_shareable = BooleanField(default=False, index=True)
    share_token = CharField(max_length=64, null=True, index=True)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_agency_report_templates"


class AdOmniChannelAccount(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    platform = CharField(max_length=32, null=False, index=True)  # telegram_ads, meta_ads, google_ads, tiktok_ads, yandex_direct
    account_name = CharField(max_length=128, null=False)
    account_id_external = CharField(max_length=128, null=True)
    access_token = TextField(null=True)
    refresh_token = TextField(null=True)
    auth_status = CharField(max_length=32, default="connected", index=True)  # connected, expired, error, disconnected
    default_currency = CharField(max_length=8, default="USD")
    auto_sync_enabled = BooleanField(default=True)
    total_campaigns_exported = IntegerField(default=0)
    total_external_spend = FloatField(default=0.0)
    last_sync_time = BigIntegerField(null=True)
    create_time = BigIntegerField(null=False, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_omnichannel_accounts"


class AdOmniChannelSyncJob(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    advertiser_id = CharField(max_length=32, null=False, index=True)
    account_id = CharField(max_length=32, null=False, index=True)
    campaign_id = CharField(max_length=32, null=True, index=True)
    platform = CharField(max_length=32, null=False, index=True)
    job_type = CharField(max_length=32, default="export_campaign", index=True)  # export_campaign, sync_audiences, pull_metrics
    status = CharField(max_length=32, default="success", index=True)  # pending, running, success, failed
    external_campaign_id = CharField(max_length=128, null=True)
    payload_data = JSONField(null=True, default=dict)
    response_data = JSONField(null=True, default=dict)
    items_synced_count = IntegerField(default=1)
    error_message = TextField(null=True)
    create_time = BigIntegerField(null=False, index=True)
    finish_time = BigIntegerField(null=True)

    class Meta:
        db_table = "ad_omnichannel_sync_jobs"


class PromoCode(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    code = CharField(max_length=64, unique=True, index=True)
    discount_type = CharField(max_length=32, default="percent")  # percent, fixed_usd, advertiser_bonus_usd
    discount_value = FloatField(default=0.0)  # e.g. 20.0 for 20% or $20
    applies_to = CharField(max_length=32, default="all", index=True)  # subscription, advertiser_deposit, all
    plan_id = CharField(max_length=32, null=True)  # plus, pro, or null for all
    max_uses = IntegerField(default=100)
    used_count = IntegerField(default=0)
    is_active = BooleanField(default=True, index=True)
    expires_at = BigIntegerField(null=True)
    create_time = BigIntegerField(null=True, index=True)
    update_time = BigIntegerField(null=True)

    class Meta:
        db_table = "promo_codes"


class PromoCodeUsage(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    promo_code_id = CharField(max_length=32, null=False, index=True)
    user_id = CharField(max_length=32, null=False, index=True)
    order_id = CharField(max_length=64, null=True, index=True)
    discount_applied = FloatField(default=0.0)
    create_time = BigIntegerField(null=False, index=True)

    class Meta:
        db_table = "promo_code_usages"


GAUSSDB_EMPTY_STRING_COMPATIBLE_COLUMNS = (
    ("user", ("nickname",)),
    ("tenant", ("llm_id", "embd_id", "asr_id", "img2txt_id", "rerank_id")),
    ("knowledgebase", ("embd_id",)),
    ("dialog", ("llm_id", "rerank_id")),
    ("memory", ("embd_id", "llm_id")),
    ("file", ("source_type",)),
    ("document", ("suffix",)),
    ("system_settings", ("value",)),
    ("task", ("task_type",)),
    ("sync_logs", ("error_msg", "full_exception_trace")),
    ("api_4_conversation", ("user_id",)),
    ("user_canvas", ("tags",)),
)


def _quote_identifier_for_gaussdb(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def relax_gaussdb_empty_string_compatible_columns():
    if not is_gaussdb_compatible_database():
        return

    # These fields retain their historical application-level empty-string
    # semantics, but A/ORA-compatible GaussDB stores "" as NULL. Existing
    # databases must therefore make only these listed columns nullable. MySQL,
    # PostgreSQL, and unlisted fields remain unchanged.
    for table_name, column_names in GAUSSDB_EMPTY_STRING_COMPATIBLE_COLUMNS:
        quoted_table = _quote_identifier_for_gaussdb(table_name)
        for column_name in column_names:
            quoted_column = _quote_identifier_for_gaussdb(column_name)
            try:
                DB.execute_sql(f"ALTER TABLE {quoted_table} ALTER COLUMN {quoted_column} DROP NOT NULL")
            except Exception as ex:
                # Match the migration framework's behavior for failed column
                # additions or type changes: log at critical and continue
                # startup. This avoids aborting on a missing historical column
                # while identifying the constraint that was not relaxed.
                logging.critical(
                    "Failed to relax GaussDB empty-string compatible column %s.%s: %s",
                    table_name,
                    column_name,
                    ex,
                )


def alter_db_add_column(migrator, table_name, column_name, column_type):
    if is_gaussdb_compatible_database():
        try:
            migrate(migrator.add_column(table_name, column_name, column_type))
        except (OperationalError, ProgrammingError) as ex:
            if not is_duplicate_column_error(ex):
                logging.critical(f"Failed to add {settings.DATABASE_TYPE.upper()}.{table_name} column {column_name}, operation error: {ex}")
        except Exception as ex:
            logging.critical(f"Failed to add {settings.DATABASE_TYPE.upper()}.{table_name} column {column_name}, error: {ex}")
        return

    try:
        migrate(migrator.add_column(table_name, column_name, column_type))
    except OperationalError as ex:
        error_codes = [1060, 1068]
        error_messages = ["Duplicate column name", "Multiple primary key defined"]

        should_skip_error = (hasattr(ex, "args") and ex.args and ex.args[0] in error_codes) or (str(ex) in error_messages)

        if not should_skip_error:
            logging.critical(f"Failed to add {settings.DATABASE_TYPE.upper()}.{table_name} column {column_name}, operation error: {ex}")

    except Exception as ex:
        logging.critical(f"Failed to add {settings.DATABASE_TYPE.upper()}.{table_name} column {column_name}, error: {ex}")
        pass


def alter_db_column_type(migrator, table_name, column_name, new_column_type):
    try:
        migrate(migrator.alter_column_type(table_name, column_name, new_column_type))
    except Exception as ex:
        logging.critical(f"Failed to alter {settings.DATABASE_TYPE.upper()}.{table_name} column {column_name} type, error: {ex}")
        pass


def alter_db_rename_column(migrator, table_name, old_column_name, new_column_name):
    try:
        migrate(migrator.rename_column(table_name, old_column_name, new_column_name))
    except Exception:
        # rename fail will lead to a weired error.
        # logging.critical(f"Failed to rename {settings.DATABASE_TYPE.upper()}.{table_name} column {old_column_name} to {new_column_name}, error: {ex}")
        pass


def alter_db_drop_index(migrator, table_name, index_name):
    try:
        migrate(migrator.drop_index(table_name, index_name))
    except Exception:
        # rename fail will lead to a weired error.
        # logging.critical(f"Failed to rename {settings.DATABASE_TYPE.upper()}.{table_name} column {old_column_name} to {new_column_name}, error: {ex}")
        pass


def ensure_model_indexes(migrator):
    """Create indexes declared by the Peewee models when they are missing."""
    members = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    for name, model in members:
        if model == DataBaseModel or not issubclass(model, DataBaseModel):
            continue

        table_name = model._meta.table_name
        expected = {}
        for field in model._meta.fields.values():
            if field.primary_key:
                continue
            if field.index or field.unique:
                expected[(field.name,)] = bool(field.unique)

        for columns, unique in model._meta.indexes:
            expected[tuple(columns)] = bool(unique)

        if not expected:
            continue

        try:
            existing = {tuple(index.columns): bool(index.unique) for index in DB.get_indexes(table_name)}
        except Exception as ex:
            logging.error(f"Failed to inspect indexes on {table_name}: {ex}")
            continue

        for columns, unique in expected.items():
            if columns in existing and (not unique or existing[columns]):
                continue
            try:
                migrate(migrator.add_index(table_name, columns, unique=unique))
                logging.info(f"Created {'unique ' if unique else ''}index on {table_name} ({', '.join(columns)})")
            except Exception as ex:
                logging.error(f"Failed to create {'unique ' if unique else ''}index on {table_name} ({', '.join(columns)}): {ex}")


def _gaussdb_user_email_unique_index_exists() -> bool:
    cursor = DB.execute_sql(
        """
        SELECT COUNT(*)
        FROM pg_indexes
        WHERE schemaname = current_schema()
          AND tablename = 'user'
          AND lower(indexdef) LIKE %s
          AND (
            lower(indexdef) LIKE %s
            OR lower(indexdef) LIKE %s
          )
    """,
        ("create unique index%", "%(email)%", '%("email")%'),
    )
    result = cursor.fetchone()
    return bool(result and result[0] > 0)


def migrate_add_unique_email(migrator):
    """Deduplicates user emails and add UNIQUE constraint to email column (idempotent)"""
    # step 0: check existing index state on user.email and prepare for unique constraint
    try:
        if is_gaussdb_compatible_database():
            # GaussDB cannot use MySQL information_schema.statistics or
            # backtick syntax. Query pg_indexes through a distinct GaussDB path
            # so future catalog changes remain isolated in
            # _gaussdb_user_email_unique_index_exists.
            if _gaussdb_user_email_unique_index_exists():
                logging.info("UNIQUE index on user.email already exists, skipping migration")
                return
        elif settings.DATABASE_TYPE.upper() == "POSTGRES":
            cursor = DB.execute_sql("""
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE tablename = 'user'
                  AND indexname = 'user_email'
            """)
            result = cursor.fetchone()
            if result and result[0] > 0:
                logging.info("UNIQUE index on user.email already exists, skipping migration")
                return
        else:
            # Fetch the first index on email: tells us both the name and whether it's unique.
            # non_unique=0 means unique, non_unique=1 means non-unique.
            cursor = DB.execute_sql("""
                SELECT index_name, non_unique
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = 'user'
                  AND column_name = 'email'
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                index_name, non_unique = row
                if non_unique == 0:
                    logging.info("UNIQUE index on user.email already exists, skipping migration")
                    return
                # Non-unique index exists (e.g. from old peewee index=True); drop it so
                # the upcoming ADD UNIQUE INDEX does not hit MySQL error 1061 "Duplicate key name".
                DB.execute_sql(f"ALTER TABLE `user` DROP INDEX `{index_name}`")
                logging.info(f"Dropped non-unique index '{index_name}' on user.email before adding unique index")
    except Exception as ex:
        logging.warning(f"Failed to check/prepare email index on user table: {ex}, continuing with migration")

    # step 1: rename duplicate rows so the UNIQUE constraint can be applied
    try:
        duplicates = User.select(User.email).group_by(User.email).having(fn.COUNT(User.id) > 1).tuples()
        for (dup_email,) in duplicates:
            # Keep the superuser row, or the oldest row if there is no superuser
            rows = list(User.select(User.id).where(User.email == dup_email).order_by(User.is_superuser.desc(), User.create_time.asc()).tuples())
            for (uid,) in rows[1:]:
                new_email = f"{dup_email}_DUPLICATE_{uid[:8]}"
                User.update(email=new_email).where(User.id == uid).execute()
                logging.warning("Renamed duplicate user %s email to %s during migration", uid, new_email)
    except Exception as ex:
        logging.critical("Failed to deduplicate user.email before adding UNIQUE constraint: %s", ex)
        return

    # step 2: add UNIQUE index via migrator
    try:
        migrate(migrator.add_index("user", ("email",), unique=True))
    except (OperationalError, ProgrammingError) as ex:
        msg = str(ex)
        if is_gaussdb_compatible_database():
            already_exists = is_duplicate_object_error(ex)
        else:
            # Preserve the upstream MySQL/PostgreSQL handling.
            already_exists = "1061" in msg or "Duplicate key name" in msg or "already exists" in msg.lower()
        if already_exists:
            pass
        else:
            logging.critical("Failed to add UNIQUE constraint on user.email: %s", ex)
    except Exception as ex:
        logging.critical("Failed to add UNIQUE constraint on user.email: %s", ex)


def update_tenant_llm_to_id_primary_key():
    """Add ID and set to primary key step by step."""
    if is_gaussdb_compatible_database():
        # Use the GaussDB implementation for sequences, catalogs, and constraint
        # DDL instead of MySQL AUTO_INCREMENT/INFORMATION_SCHEMA or a branch
        # labeled as PostgreSQL.
        _update_tenant_llm_to_id_primary_key_gaussdb()
    elif settings.DATABASE_TYPE.upper() == "POSTGRES":
        _update_tenant_llm_to_id_primary_key_postgres()
    else:
        _update_tenant_llm_to_id_primary_key_mysql()


def _update_tenant_llm_to_id_primary_key_mysql():
    """MySQL implementation: Add ID column and set as AUTO_INCREMENT primary key."""
    try:
        with DB.atomic():
            # 0. Check if 'id' column already exists
            cursor = DB.execute_sql("""
                            SELECT COLUMN_NAME
                            FROM INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_SCHEMA = DATABASE()
                            AND TABLE_NAME = 'tenant_llm'
                            AND COLUMN_NAME = 'id'
                        """)
            if cursor.rowcount > 0:
                return

            # 1. Add nullable column
            DB.execute_sql("ALTER TABLE tenant_llm ADD COLUMN temp_id INT NULL")

            # 2. Set ID using MySQL user variables
            DB.execute_sql("SET @row = 0;")
            DB.execute_sql("UPDATE tenant_llm SET temp_id = (@row := @row + 1) ORDER BY tenant_id, llm_factory, llm_name;")

            # 3. Drop old primary key
            DB.execute_sql("ALTER TABLE tenant_llm DROP PRIMARY KEY")

            # 4. Update ID column to primary key with AUTO_INCREMENT
            DB.execute_sql("""
            ALTER TABLE tenant_llm
            MODIFY COLUMN temp_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY
            """)

            # 5. Add unique key
            DB.execute_sql("""
                ALTER TABLE tenant_llm
                ADD CONSTRAINT uk_tenant_llm UNIQUE (tenant_id, llm_factory, llm_name)
            """)

            # 6. rename
            DB.execute_sql("ALTER TABLE tenant_llm RENAME COLUMN temp_id TO id")

            logging.info("Successfully updated tenant_llm to id primary key.")

    except Exception as e:
        logging.error(str(e))
        cursor = DB.execute_sql("""
                                    SELECT COLUMN_NAME
                                    FROM INFORMATION_SCHEMA.COLUMNS
                                    WHERE TABLE_SCHEMA = DATABASE()
                                    AND TABLE_NAME = 'tenant_llm'
                                    AND COLUMN_NAME = 'temp_id'
                                """)
        if cursor.rowcount > 0:
            DB.execute_sql("ALTER TABLE tenant_llm DROP COLUMN temp_id")


def _update_tenant_llm_to_id_primary_key_postgres():
    """PostgreSQL implementation: Add SERIAL primary key column to tenant_llm."""
    try:
        with DB.atomic():
            # 0. Check if 'id' column already exists
            cursor = DB.execute_sql("""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_catalog = current_database()
                            AND table_name = 'tenant_llm'
                            AND column_name = 'id'
                        """)
            if cursor.rowcount > 0:
                return

            # 1. Add nullable integer column
            DB.execute_sql("ALTER TABLE tenant_llm ADD COLUMN temp_id INTEGER NULL")

            # 2. Assign sequential row numbers ordered consistently
            DB.execute_sql("""
                UPDATE tenant_llm
                SET temp_id = subq.rn
                FROM (
                    SELECT ctid,
                           ROW_NUMBER() OVER (ORDER BY tenant_id, llm_factory, llm_name) AS rn
                    FROM tenant_llm
                ) AS subq
                WHERE tenant_llm.ctid = subq.ctid
            """)

            # 3. Drop old composite primary key constraint
            cursor = DB.execute_sql("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_catalog = current_database()
                  AND table_name = 'tenant_llm'
                  AND constraint_type = 'PRIMARY KEY'
            """)
            row = cursor.fetchone()
            if row:
                DB.execute_sql(f'ALTER TABLE tenant_llm DROP CONSTRAINT "{row[0]}"')

            # 4. Make temp_id NOT NULL and create a sequence for it
            DB.execute_sql("ALTER TABLE tenant_llm ALTER COLUMN temp_id SET NOT NULL")
            DB.execute_sql("CREATE SEQUENCE IF NOT EXISTS tenant_llm_id_seq")
            DB.execute_sql("""
                SELECT setval('tenant_llm_id_seq', COALESCE((SELECT MAX(temp_id) FROM tenant_llm), 0))
            """)
            DB.execute_sql("ALTER TABLE tenant_llm ALTER COLUMN temp_id SET DEFAULT nextval('tenant_llm_id_seq')")
            DB.execute_sql("ALTER SEQUENCE tenant_llm_id_seq OWNED BY tenant_llm.temp_id")
            DB.execute_sql("ALTER TABLE tenant_llm ADD PRIMARY KEY (temp_id)")

            # 5. Add unique constraint
            DB.execute_sql("""
                ALTER TABLE tenant_llm
                ADD CONSTRAINT uk_tenant_llm UNIQUE (tenant_id, llm_factory, llm_name)
            """)

            # 6. Rename temp_id to id
            DB.execute_sql("ALTER TABLE tenant_llm RENAME COLUMN temp_id TO id")

            logging.info("Successfully updated tenant_llm to id primary key (PostgreSQL).")

    except Exception as e:
        logging.error(str(e))
        cursor = DB.execute_sql("""
                                    SELECT column_name
                                    FROM information_schema.columns
                                    WHERE table_catalog = current_database()
                                    AND table_name = 'tenant_llm'
                                    AND column_name = 'temp_id'
                                """)
        if cursor.rowcount > 0:
            DB.execute_sql("ALTER TABLE tenant_llm DROP COLUMN temp_id")


class KnowledgeEntity(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=255, null=False, index=True)
    entity_type = CharField(max_length=64, null=False, index=True, help_text="Person|Project|Tech|Doc|Org|Customer|Decision")
    description = TextField(null=True)
    canonical_id = CharField(max_length=32, null=True, index=True)
    attributes = JSONField(null=True, default=dict)
    confidence_score = FloatField(default=1.0)

    class Meta:
        db_table = "knowledge_entity"


class EntityAlias(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    alias_name = CharField(max_length=255, null=False, index=True)
    entity_id = CharField(max_length=32, null=False, index=True)
    source_type = CharField(max_length=64, null=True)

    class Meta:
        db_table = "entity_alias"


class KnowledgeRelation(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    src_entity_id = CharField(max_length=32, null=False, index=True)
    predicate = CharField(max_length=64, null=False, index=True, help_text="OWNS|USES|CREATED|DISCUSSED|FIXES|EXPERT_IN")
    dst_entity_id = CharField(max_length=32, null=False, index=True)
    weight = FloatField(default=1.0)
    confidence_score = FloatField(default=1.0)
    conversation_id = CharField(max_length=32, null=True, index=True)
    document_id = CharField(max_length=32, null=True, index=True)
    source_snippet = TextField(null=True)

    class Meta:
        db_table = "knowledge_relation"


class ConversationMetadata(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    conversation_id = CharField(max_length=32, null=False, unique=True, index=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    user_id = CharField(max_length=32, null=False, index=True)
    department = CharField(max_length=128, null=True)
    project_id = CharField(max_length=32, null=True, index=True)
    topics = JSONField(null=True, default=list)
    tags = JSONField(null=True, default=list)
    summary = TextField(null=True)
    decisions_json = JSONField(null=True, default=list)
    action_items_json = JSONField(null=True, default=list)
    unresolved_questions = JSONField(null=True, default=list)
    referenced_doc_ids = JSONField(null=True, default=list)
    models_used = JSONField(null=True, default=list)
    agents_involved = JSONField(null=True, default=list)
    language = CharField(max_length=16, null=True, default="en")
    duration_seconds = IntegerField(default=0)

    class Meta:
        db_table = "conversation_metadata"


class ExpertiseProfile(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    user_id = CharField(max_length=32, null=False, index=True)
    domain_topic = CharField(max_length=128, null=False, index=True)
    confidence_score = FloatField(default=0.0)
    depth_level = CharField(max_length=32, default="Intermediate")
    contribution_count = IntegerField(default=1)
    evidence_summary = TextField(null=True)
    last_active_at = BigIntegerField(null=False)

    class Meta:
        db_table = "expertise_profile"


class SummaryRegistry(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    summary_type = CharField(max_length=32, null=False, index=True, help_text="Daily|Weekly|Monthly|Project|Customer|Department")
    target_id = CharField(max_length=64, null=False, index=True)
    title = CharField(max_length=255, null=False)
    content = TextField(null=False)
    key_decisions = JSONField(null=True, default=list)
    key_risks = JSONField(null=True, default=list)
    trending_topics = JSONField(null=True, default=list)
    period_start = BigIntegerField(null=False)
    period_end = BigIntegerField(null=False)

    class Meta:
        db_table = "summary_registry"


class EILAuditLog(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    operator_id = CharField(max_length=32, null=False, index=True)
    action = CharField(max_length=64, null=False, index=True)
    resource_type = CharField(max_length=64, null=False)
    resource_id = CharField(max_length=64, null=True)
    details = JSONField(null=True, default=dict)
    ip_address = CharField(max_length=45, null=True)

    class Meta:
        db_table = "eil_audit_log"


class EILUserOnboarding(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=32, null=False, unique=True, index=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    department = CharField(max_length=128, null=True)
    role_description = TextField(null=True)
    expertise_tags = JSONField(null=True, default=list)
    primary_projects = JSONField(null=True, default=list)
    is_completed = IntegerField(default=0)

    class Meta:
        db_table = "eil_user_onboarding"



def _update_tenant_llm_to_id_primary_key_gaussdb():
    """GaussDB-compatible implementation: add sequence-backed primary key."""
    # GaussDB can perform this migration with pg_attribute, pg_constraint, and
    # a sequence. Keep the entry point distinct so catalog, ctid, or sequence
    # differences can be handled without changing the PostgreSQL path.
    _update_tenant_llm_to_id_primary_key_gaussdb_catalog()


def _update_tenant_llm_to_id_primary_key_gaussdb_catalog():
    """GaussDB pg_catalog implementation for the tenant_llm migration."""
    try:
        with DB.atomic():
            # 0. Check if 'id' column already exists
            # information_schema rowcount is unreliable on GaussDB. Query
            # pg_attribute and use fetchone() to prevent a duplicate migration.
            cursor = DB.execute_sql("""
                            SELECT a.attname
                            FROM pg_attribute a
                            JOIN pg_class c ON c.oid = a.attrelid
                            JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE n.nspname = current_schema()
                            AND c.relname = 'tenant_llm'
                            AND a.attname = 'id'
                            AND NOT a.attisdropped
                        """)
            if cursor.fetchone():
                return

            # 1. Add nullable integer column
            DB.execute_sql("ALTER TABLE tenant_llm ADD COLUMN temp_id INTEGER NULL")

            # 2. Assign sequential row numbers ordered consistently
            DB.execute_sql("""
                UPDATE tenant_llm
                SET temp_id = subq.rn
                FROM (
                    SELECT ctid,
                           ROW_NUMBER() OVER (ORDER BY tenant_id, llm_factory, llm_name) AS rn
                    FROM tenant_llm
                ) AS subq
                WHERE tenant_llm.ctid = subq.ctid
            """)

            # 3. Drop old composite primary key constraint
            # Older tenant_llm tables use (tenant_id, llm_factory, llm_name) as
            # a composite primary key. The new schema needs an id primary key
            # and a composite unique constraint. Read the actual constraint name
            # from pg_constraint instead of assuming a fixed name.
            cursor = DB.execute_sql("""
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class c ON c.oid = con.conrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = current_schema()
                  AND c.relname = 'tenant_llm'
                  AND con.contype = 'p'
            """)
            row = cursor.fetchone()
            if row:
                DB.execute_sql(f'ALTER TABLE tenant_llm DROP CONSTRAINT "{row[0]}"')

            # 4. Make temp_id NOT NULL and create a sequence for it
            # GaussDB and PostgreSQL do not use MySQL AUTO_INCREMENT here. A
            # sequence with nextval() provides the generated key, and OWNED BY
            # keeps its lifecycle tied to the column after temp_id becomes id.
            DB.execute_sql("ALTER TABLE tenant_llm ALTER COLUMN temp_id SET NOT NULL")
            DB.execute_sql("CREATE SEQUENCE IF NOT EXISTS tenant_llm_id_seq")
            DB.execute_sql("""
                SELECT setval('tenant_llm_id_seq', COALESCE((SELECT MAX(temp_id) FROM tenant_llm), 0))
            """)
            DB.execute_sql("ALTER TABLE tenant_llm ALTER COLUMN temp_id SET DEFAULT nextval('tenant_llm_id_seq')")
            DB.execute_sql("ALTER SEQUENCE tenant_llm_id_seq OWNED BY tenant_llm.temp_id")
            DB.execute_sql("ALTER TABLE tenant_llm ADD PRIMARY KEY (temp_id)")

            # 5. Add unique constraint
            DB.execute_sql("""
                ALTER TABLE tenant_llm
                ADD CONSTRAINT uk_tenant_llm UNIQUE (tenant_id, llm_factory, llm_name)
            """)

            # 6. Rename temp_id to id
            DB.execute_sql("ALTER TABLE tenant_llm RENAME COLUMN temp_id TO id")

            logging.info("Successfully updated tenant_llm to id primary key (GaussDB).")

    except Exception as e:
        logging.error(str(e))
        cursor = DB.execute_sql("""
                                    SELECT a.attname
                                    FROM pg_attribute a
                                    JOIN pg_class c ON c.oid = a.attrelid
                                    JOIN pg_namespace n ON n.oid = c.relnamespace
                                    WHERE n.nspname = current_schema()
                                    AND c.relname = 'tenant_llm'
                                    AND a.attname = 'temp_id'
                                    AND NOT a.attisdropped
                                """)
        if cursor.fetchone():
            DB.execute_sql("ALTER TABLE tenant_llm DROP COLUMN temp_id")


def migrate_db():
    logging.disable(logging.ERROR)
    migrator = DatabaseMigrator[settings.DATABASE_TYPE.upper()].value(DB)
    alter_db_add_column(migrator, "file", "source_type", EmptyStringCharField(max_length=128, null=False, default="", help_text="where dose this document come from", index=True))
    alter_db_add_column(migrator, "tenant", "rerank_id", EmptyStringCharField(max_length=128, null=False, default="BAAI/bge-reranker-v2-m3", help_text="default rerank model ID"))
    alter_db_add_column(migrator, "dialog", "rerank_id", EmptyStringCharField(max_length=128, null=False, default="", help_text="default rerank model ID"))
    alter_db_column_type(migrator, "dialog", "top_k", IntegerField(default=1024))
    alter_db_add_column(migrator, "tenant_llm", "api_key", CharField(max_length=2048, null=True, help_text="API KEY", index=True))
    alter_db_add_column(migrator, "api_token", "source", CharField(max_length=16, null=True, help_text="none|agent|dialog", index=True))
    alter_db_add_column(migrator, "tenant", "tts_id", CharField(max_length=256, null=True, help_text="default tts model ID", index=True))
    alter_db_add_column(migrator, "api_4_conversation", "source", CharField(max_length=16, null=True, help_text="none|agent|dialog", index=True))
    alter_db_add_column(migrator, "task", "retry_count", IntegerField(default=0))
    alter_db_column_type(migrator, "api_token", "dialog_id", CharField(max_length=32, null=True, index=True))
    alter_db_add_column(migrator, "tenant_llm", "max_tokens", IntegerField(default=8192, index=True))
    alter_db_add_column(migrator, "api_4_conversation", "dsl", JSONField(null=True, default={}))
    alter_db_add_column(migrator, "knowledgebase", "pagerank", IntegerField(default=0, index=False))
    alter_db_add_column(migrator, "api_token", "beta", CharField(max_length=255, null=True, index=True))
    alter_db_add_column(migrator, "task", "digest", TextField(null=True, help_text="task digest", default=""))
    alter_db_add_column(migrator, "task", "chunk_ids", EmptyStringLongTextField(null=True, help_text="chunk ids", default=""))
    alter_db_add_column(migrator, "conversation", "user_id", CharField(max_length=255, null=True, help_text="user_id", index=True))
    alter_db_add_column(migrator, "task", "task_type", EmptyStringCharField(max_length=32, null=False, default=""))
    alter_db_add_column(migrator, "task", "priority", IntegerField(default=0))
    alter_db_add_column(migrator, "user_canvas", "permission", CharField(max_length=16, null=False, help_text="me|team", default="me", index=True))
    alter_db_add_column(migrator, "user_canvas", "release", BooleanField(null=False, help_text="is released", default=False, index=True))
    alter_db_add_column(migrator, "llm", "is_tools", BooleanField(null=False, help_text="support tools", default=False))
    alter_db_add_column(migrator, "mcp_server", "variables", JSONField(null=True, help_text="MCP Server variables", default=dict))
    alter_db_rename_column(migrator, "task", "process_duation", "process_duration")
    alter_db_rename_column(migrator, "document", "process_duation", "process_duration")
    alter_db_add_column(migrator, "document", "suffix", EmptyStringCharField(max_length=32, null=False, default="", help_text="The real file extension suffix", index=True))
    alter_db_add_column(migrator, "api_4_conversation", "errors", TextField(null=True, help_text="errors"))
    alter_db_add_column(migrator, "dialog", "meta_data_filter", JSONField(null=True, default={}))
    alter_db_add_column(migrator, "dialog", "rerank_candidates_count", IntegerField(default=64))
    alter_db_column_type(migrator, "canvas_template", "title", JSONField(null=True, default=dict, help_text="Canvas title"))
    alter_db_column_type(migrator, "canvas_template", "description", JSONField(null=True, default=dict, help_text="Canvas description"))
    alter_db_add_column(migrator, "user_canvas", "canvas_category", CharField(max_length=32, null=False, default="agent_canvas", help_text="agent_canvas|dataflow_canvas", index=True))
    alter_db_add_column(migrator, "canvas_template", "canvas_category", CharField(max_length=32, null=False, default="agent_canvas", help_text="agent_canvas|dataflow_canvas", index=True))
    alter_db_add_column(migrator, "canvas_template", "canvas_types", ListField(null=True, default=list, help_text="Canvas types"))
    alter_db_add_column(migrator, "knowledgebase", "pipeline_id", CharField(max_length=32, null=True, help_text="Pipeline ID", index=True))
    alter_db_add_column(migrator, "chat_channel", "dialog_id", CharField(max_length=32, null=True, help_text="connected dialog id", index=True))
    alter_db_add_column(migrator, "document", "pipeline_id", CharField(max_length=32, null=True, help_text="Pipeline ID", index=True))
    alter_db_add_column(migrator, "knowledgebase", "graphrag_task_id", CharField(max_length=32, null=True, help_text="Gragh RAG task ID", index=True))
    alter_db_add_column(migrator, "knowledgebase", "raptor_task_id", CharField(max_length=32, null=True, help_text="RAPTOR task ID", index=True))
    alter_db_add_column(migrator, "knowledgebase", "graphrag_task_finish_at", DateTimeField(null=True))
    alter_db_add_column(migrator, "knowledgebase", "raptor_task_finish_at", DateTimeField(null=True))
    alter_db_add_column(migrator, "knowledgebase", "mindmap_task_id", CharField(max_length=32, null=True, help_text="Mindmap task ID", index=True))
    alter_db_add_column(migrator, "knowledgebase", "mindmap_task_finish_at", DateTimeField(null=True))
    alter_db_rename_column(migrator, "knowledgebase", "artifact_task_id", "wiki_task_id")
    alter_db_rename_column(migrator, "knowledgebase", "artifact_task_finish_at", "wiki_task_finish_at")
    alter_db_add_column(migrator, "knowledgebase", "wiki_task_id", CharField(max_length=32, null=True, help_text="Artifact compilation task ID", index=True))
    alter_db_add_column(migrator, "knowledgebase", "wiki_task_finish_at", DateTimeField(null=True))
    alter_db_add_column(migrator, "knowledgebase", "skill_task_id", CharField(max_length=32, null=True, help_text="Skill generation task ID", index=True))
    alter_db_add_column(migrator, "knowledgebase", "skill_task_finish_at", DateTimeField(null=True))
    for _structure_type in ("structure_graph", "structure_mindmap", "timeline", "session_graph", "session_essence", "structure"):
        alter_db_add_column(migrator, "knowledgebase", f"{_structure_type}_task_id", CharField(max_length=32, null=True, help_text=f"{_structure_type} merge task ID", index=True))
        alter_db_add_column(migrator, "knowledgebase", f"{_structure_type}_task_finish_at", DateTimeField(null=True))
    alter_db_column_type(migrator, "tenant_llm", "api_key", TextField(null=True, help_text="API KEY"))
    alter_db_add_column(migrator, "tenant_llm", "status", CharField(max_length=1, null=False, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True))
    alter_db_add_column(migrator, "connector2kb", "auto_parse", CharField(max_length=1, null=False, default="1", index=False))
    alter_db_add_column(migrator, "llm_factories", "rank", IntegerField(default=0, index=False))
    alter_db_add_column(migrator, "api_4_conversation", "name", CharField(max_length=255, null=True, help_text="conversation name", index=False))
    alter_db_add_column(migrator, "api_4_conversation", "exp_user_id", CharField(max_length=255, null=True, help_text="exp_user_id", index=True))
    alter_db_add_column(migrator, "sync_logs", "task_type", CharField(max_length=32, null=False, default="sync", index=True))
    # Migrate system_settings.value from CharField to TextField for longer sandbox configs.
    # Use the dedicated field so the GaussDB column remains nullable after the
    # type change and the ORM restores NULL to the application-level "".
    alter_db_column_type(migrator, "system_settings", "value", EmptyStringTextField(null=False, help_text="Configuration value (JSON, string, etc.)"))
    alter_db_add_column(migrator, "document", "content_hash", CharField(max_length=32, null=True, help_text="xxhash128 of document content for change detection", default="", index=True))
    alter_db_add_column(migrator, "user_canvas_version", "release", BooleanField(null=False, help_text="is released", default=False, index=True))
    alter_db_add_column(
        migrator,
        "user_canvas",
        "tags",
        EmptyStringCharField(
            max_length=512,
            null=False,
            default="",
            help_text="Comma-separated tags for organizing agents",
            index=True,
        ),
    )
    alter_db_add_column(migrator, "api_4_conversation", "version_title", CharField(max_length=255, null=True, help_text="canvas version title when session created", index=False))
    alter_db_column_type(migrator, "document", "size", BigIntegerField(default=0, index=True))
    alter_db_column_type(migrator, "file", "size", BigIntegerField(default=0, index=True))
    alter_db_add_column(migrator, "tenant", "ocr_id", CharField(max_length=128, null=True, help_text="default ocr model ID", index=True))
    alter_db_add_column(migrator, "user", "is_onboarded", BooleanField(null=True, help_text="is onboarding survey completed", default=False, index=True))
    alter_db_add_column(migrator, "user", "onboarding_info", TextField(null=True, help_text="onboarding survey responses"))
    try:
        DB.execute_sql("ALTER TABLE user ADD COLUMN is_onboarded TINYINT(1) DEFAULT 0;")
    except Exception:
        pass
    try:
        DB.execute_sql("ALTER TABLE user ADD COLUMN onboarding_info TEXT;")
    except Exception:
        pass
    try:
        admin_emails = os.getenv("DEFAULT_SUPERUSER_EMAIL", "admin@ragflow.io,albakiev.sardorbek@gmail.com")
        if not admin_emails or not admin_emails.strip():
            admin_emails = "admin@ragflow.io,albakiev.sardorbek@gmail.com"
        for em in [e.strip().lower() for e in admin_emails.split(",") if e.strip()]:
            DB.execute_sql(f"UPDATE user SET is_superuser = 1 WHERE LOWER(email) = '{em}';")
        DB.execute_sql("UPDATE user_tenant SET role = 'owner' WHERE tenant_id = user_id AND role = 'normal';")
    except Exception:
        pass
    try:
        DB.execute_sql("ALTER TABLE advertisers ADD COLUMN pixel_id VARCHAR(32) NULL;")
    except Exception:
        pass
    try:
        DB.execute_sql("ALTER TABLE advertisers ADD UNIQUE INDEX idx_advertisers_pixel_id (pixel_id);")
    except Exception:
        pass
    try:
        DB.execute_sql("ALTER TABLE advertisers ADD COLUMN website_url VARCHAR(1024) NULL;")
    except Exception:
        pass
    alter_db_add_column(migrator, "tenant", "tenant_ocr_id", CharField(max_length=32, null=True, help_text="id in tenant_model", index=True))
    alter_db_column_type(migrator, "chat_channel", "status", IntegerField(default=1, index=True))
    alter_db_rename_column(migrator, "chat_channel", "dialog_id", "chat_id")
    alter_db_add_column(migrator, "chat_channel", "agent_id", CharField(max_length=32, null=True, help_text="connected agent id", index=True))
    # ---- FileCommit / FileCommitItem: artifact-page commit extension ----
    alter_db_add_column(migrator, "file_commit", "title", CharField(max_length=255, null=True))
    alter_db_add_column(migrator, "file_commit", "comments", TextField(null=True))
    alter_db_add_column(migrator, "file_commit_item", "diff", LongTextField(null=True))
    alter_db_add_column(migrator, "file_commit_item", "content_after_storage", CharField(max_length=16, null=True, index=True))
    alter_db_add_column(migrator, "file_commit_item", "content_after_location", CharField(max_length=512, null=True))
    alter_db_add_column(migrator, "file_commit_item", "slug_kwd", CharField(max_length=512, null=True, index=True))
    alter_db_add_column(migrator, "file_commit_item", "page_type_kwd", CharField(max_length=32, null=True, index=True))
    alter_db_drop_index(migrator, "tenant_langfuse", "idx_tenant_langfuse_secret_key")
    alter_db_drop_index(migrator, "tenant_langfuse", "idx_tenant_langfuse_public_key")
    alter_db_drop_index(migrator, "tenant_langfuse", "idx_tenant_langfuse_host")
    # Run after all alter_db_* calls so newly added compatible columns, such as
    # user_canvas.tags, exist before their GaussDB NOT NULL constraints relax.
    relax_gaussdb_empty_string_compatible_columns()

    # Drop both the explicit "idx_*" name from later migrations AND the
    # Peewee-auto-derived "<table-as-classname>_<col1>_<col2>" name from the
    # original TenantModelInstance definition (commit dc4b82523). Databases
    # created before #15460 dropped the model's `indexes = ((...,), True)`
    # tuple still carry the auto-named compound unique index, which makes a
    # second instance with an empty api_key (e.g. Ollama) fail with
    # "Duplicate entry ... for key 'tenantmodelinstance_api_key_provider_id'"
    # — see #15699.
    legacy_indexes = [
        ("tenant_model_instance", "idx_api_key_provider_id"),
        ("tenant_model_instance", "tenantmodelinstance_api_key_provider_id"),
        ("tenant_model", "idx_provider_model_instance"),
        ("compilation_template", "compilationtemplate_tenant_id_name_is_builtin_status"),
        ("compilation_template", "compilation_template_tenant_id_name_is_builtin_status"),
        ("compilation_template", "idx_compilation_template_tenant_id_name_is_builtin_status"),
        ("compilation_template_group", "compilationtemplategroup_tenant_id_name_status"),
        ("compilation_template_group", "compilation_template_group_tenant_id_name_status"),
        ("compilation_template_group", "idx_compilation_template_group_tenant_id_name_status"),
    ]
    for table_name, index_name in legacy_indexes:
        try:
            migrate(migrator.drop_index(table_name, index_name))
        except (OperationalError, ProgrammingError) as ex:
            msg = str(ex)
            if is_gaussdb_compatible_database():
                can_skip = is_undefined_object_error(ex) or is_duplicate_object_error(ex)
            else:
                can_skip = "1091" in msg or "can't DROP" in msg.lower() or "does not exist" in msg.lower() or "already exists" in msg.lower()
            if can_skip:
                pass
            else:
                logging.critical(f"Failed to drop index {index_name} on {table_name}: {ex}")
        except Exception as ex:
            logging.critical(f"Failed to drop index {index_name} on {table_name}: {ex}")
    alter_db_add_column(migrator, "api_token", "name", CharField(max_length=255, null=True, help_text="API key name"))
    alter_db_add_column(migrator, "api_token", "status", CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True))
    alter_db_add_column(migrator, "tenant", "plan_type", CharField(max_length=32, default="free", index=True))
    alter_db_add_column(migrator, "tenant", "plan_expiry_date", DateTimeField(null=True, index=True))
    alter_db_add_column(migrator, "user", "phone", CharField(max_length=32, null=True, help_text="phone number", index=True))
    alter_db_add_column(migrator, "user", "referred_by_id", CharField(max_length=32, null=True, help_text="referred by user id", index=True))
    alter_db_add_column(migrator, "user", "marketing_consent", BooleanField(null=True, help_text="consent to receive marketing newsletters and promotions", default=True, index=True))

    # Add AI infrastructure columns
    alter_db_add_column(migrator, "subscription_plan", "daily_token_limit", BigIntegerField(default=50000, help_text="Daily token limit"))
    alter_db_add_column(migrator, "subscription_plan", "daily_request_limit", IntegerField(default=500, help_text="Daily request limit"))
    alter_db_add_column(migrator, "subscription_plan", "monthly_request_limit", IntegerField(default=10000, help_text="Monthly request limit"))
    alter_db_add_column(migrator, "subscription_plan", "requests_per_minute", IntegerField(default=60, help_text="Rate limit per minute"))
    alter_db_add_column(migrator, "subscription_plan", "max_tokens_per_request", IntegerField(default=4096, help_text="Max tokens per request"))
    alter_db_add_column(migrator, "subscription_plan", "allow_byok", BooleanField(default=False))
    alter_db_add_column(migrator, "subscription_plan", "max_byok_models", IntegerField(default=0))
    alter_db_add_column(migrator, "subscription_plan", "default_rerank_id", CharField(max_length=128, null=True))

    alter_db_add_column(migrator, "ai_model", "input_token_price", FloatField(default=0.0, help_text="USD per 1M input tokens"))
    alter_db_add_column(migrator, "ai_model", "output_token_price", FloatField(default=0.0, help_text="USD per 1M output tokens"))
    alter_db_add_column(migrator, "ai_model", "max_tokens", IntegerField(default=8192))
    alter_db_add_column(migrator, "ai_model", "owner_user_id", CharField(max_length=32, null=True, index=True))
    alter_db_add_column(migrator, "ai_model", "owner_tenant_id", CharField(max_length=32, null=True, index=True))
    alter_db_add_column(migrator, "ai_model", "status", CharField(max_length=32, default="active", index=True))
    alter_db_add_column(migrator, "ai_model", "global_instance_id", CharField(max_length=32, default="GLOBAL", index=True))
    alter_db_add_column(migrator, "ai_model", "extra", JSONField(null=True, default=dict))
    alter_db_add_column(migrator, "ai_model", "create_time", BigIntegerField(null=True))
    alter_db_add_column(migrator, "ai_model", "update_time", BigIntegerField(null=True))

    alter_db_add_column(migrator, "subscription_ai_policy", "is_default_rerank", BooleanField(default=False))

    alter_db_add_column(migrator, "token_usage_log", "global_instance_id", CharField(max_length=32, default="GLOBAL", index=True))
    alter_db_add_column(migrator, "token_usage_log", "provider_id", CharField(max_length=128, null=True, index=True))
    alter_db_add_column(migrator, "token_usage_log", "estimated_cost", FloatField(default=0.0))
    alter_db_add_column(migrator, "token_usage_log", "status", CharField(max_length=32, default="SUCCESS", index=True))
    alter_db_add_column(migrator, "token_usage_log", "date_str", CharField(max_length=10, null=True, index=True))
    alter_db_add_column(migrator, "token_usage_log", "create_time", BigIntegerField(null=True, index=True))

    logging.disable(logging.NOTSET)
    # this is after re-enabling logging to allow logging changed user emails
    migrate_add_unique_email(migrator)
    migrate_model_type_names()
    ensure_model_indexes(migrator)


def migrate_model_type_names():
    """Rename legacy model_type string values to the canonical asr/vision names.

    Previously the code used speech2text / image2text. LLMType now emits asr /
    vision, and the backend compares model_type strings directly. This idempotent
    data migration updates persisted rows in llm and tenant_llm before the new
    enum values are used at runtime.
    """
    RENAME_MAP = {
        "speech2text": "asr",
        "image2text": "vision",
    }
    tables = ["llm", "tenant_llm"]
    for table in tables:
        if not DB.table_exists(table):
            continue
        for old_name, new_name in RENAME_MAP.items():
            try:
                cursor = DB.execute_sql(
                    "UPDATE {} SET model_type = %s WHERE model_type = %s".format(table),
                    (new_name, old_name),
                )
                if cursor.rowcount:
                    logging.info(
                        "Migrated %s rows in %s.model_type from %s to %s",
                        cursor.rowcount,
                        table,
                        old_name,
                        new_name,
                    )
            except Exception as ex:
                logging.warning(
                    "Failed to migrate model_type values in %s (from %s to %s): %s",
                    table,
                    old_name,
                    new_name,
                    ex,
                )
