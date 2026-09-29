#!/usr/bin/env python3
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

"""
Connector Credentials Migration CLI (Part B).

Scans all connector records in the database, identifies plaintext credentials or legacy v1 ciphertexts in config,
and encrypts/upgrades them at rest using authenticated AES-256-GCM (enc:v2:).
Also provides --reverse for emergency rollback and --rotate for key rotation.

Usage:
  # 1. Preview forward encryption without modifying the database (SAFE):
  python api/scripts/migrate_connector_credentials.py --dry-run

  # 2. Perform actual encryption (requires database backup first):
  python api/scripts/migrate_connector_credentials.py --apply

  # 3. Emergency rollback (decrypts back to plaintext, requires DB backup first):
  python api/scripts/migrate_connector_credentials.py --reverse --apply

  # 4. Key rotation (re-encrypts with new primary master key using rotation keyring):
  python api/scripts/migrate_connector_credentials.py --rotate --apply
"""

import os
import sys
import copy
import argparse
import logging
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("MigrateConnectorCredentials")


def find_unencrypted_keys(config: dict) -> list[str]:
    """Inspects a config dictionary and returns a list of sensitive key paths that are not yet encrypted with enc:v2:."""
    from api.utils.key_crypto import _is_sensitive_connector_key, is_masked_value

    unencrypted = []

    def _walk(d: dict, prefix: str, in_credentials: bool):
        for k, v in d.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            sub_in_creds = in_credentials or (str(k).lower() == "credentials")
            if isinstance(v, dict):
                _walk(v, path, sub_in_creds)
            elif isinstance(v, list):
                for idx, item in enumerate(v):
                    if isinstance(item, dict):
                        _walk(item, f"{path}[{idx}]", sub_in_creds)
            elif isinstance(v, str):
                if _is_sensitive_connector_key(k, sub_in_creds):
                    trimmed = v.strip()
                    if trimmed and not trimmed.startswith("enc:v2:") and not is_masked_value(trimmed):
                        unencrypted.append(path)

    if isinstance(config, dict):
        _walk(config, "", False)
    return unencrypted


def find_encrypted_keys(config: dict) -> list[str]:
    """Inspects a config dictionary and returns a list of encrypted key paths (enc:v2: or enc:v1:)."""
    from api.utils.key_crypto import is_encrypted_key

    encrypted = []

    def _walk(d: dict, prefix: str):
        for k, v in d.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                _walk(v, path)
            elif isinstance(v, list):
                for idx, item in enumerate(v):
                    if isinstance(item, dict):
                        _walk(item, f"{path}[{idx}]")
            elif isinstance(v, str):
                if is_encrypted_key(v):
                    encrypted.append(path)

    if isinstance(config, dict):
        _walk(config, "")
    return encrypted


def run_migration(apply: bool = False, reverse: bool = False, rotate: bool = False):
    from api.db.db_models import Connector, DB
    from api.utils.key_crypto import encrypt_connector_config, decrypt_connector_config

    mode_label = "REVERSE (DECRYPT TO PLAINTEXT)" if reverse else ("KEY ROTATION" if rotate else "ENCRYPT TO AES-256-GCM")
    action_label = "LIVE APPLY" if apply else "DRY RUN (Preview Only)"
    print("\n" + "=" * 75)
    print(f"  CONNECTOR CREDENTIALS MIGRATION")
    print(f"  Action: {mode_label}")
    print(f"  Mode:   {action_label}")
    print("=" * 75)
    if not apply:
        print("  NOTE: No changes will be written to the database.")
        print("  To execute real migration, run with: --apply")
    else:
        print("  WARNING: Modifying database records. Ensure a full DB backup exists!")
    print("-" * 75 + "\n")

    total_count = 0
    clean_count = 0
    affected_count = 0
    error_count = 0

    try:
        with DB.connection_context():
            connectors = list(Connector.select())
            total_count = len(connectors)

            for conn in connectors:
                conn_id = conn.id
                conn_name = conn.name or "(unnamed)"
                conn_source = conn.source or "(unknown)"
                raw_config = conn.config or {}

                if reverse:
                    target_keys = find_encrypted_keys(raw_config)
                    status_name = "ENCRYPTED"
                elif rotate:
                    target_keys = find_encrypted_keys(raw_config)
                    status_name = "NEEDS_ROTATION"
                else:
                    target_keys = find_unencrypted_keys(raw_config)
                    status_name = "UNENCRYPTED"

                if not target_keys:
                    clean_count += 1
                    logger.debug(f"[OK] Connector {conn_id} ({conn_name} / {conn_source}) requires no changes.")
                    continue

                affected_count += 1
                logger.info(
                    f"[{'APPLYING' if apply else 'PLANNED'}] "
                    f"Connector: {conn_id} | Name: '{conn_name}' | Source: {conn_source} | "
                    f"{status_name} fields: {target_keys}"
                )

                if apply:
                    try:
                        if reverse:
                            new_config = decrypt_connector_config(raw_config)
                        elif rotate:
                            # Decrypt with rotation keyring, then re-encrypt with current primary key
                            decrypted = decrypt_connector_config(raw_config)
                            new_config = encrypt_connector_config(decrypted)
                        else:
                            new_config = encrypt_connector_config(raw_config)

                        conn.config = new_config
                        conn.save()
                        logger.info(f"  -> Successfully updated and saved connector {conn_id}")
                    except Exception as ex:
                        error_count += 1
                        logger.error(f"  -> Failed to update connector {conn_id}: {ex}")

    except Exception as ex:
        logger.error(f"Database connection or query failed: {ex}")
        sys.exit(1)

    print("\n" + "=" * 75)
    print("  MIGRATION SUMMARY")
    print("=" * 75)
    print(f"  Total connectors checked:        {total_count}")
    print(f"  Unchanged / up-to-date:          {clean_count}")
    print(f"  Connectors requiring change:     {affected_count}")
    if apply:
        print(f"  Successfully modified:           {affected_count - error_count}")
        print(f"  Errors encountered:              {error_count}")
    else:
        print(f"  Status:                          Preview complete. 0 records modified.")
    print("=" * 75 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate connector credentials in database: encrypt, rotate, or rollback."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Execute the changes and persist to database (default is preview dry-run)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview changes without modifying the database."
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        default=False,
        help="Emergency rollback: decrypt encrypted credentials back to plaintext."
    )
    parser.add_argument(
        "--rotate",
        action="store_true",
        default=False,
        help="Key rotation: decrypt with rotation keyring and re-encrypt with active primary key."
    )

    args = parser.parse_args()
    apply_mode = args.apply and not args.dry_run

    run_migration(apply=apply_mode, reverse=args.reverse, rotate=args.rotate)


if __name__ == "__main__":
    main()
