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

from common.http_client import async_request, sync_request
from .oauth import OAuthClient, UserInfo


class GoogleOAuthClient(OAuthClient):
    def __init__(self, config):
        """
        Initialize the GoogleOAuthClient with default endpoints if omitted.
        """
        defaults = {
            "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
            "scope": "openid email profile"
        }
        for k, v in defaults.items():
            if not config.get(k):
                config[k] = v
        super().__init__(config)

    def fetch_user_info(self, access_token, id_token=None, **kwargs):
        """Fetch Google user info (synchronous)."""
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = sync_request("GET", self.userinfo_url, headers=headers, timeout=self.http_request_timeout)
            response.raise_for_status()
            return self.normalize_user_info(response.json())
        except Exception as e:
            raise ValueError(f"Failed to fetch google user info: {e}")

    async def async_fetch_user_info(self, access_token, id_token=None, **kwargs):
        """Fetch Google user info (asynchronous)."""
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = await async_request("GET", self.userinfo_url, headers=headers, timeout=self.http_request_timeout)
            response.raise_for_status()
            return self.normalize_user_info(response.json())
        except Exception as e:
            raise ValueError(f"Failed to fetch google user info: {e}")

    def normalize_user_info(self, user_info):
        email = user_info.get("email")
        username = user_info.get("email", "").split("@")[0] or user_info.get("sub", "")
        nickname = user_info.get("name", user_info.get("given_name", username))
        avatar_url = user_info.get("picture", "")
        return UserInfo(email=email, username=username, nickname=nickname, avatar_url=avatar_url)
