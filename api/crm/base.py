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
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CRMProviderBase(ABC):
    """Abstract interface for all CRM and ERP system adapters."""

    @staticmethod
    def is_management_enabled(connection_config: Dict[str, Any]) -> bool:
        """Check if management/write actions are enabled for this provider configuration."""
        if not connection_config or not isinstance(connection_config, dict):
            return True
        for key in ("management_enabled", "enable_management", "allow_write", "allow_crm_actions"):
            if key in connection_config:
                return bool(connection_config[key])
        return True

    @classmethod
    def check_management_allowed(cls, connection_config: Dict[str, Any], action_name: str = "write") -> None:
        """Enforce that CRM management is enabled before executing any write/mutate action."""
        if not cls.is_management_enabled(connection_config):
            raise PermissionError(
                f"CRM management is disabled for this provider. "
                f"Action '{action_name}' is blocked. Data extraction and reading remain active."
            )

    @abstractmethod
    def create_lead(self, connection_config: Dict[str, Any], lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create lead/deal in external CRM system.
        
        Args:
            connection_config: Decrypted connection configuration dictionary.
            lead_data: Lead payload containing name, phone, query, context, etc.
            
        Returns:
            Dict containing external CRM reference ID and details.
        """
        pass

    @abstractmethod
    def find_contact(self, connection_config: Dict[str, Any], phone: str) -> Optional[Dict[str, Any]]:
        """Look up existing contact by normalized E.164 phone.
        
        Args:
            connection_config: Decrypted connection configuration dictionary.
            phone: Normalized E.164 phone string.
            
        Returns:
            Dict containing contact details or None if not found.
        """
        pass

    @abstractmethod
    def refresh_auth(self, connection_config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform token refresh or validate credentials.
        
        Args:
            connection_config: Decrypted connection configuration dictionary.
            
        Returns:
            Updated connection configuration dictionary with fresh tokens.
        """
        pass

    @abstractmethod
    def check_stock(self, connection_config: Dict[str, Any], item_query: str) -> Dict[str, Any]:
        """Query inventory / stock balance (e.g. 1C OData).
        
        Args:
            connection_config: Decrypted connection configuration dictionary.
            item_query: SKU, article code, or item name query.
            
        Returns:
            Dict containing available stock details.
        """
        pass

    @abstractmethod
    def query_records(
        self,
        connection_config: Dict[str, Any],
        entity: str,
        query: str = "",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query existing CRM records (deals, leads, contacts, companies, products, orders).
        
        Args:
            connection_config: Decrypted connection configuration dictionary.
            entity: Entity type ('deal', 'lead', 'contact', 'company', 'product', 'order').
            query: Search string (e.g. phone, email, name, ID).
            filters: Optional dictionary of filter criteria.
            limit: Maximum number of records to return.
            
        Returns:
            List of dictionaries representing matched records.
        """
        pass


class CRMProviderRegistry:
    """Registry and factory for CRM/ERP provider adapters."""
    _providers: Dict[str, CRMProviderBase] = {}

    @classmethod
    def register(cls, crm_type: str, provider: CRMProviderBase) -> None:
        """Register a CRM provider instance for a specific crm_type."""
        cls._providers[crm_type] = provider

    @classmethod
    def get(cls, crm_type: str) -> CRMProviderBase:
        """Retrieve a provider instance, lazily creating defaults if unregistered."""
        if crm_type in cls._providers:
            return cls._providers[crm_type]

        if crm_type in ("amocrm", "kommo"):
            from api.crm.clients.amocrm import AmoCRMClient
            provider = AmoCRMClient()
            cls._providers[crm_type] = provider
            return provider
        elif crm_type in ("bitrix24", "bitrix24_onprem"):
            from api.crm.clients.bitrix24 import Bitrix24Client
            provider = Bitrix24Client()
            cls._providers[crm_type] = provider
            return provider
        elif crm_type in ("1c", "1c_odata"):
            from api.crm.clients.one_c import OneCClient
            provider = OneCClient()
            cls._providers[crm_type] = provider
            return provider
        elif crm_type == "hubspot":
            from api.crm.clients.hubspot import HubSpotClient
            provider = HubSpotClient()
            cls._providers[crm_type] = provider
            return provider

        raise ValueError(f"Unsupported or unregistered CRM provider type: '{crm_type}'")

    @classmethod
    def clear(cls) -> None:
        """Clear registered providers (for test cleanup)."""
        cls._providers.clear()

