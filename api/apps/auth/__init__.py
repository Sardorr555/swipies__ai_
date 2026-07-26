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

from .oauth import OAuthClient
from .oidc import OIDCClient
from .github import GithubOAuthClient
from .google import GoogleOAuthClient


CLIENT_TYPES = {
    "oauth2": OAuthClient,
    "oidc": OIDCClient,
    "github": GithubOAuthClient,
    "google": GoogleOAuthClient,
}


def get_auth_client(config) -> OAuthClient:
    channel_type = str(config.get("type", "")).lower()
    channel_name = str(config.get("channel", "")).lower()
    if channel_type == "":
        if "google" in channel_name:
            channel_type = "google"
        elif "github" in channel_name:
            channel_type = "github"
        elif config.get("issuer"):
            channel_type = "oidc"
        else:
            channel_type = "oauth2"
    client_class = CLIENT_TYPES.get(channel_type)
    if not client_class:
        if "google" in channel_name or "google" in channel_type:
            client_class = GoogleOAuthClient
        elif "github" in channel_name or "github" in channel_type:
            client_class = GithubOAuthClient
        else:
            client_class = OAuthClient

    return client_class(config)
