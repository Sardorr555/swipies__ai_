#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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

import base64
import json
import re
import os
import logging
import threading
import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from email.header import Header
from common import settings
from jinja2 import Template
from api.utils.email_templates import EMAIL_TEMPLATES
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


OTP_LENGTH = 4
OTP_TTL_SECONDS = 5 * 60  # valid for 5 minutes
ATTEMPT_LIMIT = 5  # maximum attempts
ATTEMPT_LOCK_SECONDS = 30 * 60  # lock for 30 minutes
RESEND_COOLDOWN_SECONDS = 60  # cooldown for 1 minute


CONTENT_TYPE_MAP = {
    # Office
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "pdf": "application/pdf",
    "csv": "text/csv",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    # Text/code
    "txt": "text/plain",
    "py": "text/plain",
    "js": "text/plain",
    "java": "text/plain",
    "c": "text/plain",
    "cpp": "text/plain",
    "h": "text/plain",
    "php": "text/plain",
    "go": "text/plain",
    "ts": "text/plain",
    "sh": "text/plain",
    "cs": "text/plain",
    "kt": "text/plain",
    "sql": "text/plain",
    # Web
    "md": "text/markdown",
    "markdown": "text/markdown",
    "mdx": "text/markdown",
    "htm": "text/html",
    "html": "text/html",
    "json": "application/json",
    # Image formats
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
    "tif": "image/tiff",
    "webp": "image/webp",
    "svg": "image/svg+xml",
    "ico": "image/x-icon",
    "avif": "image/avif",
    "heic": "image/heic",
    # PPTX
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


FORCE_ATTACHMENT_EXTENSIONS = {
    "htm",
    "html",
    "shtml",
    "xht",
    "xhtml",
    "xml",
    "mhtml",
    "svg",
}


FORCE_ATTACHMENT_CONTENT_TYPES = {
    "text/html",
    "image/svg+xml",
    "application/xhtml+xml",
    "text/xml",
    "application/xml",
    "multipart/related",
}


def should_force_attachment(ext: str | None, content_type: str | None = None) -> bool:
    normalized_ext = (ext or "").lower().strip(".")
    if normalized_ext in FORCE_ATTACHMENT_EXTENSIONS:
        return True
    normalized_type = (content_type or "").lower()
    return normalized_type in FORCE_ATTACHMENT_CONTENT_TYPES


def apply_safe_file_response_headers(response, content_type: str | None, ext: str | None = None):
    if content_type:
        response.headers.set("Content-Type", content_type)
    force_attachment = should_force_attachment(ext, content_type)
    if force_attachment:
        response.headers.set("X-Content-Type-Options", "nosniff")
        response.headers.set("Content-Disposition", "attachment")
    return response


def html2pdf(
    source: str,
    timeout: int = 2,
    install_driver: bool = True,
    print_options: dict = {},
):
    result = __get_pdf_from_html(source, timeout, install_driver, print_options)
    return result


def __send_devtools(driver, cmd, params={}):
    resource = "/session/%s/chromium/send_command_and_get_result" % driver.session_id
    url = driver.command_executor._url + resource
    body = json.dumps({"cmd": cmd, "params": params})
    response = driver.command_executor._request("POST", url, body)

    if not response:
        raise Exception(response.get("value"))

    return response.get("value")


def __get_pdf_from_html(path: str, timeout: int, install_driver: bool, print_options: dict):
    webdriver_options = Options()
    webdriver_prefs = {}
    webdriver_options.add_argument("--headless")
    webdriver_options.add_argument("--disable-gpu")
    webdriver_options.add_argument("--no-sandbox")
    webdriver_options.add_argument("--disable-dev-shm-usage")
    webdriver_options.experimental_options["prefs"] = webdriver_prefs

    webdriver_prefs["profile.default_content_settings"] = {"images": 2}

    if install_driver:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=webdriver_options)
    else:
        driver = webdriver.Chrome(options=webdriver_options)

    driver.get(path)

    try:
        WebDriverWait(driver, timeout).until(staleness_of(driver.find_element(by=By.TAG_NAME, value="html")))
    except TimeoutException:
        pass

    try:
        calculated_print_options = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
        }
        calculated_print_options.update(print_options)
        result = __send_devtools(driver, "Page.printToPDF", calculated_print_options)
        return base64.b64decode(result["data"])
    finally:
        driver.quit()


def is_valid_url(url: str) -> bool:
    if not re.match(r"(https?)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]", url):
        return False
    from common.ssrf_guard import assert_url_is_safe

    try:
        assert_url_is_safe(url)
        return True
    except ValueError:
        return False


def safe_json_parse(data: str | dict) -> dict:
    if isinstance(data, dict):
        return data
    try:
        return json.loads(data) if data else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def get_float(req: dict, key: str, default: float | int = 10.0) -> float:
    try:
        parsed = float(req.get(key, default))
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


async def send_email_html(to_email: str, subject: str, template_key: str, **context):
    try:
        tmpl = EMAIL_TEMPLATES.get(template_key)
        if not tmpl:
            logging.error("Email template '%s' not found.", template_key)
            return False

        body = Template(tmpl).render(**context)
        msg = MIMEText(body, "html", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")

        # Base SMTP settings from settings module & env vars
        server = os.environ.get("SMTP_SERVER", getattr(settings, "MAIL_SERVER", ""))
        port_env = os.environ.get("SMTP_PORT", "")
        port = int(port_env) if port_env.isdigit() else (getattr(settings, "MAIL_PORT", 587) or 587)
        username = os.environ.get("SMTP_USERNAME", getattr(settings, "MAIL_USERNAME", ""))
        password = os.environ.get("SMTP_PASSWORD", getattr(settings, "MAIL_PASSWORD", ""))
        use_ssl = os.environ.get("SMTP_USE_SSL", "").lower() in ("1", "true", "yes") if os.environ.get("SMTP_USE_SSL") else getattr(settings, "MAIL_USE_SSL", False)
        use_tls = os.environ.get("SMTP_USE_TLS", "").lower() in ("1", "true", "yes") if os.environ.get("SMTP_USE_TLS") else getattr(settings, "MAIL_USE_TLS", True)
        sender_env = os.environ.get("SMTP_SENDER", "")
        sender_name_env = os.environ.get("SMTP_SENDER_NAME", "Swipies AI")
        sender = (sender_name_env, sender_env) if sender_env else getattr(settings, "MAIL_DEFAULT_SENDER", ("Swipies AI", "noreply@swipies.app"))

        # Try override from SystemSettings DB table if available
        try:
            from api.db.services.system_settings_service import SystemSettingsService
            def get_sys_val(key, default=""):
                objs = SystemSettingsService.get_by_name(key)
                return objs[0].value if objs and objs[0].value else default

            server = get_sys_val("smtp.server", server) or get_sys_val("mail_server", server)
            port_val = get_sys_val("smtp.port", "") or get_sys_val("mail_port", "")
            if port_val:
                try:
                    port = int(port_val)
                except ValueError:
                    pass
            username = get_sys_val("smtp.username", username) or get_sys_val("mail_username", username)
            password = get_sys_val("smtp.password", password) or get_sys_val("mail_password", password)
            sender_val = get_sys_val("smtp.sender", "") or get_sys_val("mail_sender", "")
            if sender_val:
                sender = ("Swipies AI", sender_val)
        except Exception:
            pass

        code_info = context.get("code")
        if code_info:
            logging.info("=== [ACTIVATION OTP CODE FOR %s]: %s ===", to_email, code_info)

        sender_name = sender[0] if isinstance(sender, (tuple, list)) and len(sender) > 0 else "Swipies AI"
        sender_addr = sender[1] if isinstance(sender, (tuple, list)) and len(sender) > 1 else (username or "noreply@swipies.app")

        # Resend API Key: prioritize environment variable RESEND_API_KEY, or password if starting with re_
        resend_key = os.environ.get("RESEND_API_KEY", "").strip()
        active_key = resend_key or (str(password).strip() if (password and str(password).strip().startswith("re_")) else "")

        # High-performance Resend HTTP API Dispatcher (Executes if valid Resend Key is available)
        if active_key:
            resend_api_url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {active_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "from": f"{sender_name} <{sender_addr if '@' in sender_addr else 'noreply@swipies.app'}>",
                "to": [to_email],
                "subject": subject,
                "html": body,
            }
            try:
                import requests
                resp = requests.post(resend_api_url, json=payload, headers=headers, timeout=10)
                logging.info("Resend API response [%s]: %s", resp.status_code, resp.text)
                if resp.status_code in (200, 201):
                    logging.info("Email successfully dispatched to %s via Resend API", to_email)
                    return True
                elif resp.status_code in (400, 401, 403) and "invalid" in resp.text.lower():
                    logging.error("Resend API Key is invalid: %s. Falling back to SMTP...", resp.text)
                else:
                    logging.warning("Resend API primary sender notice: %s. Trying onboarding fallback...", resp.text)
                    payload["from"] = f"{sender_name} <onboarding@resend.dev>"
                    resp_fb = requests.post(resend_api_url, json=payload, headers=headers, timeout=10)
                    logging.info("Resend API fallback response [%s]: %s", resp_fb.status_code, resp_fb.text)
                    if resp_fb.status_code in (200, 201):
                        logging.info("Email successfully dispatched to %s via Resend API (onboarding fallback)", to_email)
                        return True
                    else:
                        logging.error("Resend API fallback notice: %s", resp_fb.text)
            except Exception as resend_err:
                logging.error("Resend API request exception: %s", resend_err)

        # If SMTP server is not set or empty, skip SMTP attempt
        if not server:
            logging.warning("No SMTP server configured. Email to %s could not be sent.", to_email)
            return False

        msg["From"] = f"{sender_name} <{sender_addr}>"
        msg["To"] = to_email

        is_ssl = (port == 465) or (use_ssl and not use_tls)

        smtp = aiosmtplib.SMTP(
            hostname=server,
            port=port,
            use_tls=is_ssl,
            timeout=5,
        )

        await smtp.connect()
        if not is_ssl and (use_tls or port == 587):
            try:
                await smtp.starttls()
            except Exception as tls_err:
                logging.warning("SMTP STARTTLS notice: %s", tls_err)

        if username and password:
            await smtp.login(username, password)

        await smtp.send_message(msg)
        await smtp.quit()
        logging.info("Email successfully dispatched to %s", to_email)
        return True
    except Exception as err:
        logging.error("Failed to send email to %s: %s", to_email, err)
        return False


async def send_invite_email(to_email, invite_url, tenant_id, inviter):
    # Reuse the generic HTML sender with 'invite' template
    await send_email_html(
        to_email=to_email,
        subject="RAGFlow Invitation",
        template_key="invite",
        email=to_email,
        invite_url=invite_url,
        tenant_id=tenant_id,
        inviter=inviter,
    )


def otp_keys(email: str):
    email = (email or "").strip().lower()
    return (
        f"otp:{email}",
        f"otp_attempts:{email}",
        f"otp_last_sent:{email}",
        f"otp_lock:{email}",
    )


def activation_keys(email: str):
    email = (email or "").strip().lower()
    return (
        f"act_code:{email}",
        f"act_attempts:{email}",
        f"act_last_sent:{email}",
        f"act_lock:{email}",
    )


def hash_code(code: str, salt: bytes) -> str:
    import hashlib
    import hmac

    return hmac.new(salt, (code or "").encode("utf-8"), hashlib.sha256).hexdigest()


def captcha_key(email: str) -> str:
    return f"captcha:{email}"


def dispatch_email_bg(to_email: str, subject: str, template_key: str, **context):
    """Dispatch email in a daemon thread so it runs reliably in WSGI/Flask context."""
    def _worker():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                send_email_html(to_email, subject, template_key, **context)
            )
            loop.close()
        except Exception as err:
            logging.error("Failed to deliver background email to %s: %s", to_email, err)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

