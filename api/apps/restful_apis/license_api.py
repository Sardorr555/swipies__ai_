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
        self.key = os.getenv("ATMOS_KEY", "")
        self.secret = os.getenv("ATMOS_SECRET", "")
        self.store_id = os.getenv("ATMOS_STORE_ID", "")
        self.base_url = os.getenv("ATMOS_BASE_URL", "https://sandbox-api.atmos.uz")
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
            "store_id": int(self.store_id)
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/merchant/pay/create",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data.get("transaction_id") or data.get("id")

    async def pre_apply(self, transaction_id: str, card_number: str, expiry: str):
        if self.is_mock:
            return {"status": "waiting_otp", "mock": True}

        token = await self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "transaction_id": transaction_id,
            "card_number": card_number,
            "expiry": expiry,
            "store_id": int(self.store_id)
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/merchant/pay/pre-apply",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def apply(self, transaction_id: str, otp: str):
        if self.is_mock:
            if otp and len(otp) == 6:
                return {"result": {"code": "OK"}}
            return {"result": {"code": "ERROR", "description": "Invalid OTP. Use 6 digits in sandbox."}}

        token = await self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "transaction_id": transaction_id,
            "otp": otp,
            "store_id": int(self.store_id)
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/merchant/pay/apply",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()


atmos_client = AtmosClient()


@manager.route("/license", methods=["GET"])  # noqa: F821
@login_required
def list_licenses():
    """List license keys purchased by the current user."""
    licenses = LicenseKeyService.get_by_user(current_user.id)
    return get_json_result(data=licenses)


@manager.route("/license/pay/create", methods=["POST"])  # noqa: F821
@login_required
@validate_request("name", "duration_months")
async def create_license_pay():
    """Initiates an Atmos transaction for purchasing a license key."""
    req = await get_request_json()
    name = req["name"]
    duration_months = int(req["duration_months"])

    # Determine amount in UZS
    if duration_months == 6:
        amount = 300000.0
    elif duration_months == 12:
        amount = 500000.0
    else:
        amount = duration_months * 50000.0

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
        LicenseKeyService.save(**lic_record)

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
        result_code = res.get("result", {}).get("code", "")

        if result_code == "OK":
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
