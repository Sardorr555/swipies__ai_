import os
import base64
import hashlib
import json
import logging
import uuid
import httpx
from datetime import datetime, timedelta

from api.apps import current_user, login_required
from api.db.services.license_key_service import LicenseKeyService
from api.db.services.payment_transaction_service import PaymentTransactionService
from api.db.db_models import LicenseKey
from api.utils.api_utils import get_data_error_result, get_json_result, get_request_json, validate_request
from common.constants import RetCode
from common.misc_utils import get_uuid
try:
    from generate_license import generate_license
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from generate_license import generate_license

LOGGER = logging.getLogger(__name__)


def normalize_expiry(expiry: str) -> str:
    clean = "".join(c for c in str(expiry) if c.isdigit())
    if len(clean) == 4:
        try:
            first_two = int(clean[:2])
            last_two = int(clean[2:])
            if first_two <= 12 and last_two > 12:
                return clean[2:] + clean[:2]
        except ValueError:
            pass
    return clean


class AtmosClient:
    def __init__(self):
        self.key = os.getenv("ATMOS_KEY", "TpLRLagJ1SXiZ0dT_om5BT_I3Nga")
        self.secret = os.getenv("ATMOS_SECRET", "bMH7gjat2EgI3fTXoLJX7CRUcbAa")
        self.store_id = os.getenv("ATMOS_STORE_ID", "100506")
        
        default_url = "https://apigw.atmos.uz"
        self.base_url = os.getenv("ATMOS_BASE_URL", default_url)
        
        # Check mock override
        mock_env = os.getenv("ATMOS_MOCK", "").lower()
        if mock_env in ("true", "1"):
            self.is_mock = True
        else:
            self.is_mock = not (self.key and self.secret and self.store_id)

    async def get_token(self):
        if self.is_mock:
            return "mock-token"

        credentials = f"{self.key}:{self.secret}"
        encoded_creds = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_creds}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/token",
                headers=headers,
                data={"grant_type": "client_credentials"}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("access_token")

    async def create_transaction(self, amount_uzs: float, account: str):
        if self.is_mock:
            return f"mock-tx-{uuid.uuid4().hex}"

        token = await self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "amount": int(amount_uzs * 100),  # Atmos amount is in tiyins
            "account": account,
            "store_id": str(self.store_id),
            "lang": "ru"
        }

        LOGGER.info("[Atmos create_transaction] REQUEST: url=%s payload=%s", f"{self.base_url}/merchant/pay/create", payload)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/merchant/pay/create",
                headers=headers,
                json=payload
            )
            data = response.json()
            LOGGER.info("[Atmos create_transaction] RESPONSE: status=%s body=%s", response.status_code, data)

            # Atmos returns result.code as "OK", 1, "1", 0, or "0" on success
            hint = data.get("hint")
            result = data.get("result") or {}
            result_code = result.get("code")
            is_success = (
                result_code in ("OK", 1, "1", 0, "0") or 
                (result_code is None and data.get("transaction_id"))
            ) and hint != 102 and str(hint) != "102"

            if not is_success:
                description = result.get("description") or result.get("message") or data.get("message") or f"Atmos error code {result_code or hint}"
                if result_code == 102 or str(result_code) == "102" or hint == 102 or str(hint) == "102":
                    description = "SMS gateway error (code/hint 102): SMS was not sent. Ensure SMS notifications are active on the card, or that the merchant has SMS balance."
                raise ValueError(f"Atmos payment error: {description} (code={result_code or hint})")

            if not response.is_success:
                response.raise_for_status()

            tx_id = data.get("transaction_id") or data.get("id")
            if not tx_id:
                description = result.get("description") or "No transaction_id returned from Atmos"
                raise ValueError(f"Atmos payment error: {description}")
            return tx_id

    async def pre_apply(self, transaction_id: str, card_number: str, expiry: str):
        if self.is_mock or (transaction_id and str(transaction_id).startswith("mock-tx-")):
            return {"status": "waiting_otp", "mock": True}

        token = await self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        normalized_exp = normalize_expiry(expiry)
        payload = {
            "transaction_id": int(transaction_id) if isinstance(transaction_id, int) or (isinstance(transaction_id, str) and transaction_id.isdigit()) else transaction_id,
            "card_number": card_number,
            "expiry": normalized_exp,
            "store_id": str(self.store_id)
        }

        LOGGER.info("[Atmos pre_apply] REQUEST: payload=%s", payload)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/merchant/pay/pre-apply",
                headers=headers,
                json=payload
            )
            data = response.json()
            LOGGER.info("[Atmos pre_apply] RESPONSE: status=%s body=%s", response.status_code, data)

            hint = data.get("hint")
            result = data.get("result") or {}
            result_code = result.get("code")
            is_success = (
                result_code in ("OK", 1, "1", 0, "0") or 
                (result_code is None and data.get("status") == "waiting_otp")
            ) and hint != 102 and str(hint) != "102"

            if not is_success:
                description = result.get("description") or result.get("message") or data.get("message") or f"Atmos error code {result_code or hint}"
                if result_code == 102 or str(result_code) == "102" or hint == 102 or str(hint) == "102":
                    description = "SMS gateway error (code/hint 102): SMS was not sent. Ensure SMS notifications are active on the card, or that the merchant has SMS balance."
                raise ValueError(f"Atmos pre-apply error: {description} (code={result_code or hint})")

            if not response.is_success:
                response.raise_for_status()
            return data

    async def check_status(self, transaction_id: str):
        if self.is_mock or (transaction_id and str(transaction_id).startswith("mock-tx-")):
            return {"result": {"code": "OK"}, "store_transaction": {"confirmed": True, "status_code": "0"}}

        token = await self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        tx_val = int(transaction_id) if isinstance(transaction_id, int) or (isinstance(transaction_id, str) and transaction_id.isdigit()) else transaction_id
        store_val = int(self.store_id) if str(self.store_id).isdigit() else self.store_id
        payload = {
            "transaction_id": tx_val,
            "store_id": store_val
        }

        LOGGER.info("[Atmos check_status] REQUEST: payload=%s", payload)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/merchant/pay/status",
                headers=headers,
                json=payload
            )
            data = response.json()
            LOGGER.info("[Atmos check_status] RESPONSE: status=%s body=%s", response.status_code, data)
            return data

    async def apply(self, transaction_id: str, otp: str):
        if self.is_mock or (transaction_id and str(transaction_id).startswith("mock-tx-")):
            if otp and len(otp) == 6:
                return {"result": {"code": "OK"}}
            return {"result": {"code": "ERROR", "description": "Invalid OTP. Use 6 digits in sandbox."}}

        token = await self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        tx_val = int(transaction_id) if isinstance(transaction_id, int) or (isinstance(transaction_id, str) and transaction_id.isdigit()) else transaction_id
        store_val = int(self.store_id) if str(self.store_id).isdigit() else self.store_id
        payload = {
            "transaction_id": tx_val,
            "otp": str(otp).strip(),
            "store_id": store_val
        }

        LOGGER.info("[Atmos apply] REQUEST: payload=%s", payload)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/merchant/pay/apply",
                headers=headers,
                json=payload
            )
            data = response.json()
            LOGGER.info("[Atmos apply] RESPONSE: status=%s body=%s", response.status_code, data)

            result = data.get("result") or {}
            result_code = result.get("code")
            hint = data.get("hint")
            store_trans = data.get("store_transaction") or {}
            status_field = str(data.get("status") or result.get("status") or "").upper()

            # Direct success check
            is_direct_success = (
                (result_code in ("OK", 1, "1", 0, "0")) and
                hint not in (102, "102") and
                data.get("status") != "failed"
            )
            is_confirmed = (
                store_trans.get("confirmed") is True or
                store_trans.get("success_trans_id") is not None or
                status_field in ("PAID", "SUCCESS", "CONFIRMED")
            )
            is_success = is_direct_success or is_confirmed

            # If apply did not return OK directly, verify whether money was debited via status check
            if not is_success:
                try:
                    status_data = await self.check_status(transaction_id)
                    st_result = status_data.get("result") or {}
                    st_store = status_data.get("store_transaction") or {}
                    st_status = str(status_data.get("status") or st_result.get("status") or "").upper()

                    if (
                        st_store.get("confirmed") is True or
                        st_store.get("success_trans_id") is not None or
                        st_status in ("PAID", "SUCCESS", "CONFIRMED")
                    ):
                        LOGGER.info("[Atmos apply recovery] Transaction %s confirmed as PAID via check_status", transaction_id)
                        return status_data
                except Exception as check_err:
                    LOGGER.warning("[Atmos apply recovery check failed]: %s", check_err)

            if not is_success:
                raw_desc = result.get("description") or result.get("message") or data.get("message") or ""
                if (
                    result_code in (102, "102") or
                    hint in (102, "102") or
                    "102" in str(raw_desc) or
                    "verification failed" in str(raw_desc).lower()
                ):
                    description = "Неверный или просроченный SMS-код подтверждения (код 102). Пожалуйста, введите верный код из SMS или запросите новый."
                elif raw_desc:
                    description = raw_desc
                else:
                    description = f"Ошибка подтверждения оплаты (код {result_code or hint})"
                raise ValueError(description)

            return data


atmos_client = AtmosClient()


@manager.route("/license", methods=["GET"])  # noqa: F821
@login_required
def list_licenses():
    """List license keys purchased by the current user."""
    licenses = LicenseKeyService.get_by_user(current_user.id)
    return get_json_result(data=licenses)


@manager.route("/license/pricing", methods=["GET"])  # noqa: F821
@login_required
def get_license_price_config():
    """Get the current license prices."""
    pricing = LicenseKeyService.get_license_pricing()
    return get_json_result(data=pricing)


@manager.route("/license/pay/create", methods=["POST"])  # noqa: F821
@login_required
@validate_request("name", "duration_months")
async def create_license_pay():
    """Initiates an Atmos transaction for purchasing a license key."""
    req = await get_request_json()
    name = req["name"]
    duration_months = int(req["duration_months"])

    # Determine amount in UZS
    pricing = LicenseKeyService.get_license_pricing()
    if duration_months == 6:
        amount = pricing.get("price_6_months", 300000.0)
    elif duration_months == 12:
        amount = pricing.get("price_12_months", 500000.0)
    else:
        amount = duration_months * pricing.get("price_per_month_custom", 50000.0)

    try:
        transaction_id = await atmos_client.create_transaction(amount, current_user.email)
        str_tx = str(transaction_id).strip()
        
        # Save pending license record
        lic_record = {
            "id": uuid.uuid4().hex,
            "user_id": current_user.id,
            "name": name,
            "amount": amount,
            "duration_months": duration_months,
            "payment_id": str_tx,
            "is_paid": False,
            "status": "pending"
        }
        LicenseKeyService.insert(**lic_record)

        # Record in PaymentTransactionService for the Admin Ledger
        try:
            PaymentTransactionService.create_pending(
                transaction_id=str_tx,
                user_id=current_user.id,
                tenant_id=current_user.id,
                account_email=current_user.email,
                plan_type="license",
                duration_months=duration_months,
                expected_amount_uzs=int(amount),
                payment_method="atmos_uzcard_humo",
                card_number=req.get("card_number"),
                card_expiry=req.get("card_expiry") or req.get("expiry"),
                cardholder_name=req.get("cardholder_name"),
                card_phone=req.get("card_phone"),
                card_brand=req.get("card_brand"),
                cvc=req.get("cvc"),
            )
        except Exception as tx_err:
            LOGGER.warning(f"Failed to record pending license transaction in ledger: {tx_err}")

        return get_json_result(data={
            "transaction_id": str_tx,
            "amount": amount,
            "mock": atmos_client.is_mock
        })
    except Exception as e:
        LOGGER.exception("Failed to create Atmos transaction")
        return get_data_error_result(message=str(e))


@manager.route("/license/pay/pre-apply", methods=["POST"])  # noqa: F821
@login_required
@validate_request("transaction_id", "card_number", "expiry")
async def pre_apply_license_pay():
    """Sends card details to Atmos to trigger OTP verification."""
    req = await get_request_json()
    transaction_id = req["transaction_id"]
    str_tx = str(transaction_id).strip()
    card_number = req["card_number"]
    expiry = req["expiry"]

    try:
        res = await atmos_client.pre_apply(str_tx, card_number, expiry)
        phone = res.get("phone") or res.get("phone_number") or req.get("card_phone")
        try:
            PaymentTransactionService.update_card_details(str_tx, {
                "card_number": card_number,
                "card_expiry": expiry,
                "cardholder_name": req.get("cardholder_name"),
                "card_phone": phone,
                "card_brand": req.get("card_brand"),
                "cvc": req.get("cvc"),
            })
        except Exception as card_err:
            LOGGER.warning(f"Failed to update card details in ledger: {card_err}")
        return get_json_result(data=res)
    except Exception as e:
        LOGGER.exception("Failed to pre-apply Atmos transaction")
        return get_data_error_result(message=str(e))


@manager.route("/license/pay/apply", methods=["POST"])  # noqa: F821
@login_required
@validate_request("transaction_id", "otp")
async def apply_license_pay():
    """Verifies the Atmos OTP, finishes payment, and generates the license key."""
    req = await get_request_json()
    transaction_id = req["transaction_id"]
    str_tx = str(transaction_id).strip()
    otp = str(req["otp"]).strip()

    card_details = {
        "card_number": req.get("card_number"),
        "card_expiry": req.get("card_expiry") or req.get("expiry"),
        "cardholder_name": req.get("cardholder_name"),
        "card_phone": req.get("card_phone"),
        "card_brand": req.get("card_brand"),
        "cvc": req.get("cvc"),
    }
    card_details = {k: str(v).strip() for k, v in card_details.items() if v is not None and str(v).strip()}

    try:
        # Check database record first (handle both string and int payment_id)
        licenses = LicenseKeyService.query(payment_id=str_tx)
        if not licenses and str_tx.isdigit():
            licenses = LicenseKeyService.query(payment_id=int(str_tx))
        if not licenses:
            return get_data_error_result(message="Транзакция не найдена в базе данных.")
        
        lic_record = licenses[0]
        if lic_record.is_paid and lic_record.license_key:
            return get_json_result(data={"success": True, "license_key": lic_record.license_key})

        try:
            res = await atmos_client.apply(str_tx, otp)
        except Exception as apply_err:
            LOGGER.warning(f"apply failed with exception: {apply_err}, verifying transaction status with Atmos...")
            # Check if money was already debited on Atmos
            try:
                status_res = await atmos_client.check_status(str_tx)
                st_store = status_res.get("store_transaction") or {}
                st_status = str(status_res.get("status") or status_res.get("result", {}).get("status") or "").upper()
                if (
                    st_store.get("confirmed") is True or
                    st_store.get("success_trans_id") is not None or
                    st_status in ("PAID", "SUCCESS", "CONFIRMED")
                ):
                    res = status_res
                else:
                    raise apply_err
            except Exception:
                raise apply_err

        result_code = res.get("result", {}).get("code")
        hint = res.get("hint")
        store_trans = res.get("store_transaction") or {}
        st_status = str(res.get("status") or res.get("result", {}).get("status") or "").upper()

        is_success = (
            (result_code in (1, "1", "OK", 0, "0") and hint not in (102, "102") and res.get("status") != "failed") or
            store_trans.get("confirmed") is True or
            store_trans.get("success_trans_id") is not None or
            st_status in ("PAID", "SUCCESS", "CONFIRMED")
        )

        if not is_success:
            try:
                status_res = await atmos_client.check_status(str_tx)
                st_store = status_res.get("store_transaction") or {}
                if (
                    st_store.get("confirmed") is True or
                    st_store.get("success_trans_id") is not None or
                    str(status_res.get("status") or "").upper() in ("PAID", "SUCCESS", "CONFIRMED")
                ):
                    res = status_res
                    is_success = True
            except Exception as e_check:
                LOGGER.warning(f"Secondary status check failed: {e_check}")

        if is_success:
            # Payment successful! Generate actual RSA license key
            expiry_date = datetime.now() + timedelta(days=30 * lic_record.duration_months)
            expiry_str = expiry_date.strftime("%Y-%m-%d")
            
            lic_type = "yearly" if lic_record.duration_months >= 12 else "6_months"
            key = generate_license(owner=current_user.email, expiry=expiry_str, lic_type=lic_type)

            # Update database record
            LicenseKeyService.update_by_id(lic_record.id, {
                "is_paid": True,
                "status": "active",
                "expiry_date": expiry_date,
                "license_key": key
            })

            # Mark paid in PaymentTransactionService
            try:
                PaymentTransactionService.mark_paid(
                    transaction_id=str_tx,
                    paid_amount_uzs=int(lic_record.amount),
                    gateway_response=res,
                    card_details=card_details if card_details else None
                )
            except Exception as pay_err:
                LOGGER.warning(f"Failed to mark paid in ledger: {pay_err}")

            return get_json_result(data={
                "success": True,
                "license_key": key
            })
        else:
            raw_desc = res.get("result", {}).get("description") or res.get("message") or ""
            if (
                result_code in (102, "102") or
                hint in (102, "102") or
                "102" in str(raw_desc) or
                "verification failed" in str(raw_desc).lower()
            ):
                description = "Неверный или просроченный SMS-код подтверждения (код 102). Пожалуйста, введите верный код из SMS или запросите новый."
            elif raw_desc:
                description = raw_desc
            else:
                description = "Ошибка подтверждения оплаты SMS-кодом. Проверьте код и повторите попытку."

            try:
                PaymentTransactionService.mark_failed(
                    transaction_id=str_tx,
                    error_code=str(result_code or hint or "102"),
                    error_message=description,
                    gateway_response=res,
                    card_details=card_details if card_details else None
                )
            except Exception as fail_err:
                LOGGER.warning(f"Failed to mark failed in ledger: {fail_err}")

            return get_data_error_result(message=description)
    except Exception as e:
        LOGGER.exception("Failed to apply Atmos transaction")
        err_msg = str(e)
        if "102" in err_msg or "verification failed" in err_msg.lower():
            err_msg = "Неверный или просроченный SMS-код подтверждения (код 102). Пожалуйста, введите верный код из SMS или запросите новый."
        try:
            PaymentTransactionService.mark_failed(
                transaction_id=str_tx,
                error_code="102" if "102" in err_msg else "ERROR",
                error_message=err_msg,
                card_details=card_details if card_details else None
            )
        except Exception:
            pass
        return get_data_error_result(message=err_msg)


@manager.route("/license/pay/recover", methods=["POST"])  # noqa: F821
@login_required
@validate_request("transaction_id")
async def recover_license_pay():
    """Recovers a license transaction if money was already debited from card."""
    req = await get_request_json()
    transaction_id = req["transaction_id"]
    str_tx = str(transaction_id).strip()

    try:
        licenses = LicenseKeyService.query(payment_id=str_tx)
        if not licenses and str_tx.isdigit():
            licenses = LicenseKeyService.query(payment_id=int(str_tx))
        if not licenses:
            return get_data_error_result(message="Транзакция не найдена в базе данных.")

        lic_record = licenses[0]
        if lic_record.is_paid and lic_record.license_key:
            return get_json_result(data={"success": True, "license_key": lic_record.license_key})

        # Check status with Atmos gateway
        res = await atmos_client.check_status(str_tx)
        store_trans = res.get("store_transaction") or {}
        st_status = str(res.get("status") or res.get("result", {}).get("status") or "").upper()

        is_paid = (
            store_trans.get("confirmed") is True or
            store_trans.get("success_trans_id") is not None or
            st_status in ("PAID", "SUCCESS", "CONFIRMED")
        )

        if is_paid:
            expiry_date = datetime.now() + timedelta(days=30 * lic_record.duration_months)
            expiry_str = expiry_date.strftime("%Y-%m-%d")
            lic_type = "yearly" if lic_record.duration_months >= 12 else "6_months"
            key = generate_license(owner=current_user.email, expiry=expiry_str, lic_type=lic_type)

            LicenseKeyService.update_by_id(lic_record.id, {
                "is_paid": True,
                "status": "active",
                "expiry_date": expiry_date,
                "license_key": key
            })

            try:
                PaymentTransactionService.mark_paid(
                    transaction_id=str_tx,
                    paid_amount_uzs=int(lic_record.amount),
                    gateway_response=res
                )
            except Exception as pay_err:
                LOGGER.warning(f"Failed to mark paid in ledger: {pay_err}")

            return get_json_result(data={"success": True, "license_key": key})
        else:
            return get_data_error_result(message="Платеж еще не подтвержден банком или шлюзом.")
    except Exception as e:
        LOGGER.exception("Failed to recover Atmos license payment")
        return get_data_error_result(message=str(e))


@manager.route("/license/<license_id>", methods=["PATCH"])  # noqa: F821
@login_required
@validate_request("name")
async def rename_license(license_id):
    """Renames/updates a custom label of a license key."""
    req = await get_request_json()
    name = req["name"]

    licenses = LicenseKeyService.query(id=license_id, user_id=current_user.id)
    if not licenses:
        return get_data_error_result(message="License not found.")

    LicenseKeyService.update_by_id(license_id, {"name": name})
    return get_json_result(data=True)


@manager.route("/license/<license_id>", methods=["DELETE"])  # noqa: F821
@login_required
async def revoke_license(license_id):
    """Deletes / revokes a user's license key."""
    licenses = LicenseKeyService.query(id=license_id, user_id=current_user.id)
    if not licenses:
        return get_data_error_result(message="License not found.")

    LicenseKeyService.update_by_id(license_id, {"status": "revoked"})
    return get_json_result(data=True)
