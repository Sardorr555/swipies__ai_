#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
import os

# Swipies Ads & Platform Branding settings
ADS_ENABLED = True
ADS_FOR_FREE_USERS = True
ADS_PLATFORM_BRANDING_ENABLED = True
ADS_LLM_PROMPT_ENABLED = True
ADS_TARGETING_ENABLED = True
ADS_BILLING_ENABLED = True
ADS_ANALYTICS_ENABLED = True
SWIPIES_APP_URL = os.getenv("SWIPIES_APP_URL", "https://swipies.app")
SWIPIES_BRAND_NAME = os.getenv("SWIPIES_BRAND_NAME", "Swipies AI")

# Atmos Payment Gateway settings (Uzcard / Humo / Visa / Mastercard)
ATMOS_KEY = os.getenv("ATMOS_KEY", "TpLRLagJ1SXiZ0dT_om5BT_I3Nga")
ATMOS_SECRET = os.getenv("ATMOS_SECRET", "bMH7gjat2EgI3fTXoLJX7CRUcbAa")
ATMOS_STORE_ID = os.getenv("ATMOS_STORE_ID", "100506")
ATMOS_BASE_URL = os.getenv("ATMOS_BASE_URL", "https://apigw.atmos.uz")
ATMOS_MOCK_MODE = os.getenv("ATMOS_MOCK_MODE", "false").lower() in ["true", "1", "yes"]
USD_TO_UZS_RATE = float(os.getenv("USD_TO_UZS_RATE", "12800.0"))
