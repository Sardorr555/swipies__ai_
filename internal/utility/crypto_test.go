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

package utility

import (
	"errors"
	"os"
	"strings"
	"testing"
)

func TestCrypto_EncryptDecryptAES256GCM_HKDF(t *testing.T) {
	secret := "test-secret-key-for-aes-256-gcm!"
	plain := "super-sensitive-api-token-value-999"

	enc, err := EncryptAPIKey(plain, secret)
	if err != nil {
		t.Fatalf("EncryptAPIKey failed: %v", err)
	}
	if !strings.HasPrefix(enc, "enc:v2:") {
		t.Fatalf("Expected enc:v2: prefix, got: %s", enc)
	}

	dec, err := DecryptAPIKey(enc, secret)
	if err != nil {
		t.Fatalf("DecryptAPIKey failed: %v", err)
	}
	if dec != plain {
		t.Fatalf("Expected '%s', got '%s'", plain, dec)
	}
}

func TestCrypto_FailClosedOnInsecureSecretKey(t *testing.T) {
	plain := "should-not-encrypt-under-bad-key"

	// 1. Empty secret
	_, err := EncryptAPIKey(plain, "")
	if !errors.Is(err, ErrInsecureSecretKey) {
		t.Fatalf("Expected ErrInsecureSecretKey for empty key, got: %v", err)
	}

	// 2. Secret too short (<32 bytes)
	_, err = EncryptAPIKey(plain, "short-key-16-bytes")
	if !errors.Is(err, ErrInsecureSecretKey) {
		t.Fatalf("Expected ErrInsecureSecretKey for short key, got: %v", err)
	}

	// 3. Known insecure default key
	_, err = EncryptAPIKey(plain, "ragflow_single_global_instance_master_secret_2026")
	if !errors.Is(err, ErrInsecureSecretKey) {
		t.Fatalf("Expected ErrInsecureSecretKey for default key, got: %v", err)
	}
}

func TestCrypto_PythonCrossLanguageCompatibility(t *testing.T) {
	secret := "test-master-secret-key-32bytes-ok!"
	expectedPlain := "cross-lang-test-secret-value-12345"

	// 1. Python enc:v2: (AES-256-GCM via HKDF) decrypted by Go
	pythonV2 := "enc:v2:yqE1XB6mL4jEC7fDc+utp8iy4YFn6dtO2jHQVNvvhtPn2oceDAkD5S8mu6QeISVb0nDZB7n+i5V3+8AL+l4="
	decV2, err := DecryptAPIKey(pythonV2, secret)
	if err != nil {
		t.Fatalf("Go failed to decrypt Python v2 HKDF vector: %v", err)
	}
	if decV2 != expectedPlain {
		t.Fatalf("Python v2 HKDF vector mismatch: expected '%s', got '%s'", expectedPlain, decV2)
	}

	// 2. Python enc:v1: (HMAC-SHA256 CTR) decrypted by Go
	pythonV1 := "enc:v1:MDEyMzQ1Njc4OWFiY2RlZi2J+E1szJ+OKGOCVomikPPcq0j8d0Yjn7GmJSVm2UwuvGA+XSQUssnHfH0HcjdVGcLw"
	decV1, err := DecryptAPIKey(pythonV1, secret)
	if err != nil {
		t.Fatalf("Go failed to decrypt Python v1 vector: %v", err)
	}
	if decV1 != expectedPlain {
		t.Fatalf("Python v1 vector mismatch: expected '%s', got '%s'", expectedPlain, decV1)
	}

	// 3. Go encrypts, verify Go can decrypt, and prefix is enc:v2:
	goEnc, err := EncryptAPIKey(expectedPlain, secret)
	if err != nil {
		t.Fatalf("Go EncryptAPIKey failed: %v", err)
	}
	t.Logf("GO_ENCRYPTED_HKDF_VECTOR=%s", goEnc)
	if !strings.HasPrefix(goEnc, "enc:v2:") {
		t.Fatalf("Go ciphertext should start with enc:v2:, got: %s", goEnc)
	}
	goDec, err := DecryptAPIKey(goEnc, secret)
	if err != nil || goDec != expectedPlain {
		t.Fatalf("Go roundtrip decryption failed: %v, got %s", err, goDec)
	}
}

func TestCrypto_KeyRotationKeyring(t *testing.T) {
	oldKey := "old-master-secret-key-rotated-2025"
	newKey := "new-master-secret-key-current-2026"
	secretVal := "pre-rotation-confidential-secret"

	// Encrypted under old key
	encOld, err := EncryptAPIKey(secretVal, oldKey)
	if err != nil {
		t.Fatalf("EncryptAPIKey failed: %v", err)
	}

	// Configure environment with new key as primary and old key in rotation list
	os.Setenv("RAGFLOW_SECRET_KEY", newKey)
	os.Setenv("RAGFLOW_SECRET_KEYS_ROTATION", "another-key-1,"+oldKey+",yet-another-key-2")
	defer func() {
		os.Unsetenv("RAGFLOW_SECRET_KEY")
		os.Unsetenv("RAGFLOW_SECRET_KEYS_ROTATION")
	}()

	// DecryptAPIKey with empty secret string uses env keyring
	decVal, err := DecryptAPIKey(encOld, "")
	if err != nil {
		t.Fatalf("DecryptAPIKey with rotation keyring failed: %v", err)
	}
	if decVal != secretVal {
		t.Fatalf("Expected '%s', got '%s'", secretVal, decVal)
	}
}

func TestCrypto_URLCredentialsAndRestAPIHeadersMasking(t *testing.T) {
	secret := "test-master-secret-key-32bytes-ok!"
	os.Setenv("RAGFLOW_SECRET_KEY", secret)
	defer os.Unsetenv("RAGFLOW_SECRET_KEY")

	cfg := map[string]any{
		"rss_url":     "https://feed.example.com/rss?token=secret_query_token_123&category=news",
		"sitemap_url": "https://admin:my_secret_http_pass@sitemap.example.com/sitemap.xml",
		"credentials": map[string]any{
			"instance_url": "https://service-user:p@ssword999@jira.corp.local",
			"client_id":    "public-client-id-123",
		},
		"auth_config": map[string]any{
			"api_key":   "raw-auth-config-api-key-888",
			"auth_mode": "bearer",
		},
		"headers": map[string]any{
			"Authorization": "Bearer super-secret-jwt-token-777",
			"X-Custom-Auth": "secret-custom-header-value",
		},
	}

	// 1. Verify masking
	masked := MaskConnectorConfig(cfg)

	// RSS query token must be masked
	rssMasked := masked["rss_url"].(string)
	if strings.Contains(rssMasked, "secret_query_token_123") || !strings.Contains(rssMasked, "token=********") {
		t.Errorf("RSS URL token leaked! Got: %s", rssMasked)
	}

	// Sitemap userinfo password must be masked
	sitemapMasked := masked["sitemap_url"].(string)
	if strings.Contains(sitemapMasked, "my_secret_http_pass") || !strings.Contains(sitemapMasked, "admin:********@") {
		t.Errorf("Sitemap URL password leaked! Got: %s", sitemapMasked)
	}

	// Instance URL userinfo password must be masked
	credsMasked := masked["credentials"].(map[string]any)
	instanceURLMasked := credsMasked["instance_url"].(string)
	if strings.Contains(instanceURLMasked, "p@ssword999") || !strings.Contains(instanceURLMasked, "service-user:********@") {
		t.Errorf("instance_url password leaked! Got: %s", instanceURLMasked)
	}

	// auth_config fields must be masked (deny-by-default)
	authCfgMasked := masked["auth_config"].(map[string]any)
	if authCfgMasked["api_key"] != "********" {
		t.Errorf("auth_config.api_key should be masked, got: %v", authCfgMasked["api_key"])
	}

	// headers fields must be masked (deny-by-default)
	headersMasked := masked["headers"].(map[string]any)
	if headersMasked["Authorization"] != "********" {
		t.Errorf("headers.Authorization should be masked, got: %v", headersMasked["Authorization"])
	}
	if headersMasked["X-Custom-Auth"] != "********" {
		t.Errorf("headers.X-Custom-Auth should be masked, got: %v", headersMasked["X-Custom-Auth"])
	}

	// 2. Verify encryption at rest: URLs with credentials, auth_config, and headers are encrypted
	encrypted := EncryptConnectorConfig(cfg)
	rssEnc := encrypted["rss_url"].(string)
	if !strings.HasPrefix(rssEnc, "enc:v2:") {
		t.Errorf("URL with embedded credentials was not encrypted at rest! Got: %s", rssEnc)
	}
	authCfgEnc := encrypted["auth_config"].(map[string]any)
	if !strings.HasPrefix(authCfgEnc["api_key"].(string), "enc:v2:") {
		t.Errorf("auth_config.api_key was not encrypted at rest!")
	}
	headersEnc := encrypted["headers"].(map[string]any)
	if !strings.HasPrefix(headersEnc["Authorization"].(string), "enc:v2:") {
		t.Errorf("headers.Authorization was not encrypted at rest!")
	}

	// Decrypting recovers original values
	decrypted := DecryptConnectorConfig(encrypted)
	if decrypted["rss_url"] != cfg["rss_url"] {
		t.Errorf("Decrypted rss_url mismatch: expected %v, got %v", cfg["rss_url"], decrypted["rss_url"])
	}
	if decrypted["auth_config"].(map[string]any)["api_key"] != "raw-auth-config-api-key-888" {
		t.Errorf("Decrypted auth_config mismatch")
	}
}

func TestCrypto_MergeUpdatedConnectorConfig(t *testing.T) {
	secret := "test-merge-master-key-32bytes-ok!"
	os.Setenv("RAGFLOW_SECRET_KEY", secret)
	defer os.Unsetenv("RAGFLOW_SECRET_KEY")

	existing := map[string]any{
		"credentials": map[string]any{
			"url":           "https://test.com",
			"client_secret": "my-existing-secret",
		},
	}
	encryptedExisting := EncryptConnectorConfig(existing)
	existingEncSecret := encryptedExisting["credentials"].(map[string]any)["client_secret"].(string)
	if !strings.HasPrefix(existingEncSecret, "enc:v2:") {
		t.Fatalf("Existing secret should be encrypted with enc:v2:")
	}

	// Incoming update with masked client_secret ("********") and changed url
	incoming := map[string]any{
		"credentials": map[string]any{
			"url":           "https://updated.com",
			"client_secret": "********",
		},
	}

	merged := MergeUpdatedConnectorConfig(encryptedExisting, incoming)
	mergedCreds := merged["credentials"].(map[string]any)

	if mergedCreds["url"] != "https://updated.com" {
		t.Errorf("url should be updated")
	}
	if mergedCreds["client_secret"] != existingEncSecret {
		t.Errorf("client_secret should retain existing encrypted value, got: %v", mergedCreds["client_secret"])
	}
}

func TestCrypto_URLRoundTripMaskedURL(t *testing.T) {
	secret := "test-url-roundtrip-key-32bytes-ok!"
	os.Setenv("RAGFLOW_SECRET_KEY", secret)
	defer os.Unsetenv("RAGFLOW_SECRET_KEY")

	originalURL := "https://service-user:p@ssw0rd!Really$ecret@jira.corp.local/api?token=s3cr3t-tok3n"
	rawConfig := map[string]any{
		"credentials": map[string]any{
			"instance_url": originalURL,
			"client_id":    "public-client-id",
		},
	}
	storedEnc := EncryptConnectorConfig(rawConfig)

	// Mask as returned to UI
	masked := MaskConnectorConfig(storedEnc)
	maskedCreds := masked["credentials"].(map[string]any)
	maskedURL := maskedCreds["instance_url"].(string)

	if strings.Contains(maskedURL, "p@ssw0rd!Really$ecret") {
		t.Errorf("password leaked in masked URL: %s", maskedURL)
	}
	if strings.Contains(maskedURL, "s3cr3t-tok3n") {
		t.Errorf("token leaked in masked URL: %s", maskedURL)
	}
	if !strings.Contains(maskedURL, "********") {
		t.Errorf("masked URL should contain ********, got: %s", maskedURL)
	}

	// UI sends back masked URL in update payload
	patchPayload := map[string]any{
		"credentials": map[string]any{
			"instance_url": maskedURL,
			"client_id":    "public-client-id",
		},
	}

	merged := MergeUpdatedConnectorConfig(storedEnc, patchPayload)
	mergedCreds := merged["credentials"].(map[string]any)
	mergedURLVal := mergedCreds["instance_url"].(string)

	if !strings.HasPrefix(mergedURLVal, "enc:v2:") {
		t.Fatalf("expected enc:v2: prefix after merge, got: %s", mergedURLVal)
	}

	decrypted := DecryptConnectorConfig(merged)
	recoveredURL := decrypted["credentials"].(map[string]any)["instance_url"].(string)

	if recoveredURL != originalURL {
		t.Fatalf("URL round-trip FAILED:\n  expected: %s\n  recovered: %s", originalURL, recoveredURL)
	}
}

