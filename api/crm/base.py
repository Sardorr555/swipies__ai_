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
from typing import Any, Dict, Optional


class CRMProviderBase(ABC):
    """Abstract interface for all CRM and ERP system adapters."""

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
