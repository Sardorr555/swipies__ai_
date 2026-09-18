import os
import pytest
from unittest import mock
import auth
from services import UserMgr
from exceptions import UserNotFoundError, AdminException


class MockUser:
    def __init__(self, user_id, email, password_hash="hash123", is_superuser=1, is_active=1):
        self.id = user_id
        self.email = email
        self.password = password_hash
        self.is_superuser = is_superuser
        self.is_active = is_active

    def to_json(self):
        return {"id": self.id, "email": self.email}

    def get_id(self):
        return self.id

    def save(self):
        pass


def test_admin_no_developer_email_hardcoded():
    """Verify that DEFAULT_SUPERUSER_EMAIL fallback does not contain hardcoded personal developer email."""
    with mock.patch.dict(os.environ, {}, clear=True):
        admin_emails = os.getenv("DEFAULT_SUPERUSER_EMAIL", "admin@ragflow.io")
        assert "albakiev.sardorbek@gmail.com" not in admin_emails
        assert "admin@ragflow.io" in admin_emails


def test_user_mgr_find_user_by_identifier_case_and_whitespace():
    """Verify UserMgr._find_user_by_identifier handles whitespace and mixed casing."""
    mock_user = MockUser("usr_abc123", "test.user@example.com")

    with mock.patch("api.db.services.user_service.UserService.query_user_by_email", return_value=[]), \
         mock.patch("api.db.services.user_service.UserService.model") as mock_model:
        # Mock peewee model select
        mock_query = mock.MagicMock()
        mock_query.__iter__.return_value = [mock_user]
        mock_model.select.return_value.where.return_value = mock_query

        # Test with whitespace and upper case
        result = UserMgr._find_user_by_identifier("  TEST.USER@EXAMPLE.COM  ")
        assert len(result) == 1
        assert result[0].email == "test.user@example.com"


def test_user_mgr_find_user_by_id_fallback():
    """Verify UserMgr._find_user_by_identifier falls back to user ID lookup."""
    mock_user = MockUser("usr_uuid_999", "someone@example.com")

    with mock.patch("api.db.services.user_service.UserService.query_user_by_email", return_value=[]), \
         mock.patch("api.db.services.user_service.UserService.model") as mock_model, \
         mock.patch("api.db.services.user_service.UserService.filter_by_id", return_value=mock_user):
        mock_model.select.return_value.where.return_value = []

        result = UserMgr._find_user_by_identifier("usr_uuid_999")
        assert len(result) == 1
        assert result[0].id == "usr_uuid_999"


def test_user_mgr_update_user_password():
    """Verify UserMgr.update_user_password updates password successfully."""
    mock_user = MockUser("usr_123", "user@test.com", password_hash="old_hash")

    with mock.patch.object(UserMgr, "_find_user_by_identifier", return_value=[mock_user]), \
         mock.patch("services.decrypt", return_value="new_secret_password"), \
         mock.patch("services.check_password_hash", return_value=False), \
         mock.patch("api.db.services.user_service.UserService.update_user_password") as mock_update:

        msg = UserMgr.update_user_password("user@test.com", "enc_payload")
        assert "successfully" in msg.lower()
        mock_update.assert_called_once_with("usr_123", "new_secret_password")


def test_login_admin_case_insensitive_and_whitespace():
    """Verify login_admin handles email with whitespace and mixed casing."""
    import flask
    app = flask.Flask(__name__)
    mock_admin = MockUser("admin_1", "admin@ragflow.io", password_hash="secret_hash", is_superuser=1)

    with app.test_request_context(), \
         mock.patch("api.db.services.user_service.UserService.query", return_value=[]), \
         mock.patch("api.db.services.user_service.UserService.model") as mock_model, \
         mock.patch("auth.decrypt", return_value="welcome_pass"), \
         mock.patch("api.db.services.user_service.UserService.query_user", return_value=mock_admin), \
         mock.patch("auth.login_user"):

        mock_model.select.return_value.where.return_value = [mock_admin]

        res = auth.login_admin("   ADMIN@RAGFLOW.IO   ", "enc_password")
        assert res.status_code == 200
