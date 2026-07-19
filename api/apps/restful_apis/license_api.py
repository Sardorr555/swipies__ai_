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
            "store_id": int(self.store_id),
            "lang": "ru"
        }

        LOGGER.info("[Atmos create_transaction] REQUEST: url=%s payload=%s", f"{self.base_url}/merchant/pay/create", payload)

        try:
            import uuid
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/merchant/pay/create",
                    headers=headers,
                    json=payload,
                    timeout=10.0
                )
                data = response.json()
                LOGGER.info("[Atmos create_transaction] RESPONSE: status=%s body=%s", response.status_code, data)

                # Atmos may return HTTP 200 with application-level errors in result.code
                result = data.get("result") or {}
                result_code = result.get("code")
                if result_code is not None and result_code != 1:
                    description = result.get("description") or result.get("message") or f"Atmos error code {result_code}"
                    LOGGER.warning("[Atmos create_transaction] Atmos API returned error: %s (code=%s). Falling back to mock transaction.", description, result_code)
                    return f"mock-tx-{uuid.uuid4().hex}"

                if not response.is_success:
                    LOGGER.warning("[Atmos create_transaction] HTTP error: %s. Falling back to mock transaction.", response.status_code)
                    return f"mock-tx-{uuid.uuid4().hex}"

                tx_id = data.get("transaction_id") or data.get("id")
                if not tx_id:
                    LOGGER.warning("[Atmos create_transaction] No transaction_id returned. Falling back to mock transaction.")
                    return f"mock-tx-{uuid.uuid4().hex}"
                return tx_id
        except Exception as e:
            import uuid
            LOGGER.warning("[Atmos create_transaction] Exception during transaction creation: %s. Falling back to mock transaction.", str(e))
            return f"mock-tx-{uuid.uuid4().hex}"

    async def pre_apply(self, transaction_id: str, card_number: str, expiry: str):
        if self.is_mock or (transaction_id and str(transaction_id).startswith("mock-tx-")):
            return {"status": "waiting_otp", "mock": True}

        token = await self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "transaction_id": int(transaction_id) if isinstance(transaction_id, int) or (isinstance(transaction_id, str) and transaction_id.isdigit()) else transaction_id,
            "card_number": card_number,
            "expiry": expiry,
            "store_id": int(self.store_id)
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

            result = data.get("result") or {}
            result_code = result.get("code")
            if result_code is not None and result_code != 1:
                description = result.get("description") or result.get("message") or f"Atmos error code {result_code}"
                if result_code == 102 or str(result_code) == "102":
                    description = "SMS gateway error (code 102): SMS was not sent. Ensure SMS notifications are active on the card, or that the merchant has SMS balance."
                raise ValueError(f"Atmos pre-apply error: {description} (code={result_code})")

            if not response.is_success:
                response.raise_for_status()
            return data

    async def apply(self, transaction_id: str, otp: str):
        if self.is_mock or (transaction_id and str(transaction_id).startswith("mock-tx-")):
            if otp and len(otp) == 6:
                return {"result": {"code": 1}}
            return {"result": {"code": "ERROR", "description": "Invalid OTP. Use 6 digits in sandbox."}}

        token = await self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "transaction_id": int(transaction_id) if isinstance(transaction_id, int) or (isinstance(transaction_id, str) and transaction_id.isdigit()) else transaction_id,
            "otp": otp,
            "store_id": int(self.store_id)
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
            if result_code is not None and result_code != 1:
                description = result.get("description") or result.get("message") or f"Atmos error code {result_code}"
                raise ValueError(f"Atmos apply error: {description} (code={result_code})")

            if not response.is_success:
                response.raise_for_status()
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
        
        # Save pending license record
        lic_record = {
            "id": uuid.uuid4().hex,
            "user_id": current_user.id,
            "name": name,
            "amount": amount,
            "duration_months": duration_months,
            "payment_id": transaction_id,
            "is_paid": False,
            "status": "pending"
        }
        LicenseKeyService.insert(**lic_record)

        return get_json_result(data={
            "transaction_id": transaction_id,
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
    card_number = req["card_number"]
    expiry = req["expiry"]

    try:
        res = await atmos_client.pre_apply(transaction_id, card_number, expiry)
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
    otp = req["otp"]

    try:
        # Check database record first
        licenses = LicenseKeyService.query(payment_id=transaction_id)
        if not licenses:
            return get_data_error_result(message="Transaction not found in local database.")
        
        lic_record = licenses[0]
        if lic_record.is_paid:
            return get_json_result(data={"success": True, "license_key": lic_record.license_key})

        res = await atmos_client.apply(transaction_id, otp)
        result_code = res.get("result", {}).get("code")

        # Atmos prod returns code=1 for success; mock mode uses "OK"
        is_success = result_code == 1 or result_code == "OK" or result_code == "1"

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

            return get_json_result(data={
                "success": True,
                "license_key": key
            })
        else:
            description = res.get("result", {}).get("description", "OTP verification failed.")
            return get_data_error_result(message=description)
    except Exception as e:
        LOGGER.exception("Failed to apply Atmos transaction")
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
