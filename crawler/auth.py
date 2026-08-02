import aiohttp

class AuthHandler:
    def __init__(self, auth_config: dict = None):
        self.auth_config = auth_config or {}

    def get_headers(self) -> dict:
        headers = {}
        auth_type = self.auth_config.get("type", "none")

        if auth_type == "bearer" and self.auth_config.get("token"):
            headers["Authorization"] = f"Bearer {self.auth_config['token']}"
        elif auth_type == "custom_header" and self.auth_config.get("headers"):
            headers.update(self.auth_config["headers"])

        return headers

    def get_auth(self):
        auth_type = self.auth_config.get("type", "none")
        if auth_type == "basic" and self.auth_config.get("username") and self.auth_config.get("password"):
            return aiohttp.BasicAuth(self.auth_config["username"], self.auth_config["password"])
        return None

    def get_cookies(self) -> dict:
        if self.auth_config.get("type") == "cookie" and isinstance(self.auth_config.get("cookies"), dict):
            return self.auth_config["cookies"]
        return {}

    async def login_with_playwright(self, page, login_url: str, username_selector: str, password_selector: str, submit_selector: str, username_val: str, password_val: str):
        await page.goto(login_url)
        await page.fill(username_selector, username_val)
        await page.fill(password_selector, password_val)
        await page.click(submit_selector)
        await page.wait_for_load_state("networkidle")
