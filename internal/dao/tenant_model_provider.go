//
//  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
//

package dao

import (
	"context"
	"os"
	"strings"
	"sync"
	"ragflow/internal/entity"

	"gorm.io/gorm"
)

var (
	adminUserIDCache     string
	adminUserIDCacheOnce sync.Once
)

func getAdminUserID() string {
	adminUserIDCacheOnce.Do(func() {
		var adminUser entity.User
		adminEmail := os.Getenv("DEFAULT_SUPERUSER_EMAIL")
		if adminEmail == "" {
			adminEmail = "admin@ragflow.io"
		}
		errAdmin := DB.Where("LOWER(email) = ?", strings.ToLower(adminEmail)).First(&adminUser).Error
		if errAdmin != nil {
			errAdmin = DB.Where("is_superuser = ?", true).First(&adminUser).Error
		}
		if errAdmin == nil {
			adminUserIDCache = adminUser.ID
		}
	})
	return adminUserIDCache
}

func isProOrEnterprise(tenantID string) bool {
	if tenantID == "" {
		return false
	}
	adminID := getAdminUserID()
	if adminID != "" && tenantID == adminID {
		return true
	}
	var user entity.User
	if err := DB.Where("id = ?", tenantID).First(&user).Error; err == nil {
		if user.IsSuperuser {
			return true
		}
	}
	var tenant entity.Tenant
	if err := DB.Where("id = ?", tenantID).First(&tenant).Error; err == nil {
		planType := strings.ToLower(tenant.PlanType)
		if planType == "pro" || planType == "enterprise" {
			return true
		}
	}
	return false
}

// TenantModelProviderDAO tenant model provider data access object
type TenantModelProviderDAO struct{}

// NewTenantModelProviderDAO create tenant model provider DAO
func NewTenantModelProviderDAO() *TenantModelProviderDAO {
	return &TenantModelProviderDAO{}
}

func (dao *TenantModelProviderDAO) Create(ctx context.Context, db *gorm.DB, provider *entity.TenantModelProvider) error {
	return db.WithContext(ctx).Create(provider).Error
}

// GetByID get tenant model provider by primary key (id)
func (dao *TenantModelProviderDAO) GetByID(ctx context.Context, db *gorm.DB, id string) (*entity.TenantModelProvider, error) {
	var provider entity.TenantModelProvider
	err := db.WithContext(ctx).Where("id = ?", id).First(&provider).Error
	if err != nil {
		return nil, err
	}
	return &provider, nil
}

// GetByTenantIDAndProviderName get the providers by tenant ID and provider name with platform instance routing
func (dao *TenantModelProviderDAO) GetByTenantIDAndProviderName(ctx context.Context, db *gorm.DB, tenantID, providerName string) (*entity.TenantModelProvider, error) {
	if isProOrEnterprise(tenantID) {
		var customProvider entity.TenantModelProvider
		if err := db.WithContext(ctx).Where("tenant_id = ? AND provider_name = ?", tenantID, providerName).First(&customProvider).Error; err == nil {
			return &customProvider, nil
		}
	}

	adminID := getAdminUserID()
	if adminID != "" && adminID != tenantID {
		var platformProvider entity.TenantModelProvider
		if errP := db.WithContext(ctx).Where("tenant_id = ? AND provider_name = ?", adminID, providerName).First(&platformProvider).Error; errP == nil {
			return &platformProvider, nil
		}
	}

	var provider entity.TenantModelProvider
	err := db.WithContext(ctx).Where("tenant_id = ? AND provider_name = ?", tenantID, providerName).First(&provider).Error
	if err == nil {
		return &provider, nil
	}
	return nil, err
}

// DeleteByTenantID deletes all model providers by tenant ID (hard delete)
func (dao *TenantModelProviderDAO) DeleteByTenantID(ctx context.Context, db *gorm.DB, tenantID string) (int64, error) {
	result := db.WithContext(ctx).Unscoped().Where("tenant_id = ?", tenantID).Delete(&entity.TenantModelProvider{})
	return result.RowsAffected, result.Error
}

// DeleteByTenantIDAndProviderName DeleteByTenantID deletes all providers by tenant ID (hard delete)
func (dao *TenantModelProviderDAO) DeleteByTenantIDAndProviderName(ctx context.Context, db *gorm.DB, tenantID, providerName string) (int64, error) {
	result := db.WithContext(ctx).Unscoped().Where("tenant_id = ? AND provider_name = ?", tenantID, providerName).Delete(&entity.TenantModelProvider{})
	return result.RowsAffected, result.Error
}

// ListByID list tenant model providers by ID with platform fallback
func (dao *TenantModelProviderDAO) ListByID(ctx context.Context, db *gorm.DB, id string) ([]string, error) {
	var providerNames []string
	err := db.WithContext(ctx).Model(&entity.TenantModelProvider{}).
		Where("tenant_id = ?", id).
		Pluck("provider_name", &providerNames).Error
	if err != nil {
		return nil, err
	}

	adminID := getAdminUserID()
	if adminID != "" && adminID != id {
		var adminProviderNames []string
		if errP := db.WithContext(ctx).Model(&entity.TenantModelProvider{}).
			Where("tenant_id = ?", adminID).
			Pluck("provider_name", &adminProviderNames).Error; errP == nil {
			existing := make(map[string]bool)
			for _, name := range providerNames {
				existing[name] = true
			}
			for _, name := range adminProviderNames {
				if !existing[name] {
					providerNames = append(providerNames, name)
				}
			}
		}
	}

	return providerNames, nil
}

// GetByTenantID returns all TenantModelProvider rows for a tenant with platform fallback.
func (dao *TenantModelProviderDAO) GetByTenantID(ctx context.Context, db *gorm.DB, tenantID string) ([]*entity.TenantModelProvider, error) {
	var providers []*entity.TenantModelProvider
	err := db.WithContext(ctx).Where("tenant_id = ?", tenantID).Find(&providers).Error
	if err != nil {
		return nil, err
	}

	adminID := getAdminUserID()
	if adminID != "" && adminID != tenantID {
		existingNames := make(map[string]bool)
		for _, p := range providers {
			existingNames[p.ProviderName] = true
		}
		var adminProviders []*entity.TenantModelProvider
		if errP := db.WithContext(ctx).Where("tenant_id = ?", adminID).Find(&adminProviders).Error; errP == nil {
			for _, ap := range adminProviders {
				if !existingNames[ap.ProviderName] {
					providers = append(providers, ap)
				}
			}
		}
	}

	return providers, nil
}
