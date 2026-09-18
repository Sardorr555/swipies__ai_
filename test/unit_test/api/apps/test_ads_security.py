import os
import ast
import pytest
from unittest import mock


def test_sec_01_billing_deposit_route_removed():
    """Verify that POST /v1/ads/billing/deposit is completely removed from ad_app.py (SEC-01)."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
    ad_app_path = os.path.join(repo_root, "api", "apps", "ad_app.py")

    with open(ad_app_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    assert "/billing/deposit" not in content, "SEC-01: /billing/deposit route must not exist in ad_app.py!"
    assert "deposit_funds" not in content, "SEC-01: deposit_funds handler must not exist in ad_app.py!"


def test_sec_02_payment_arbitrage_neutralized():
    """Verify that client-supplied amount_usd is ignored when amount_uzs is provided (SEC-02)."""
    from api.db.services.payment_service import AtmosService
    from api.db.db_models import DB, User

    mock_conf = {
        "usd_to_uzs_rate": 12800,
        "mock_mode": True,
        "store_id": "test_store_123",
    }

    with mock.patch.object(AtmosService, "_get_config", return_value=mock_conf), \
         mock.patch.object(User, "get_or_none", return_value=mock.MagicMock(email="test@example.com")), \
         mock.patch("api.db.db_models.PaymentOrder.create") as mock_create, \
         mock.patch.object(DB, "connect"), \
         mock.patch.object(DB, "is_closed", return_value=False), \
         mock.patch.object(DB, "close"):

        mock_order = mock.MagicMock()
        mock_order.id = "ord_test_123"
        mock_order.transaction_id = "tx_123"
        mock_order.amount_uzs = 100
        mock_order.amount_usd = 0.01
        mock_order.purpose = "advertiser_deposit"
        mock_order.plan_id = None
        mock_order.advertiser_id = "adv_test"
        mock_order.currency = "UZS"
        mock_order.status = "pending"
        mock_order.lang = "ru"
        mock_create.return_value = mock_order

        # Attack payload: amount_uzs = 100, amount_usd = 10000.0 (arbitrage attempt)
        success, msg, data = AtmosService.create_payment_order(
            user_id="usr_test",
            tenant_id="ten_test",
            purpose="advertiser_deposit",
            amount_uzs=100,
            amount_usd=10000.0,
            advertiser_id="adv_test",
        )

        assert success is True, f"create_payment_order failed: {msg}"
        # Check what arguments were passed to PaymentOrder.create
        assert mock_create.called, "PaymentOrder.create was not called!"
        create_kwargs = mock_create.call_args[1]
        assert create_kwargs["amount_uzs"] == 100
        # amount_usd must be ~0.01 USD (100 / 12800), NOT 10,000!
        assert create_kwargs["amount_usd"] == 0.01, f"Arbitrage detected! amount_usd was {create_kwargs['amount_usd']}"


def test_sec_03_subscription_renewals_requires_superuser():
    """Verify that /admin/subscriptions/process-renewals requires superuser (SEC-03)."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
    ad_app_path = os.path.join(repo_root, "api", "apps", "ad_app.py")

    with open(ad_app_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Parse AST to ensure require_superuser() is called inside admin_process_subscription_renewals
    tree = ast.parse(content)
    found_func = False
    has_superuser_check = False

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "admin_process_subscription_renewals":
            found_func = True
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call) and isinstance(subnode.func, ast.Name):
                    if subnode.func.id == "require_superuser":
                        has_superuser_check = True
                        break

    assert found_func, "admin_process_subscription_renewals not found in ad_app.py"
    assert has_superuser_check, "admin_process_subscription_renewals MUST invoke require_superuser()!"


def test_arch_03_no_runtime_ddl_in_pixel_id():
    """Verify that ConversionTrackingService.get_or_create_pixel_id contains zero ALTER TABLE execution."""
    from api.db.services.ad_engine_service import ConversionTrackingService
    from api.db.db_models import Advertiser, DB

    mock_adv = mock.MagicMock(spec=Advertiser)
    mock_adv.pixel_id = None

    with mock.patch.object(Advertiser, "get_or_none", return_value=mock_adv), \
         mock.patch.object(DB, "connect"), \
         mock.patch.object(DB, "is_closed", return_value=False), \
         mock.patch.object(DB, "close"), \
         mock.patch("api.db.db_models.DB.execute_sql") as mock_exec:

        pid = ConversionTrackingService.get_or_create_pixel_id("adv_test_id")
        assert pid.startswith("px_")
        # Ensure DB.execute_sql was NEVER called with ALTER TABLE
        for call in mock_exec.call_args_list:
            sql = str(call[0][0]).upper()
            assert "ALTER TABLE" not in sql, f"Runtime ALTER TABLE detected: {sql}"


def test_sec_07_no_developer_email_in_codebase():
    """Verify that developer personal email does not appear in production source code."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
    forbidden_email = "albakiev." + "sardorbek" + "@gmail.com"

    for root, dirs, files in os.walk(repo_root):
        if any(skip in root for skip in [".git", "node_modules", "specs", "docs", "test", "tests", ".venv"]):
            continue
        for f in files:
            if f.endswith((".py", ".ts", ".tsx", ".js", ".json")):
                full_path = os.path.join(root, f)
                with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                    assert forbidden_email not in content, f"Hardcoded developer email found in {full_path}"
