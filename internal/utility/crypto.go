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
	"crypto/aes"
	"crypto/cipher"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/binary"
	"errors"
	"io"
	"log"
	"net/url"
	"os"
	"regexp"
	"strings"

	"golang.org/x/crypto/hkdf"

	"ragflow/internal/entity"
)

var (
	// ErrInsecureSecretKey is returned when encryption is attempted with a missing, short, or default secret.
	ErrInsecureSecretKey = errors.New("CRITICAL: RAGFLOW_SECRET_KEY is missing, too short (<32 bytes), or matches an insecure default. Fail-closed: Encryption rejected.")
)

var insecureDefaultSecrets = map[string]bool{
	"ragflow_single_global_instance_master_secret_2026": true,
	"ragflow":             true,
	"infiniflow":          true,
	"default_secret_key":  true,
}

var (
	hkdfSalt = []byte("ragflow_connector_credentials_v2_salt")
	hkdfInfo = []byte("ragflow:connector:aes256-gcm:v2")
)

var sensitiveKeyPatterns = []string{
	"api_key", "secret_key", "password", "token", "access_token",
	"private_key", "key", "secret", "client_secret", "credential", "auth",
}

var denyByDefaultSections = map[string]bool{
	"credentials": true,
	"auth_config": true,
	"headers":     true,
}

// Strict allow-list of public/non-sensitive fields inside config.credentials.
var publicIdentifierFields = map[string]bool{
	"instance_url": true, "url": true, "site_url": true, "container_url": true,
	"base_url": true, "wiki_base": true, "client_id": true, "account_id": true,
	"account_name": true, "username": true, "email": true, "jira_user_email": true,
	"jira_username": true, "zendesk_email": true, "zendesk_subdomain": true,
	"container_name": true, "namespace": true, "region": true, "tenant_id": true,
	"authentication_method": true, "auth_mode": true, "auth_type": true,
	"is_cloud": true, "sync_deleted_files": true, "version": true, "api_version": true,
	"batch_size": true, "objects": true, "folder_path": true, "folder": true,
	"user_ids": true, "method": true, "http_method": true, "items_path": true,
	"id_field": true, "content_fields": true, "metadata_fields": true,
	"pagination_type": true, "max_pages": true, "request_delay": true, "poll_timestamp_field": true,
}

var (
	userinfoRegexp  = regexp.MustCompile(`://([^/@]+:[^/@]+)@`)
	queryParamsRegexp = regexp.MustCompile(`(?i)[?&](token|api_key|secret|password|key|auth|sig)=([^&]+)`)
)

func validateMasterSecret(sec string) (string, error) {
	s := strings.TrimSpace(sec)
	if len(s) < 32 {
		return "", ErrInsecureSecretKey
	}
	if insecureDefaultSecrets[strings.ToLower(s)] {
		return "", ErrInsecureSecretKey
	}
	return s, nil
}

func getMasterSecret() string {
	if sec := os.Getenv("RAGFLOW_SECRET_KEY"); len(strings.TrimSpace(sec)) >= 32 && !insecureDefaultSecrets[strings.ToLower(strings.TrimSpace(sec))] {
		return strings.TrimSpace(sec)
	}
	if sec := os.Getenv("SECRET_KEY"); len(strings.TrimSpace(sec)) >= 32 && !insecureDefaultSecrets[strings.ToLower(strings.TrimSpace(sec))] {
		return strings.TrimSpace(sec)
	}
	return ""
}

func getKeyCandidates(secret string) []string {
	if secret != "" {
		return []string{secret}
	}
	primary := getMasterSecret()
	var candidates []string
	if primary != "" {
		candidates = append(candidates, primary)
	}
	rot := os.Getenv("RAGFLOW_SECRET_KEYS_ROTATION")
	if rot != "" {
		for _, k := range strings.Split(rot, ",") {
			kClean := strings.TrimSpace(k)
			if kClean != "" && kClean != primary {
				candidates = append(candidates, kClean)
			}
		}
	}
	return candidates
}

func deriveAES256KeyHKDF(secret string) ([]byte, error) {
	hkdfReader := hkdf.New(sha256.New, []byte(secret), hkdfSalt, hkdfInfo)
	key := make([]byte, 32)
	if _, err := io.ReadFull(hkdfReader, key); err != nil {
		return nil, err
	}
	return key, nil
}

func deriveLegacyV1Keys(secret string) ([]byte, []byte) {
	encHash := sha256.Sum256([]byte(secret + ":enc"))
	macHash := sha256.Sum256([]byte(secret + ":mac"))
	return encHash[:], macHash[:]
}

func legacyV1Keystream(key, iv []byte, length int) []byte {
	stream := make([]byte, 0, length)
	var counter uint32 = 0
	counterBuf := make([]byte, 4)

	for len(stream) < length {
		binary.BigEndian.PutUint32(counterBuf, counter)
		h := sha256.New()
		h.Write(key)
		h.Write(iv)
		h.Write(counterBuf)
		block := h.Sum(nil)
		stream = append(stream, block...)
		counter++
	}
	return stream[:length]
}

// HasEmbeddedURLCredentials checks if a URL has user:pass@ or sensitive query params.
func HasEmbeddedURLCredentials(rawURL string) bool {
	if !strings.Contains(rawURL, "://") {
		return false
	}
	if userinfoRegexp.MatchString(rawURL) {
		return true
	}
	if strings.Contains(rawURL, "?") {
		if queryParamsRegexp.MatchString(rawURL) {
			return true
		}
	}
	return false
}

// SanitizeURLCredentials masks userinfo password and sensitive query parameters in a URL string.
func SanitizeURLCredentials(rawURL string) string {
	if !strings.Contains(rawURL, "://") {
		return rawURL
	}
	u, err := url.Parse(rawURL)
	if err != nil {
		// Fallback regex replacement
		masked := userinfoRegexp.ReplaceAllString(rawURL, "://$1:********@")
		masked = queryParamsRegexp.ReplaceAllString(masked, "$1=********")
		return masked
	}

	if u.User != nil {
		if _, hasPassword := u.User.Password(); hasPassword {
			u.User = url.UserPassword(u.User.Username(), "********")
		}
	}

	if u.RawQuery != "" {
		q := u.Query()
		modified := false
		for key, vals := range q {
			kLower := strings.ToLower(key)
			isSensitive := false
			for _, p := range sensitiveKeyPatterns {
				if strings.Contains(kLower, p) {
					isSensitive = true
					break
				}
			}
			if isSensitive || kLower == "sig" || kLower == "signature" || kLower == "auth" {
				for i := range vals {
					vals[i] = "********"
				}
				q[key] = vals
				modified = true
			}
		}
		if modified {
			u.RawQuery = strings.ReplaceAll(q.Encode(), "%2A%2A%2A%2A%2A%2A%2A%2A", "********")
		}
	}

	return strings.ReplaceAll(u.String(), "%2A%2A%2A%2A%2A%2A%2A%2A", "********")
}

// HasMaskedURLCredentials checks if a URL contains masked password or masked query parameters.
func HasMaskedURLCredentials(rawURL string) bool {
	if !strings.Contains(rawURL, "://") {
		return false
	}
	u, err := url.Parse(rawURL)
	if err != nil {
		return strings.Contains(rawURL, "://") && (strings.Contains(rawURL, ":***") || strings.Contains(rawURL, "=***"))
	}
	if u.User != nil {
		if pw, hasPassword := u.User.Password(); hasPassword && (IsMaskedValue(pw) || strings.Contains(pw, "***")) {
			return true
		}
	}
	if u.RawQuery != "" {
		for _, vals := range u.Query() {
			for _, v := range vals {
				if IsMaskedValue(v) || strings.Contains(v, "***") {
					return true
				}
			}
		}
	}
	return false
}

// MergeMaskedURL merges an incoming masked URL with an existing encrypted/plain URL to restore masked credentials.
func MergeMaskedURL(existingEncOrPlain, incomingURL string) string {
	if !strings.Contains(incomingURL, "://") {
		return incomingURL
	}
	existingPlain := existingEncOrPlain
	if IsEncryptedKey(existingEncOrPlain) {
		if dec, err := DecryptAPIKey(existingEncOrPlain, ""); err == nil {
			existingPlain = dec
		}
	}
	if !strings.Contains(existingPlain, "://") {
		return incomingURL
	}

	uOrig, errOrig := url.Parse(existingPlain)
	uInc, errInc := url.Parse(incomingURL)
	if errOrig != nil || errInc != nil {
		return incomingURL
	}

	scheme := uInc.Scheme
	host := uInc.Host
	userinfo := ""
	if uInc.User != nil {
		username := uInc.User.Username()
		pw, hasPW := uInc.User.Password()
		if hasPW {
			if IsMaskedValue(pw) || strings.Contains(pw, "***") {
				origPW := ""
				if uOrig.User != nil {
					if p, ok := uOrig.User.Password(); ok {
						origPW = p
					}
				}
				if origPW != "" {
					pw = origPW
				}
			}
			userinfo = username + ":" + pw
		} else {
			userinfo = username
		}
	}

	fullNetloc := host
	if userinfo != "" {
		fullNetloc = userinfo + "@" + host
	}

	rawQuery := uInc.RawQuery
	if uInc.RawQuery != "" && uOrig.RawQuery != "" {
		incPairs := strings.Split(uInc.RawQuery, "&")
		origQ := uOrig.Query()
		mergedPairs := make([]string, 0, len(incPairs))
		for _, pair := range incPairs {
			kv := strings.SplitN(pair, "=", 2)
			k := kv[0]
			v := ""
			if len(kv) == 2 {
				v = kv[1]
			}
			decodedV, _ := url.QueryUnescape(v)
			if IsMaskedValue(decodedV) || strings.Contains(decodedV, "***") || strings.Contains(v, "********") {
				if origVals, exists := origQ[k]; exists && len(origVals) > 0 {
					mergedPairs = append(mergedPairs, k+"="+origVals[0])
					continue
				}
			}
			mergedPairs = append(mergedPairs, pair)
		}
		rawQuery = strings.Join(mergedPairs, "&")
	}

	res := scheme + "://" + fullNetloc + uInc.Path
	if rawQuery != "" {
		res += "?" + rawQuery
	}
	if uInc.Fragment != "" {
		res += "#" + uInc.Fragment
	}
	return res
}

// IsEncryptedKey checks if a string is encrypted with enc:v2: (AES-256-GCM) or legacy enc:v1:.
func IsEncryptedKey(text string) bool {
	trimmed := strings.TrimSpace(text)
	return strings.HasPrefix(trimmed, "enc:v2:") || strings.HasPrefix(trimmed, "enc:v1:")
}

// EncryptAPIKey encrypts a sensitive string using standard AES-256-GCM via HKDF (enc:v2:).
// Fails closed if the secret key is missing, too short, or an insecure default.
func EncryptAPIKey(rawText, secret string) (string, error) {
	if rawText == "" {
		return "", nil
	}
	rawStr := strings.TrimSpace(rawText)
	if strings.HasPrefix(rawStr, "enc:v2:") {
		return rawStr, nil
	}

	masterSecret := secret
	if masterSecret == "" {
		masterSecret = getMasterSecret()
	}
	validatedSecret, err := validateMasterSecret(masterSecret)
	if err != nil {
		return "", err
	}

	if strings.HasPrefix(rawStr, "enc:v1:") {
		dec, err := DecryptAPIKey(rawStr, validatedSecret)
		if err == nil && dec != rawStr {
			rawStr = dec
		} else {
			return rawStr, nil
		}
	}

	aesKey, err := deriveAES256KeyHKDF(validatedSecret)
	if err != nil {
		return "", err
	}

	block, err := aes.NewCipher(aesKey)
	if err != nil {
		return "", err
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}

	nonce := make([]byte, gcm.NonceSize()) // 12 bytes
	if _, err := rand.Read(nonce); err != nil {
		return "", err
	}

	ct := gcm.Seal(nil, nonce, []byte(rawStr), nil)
	payload := append(nonce, ct...)
	return "enc:v2:" + base64.StdEncoding.EncodeToString(payload), nil
}

func decryptV2(payload []byte, candidates []string) (string, bool) {
	if len(payload) < 28 { // 12 nonce + 16 tag
		return "", false
	}
	nonce := payload[:12]
	ctWithTag := payload[12:]
	for _, cand := range candidates {
		key, err := deriveAES256KeyHKDF(cand)
		if err != nil {
			continue
		}
		block, err := aes.NewCipher(key)
		if err != nil {
			continue
		}
		gcm, err := cipher.NewGCM(block)
		if err != nil {
			continue
		}
		pt, err := gcm.Open(nil, nonce, ctWithTag, nil)
		if err == nil {
			return string(pt), true
		}
	}
	log.Printf("[ERROR] CRITICAL: DecryptAPIKey failed: authentication tag verification failed with primary key and %d rotation candidate(s).", max(0, len(candidates)-1))
	return "", false
}

func decryptV1(payload []byte, candidates []string) (string, bool) {
	if len(payload) < 32 {
		return "", false
	}
	iv := payload[:16]
	tag := payload[16:32]
	ct := payload[32:]
	for _, cand := range candidates {
		kEnc, kMac := deriveLegacyV1Keys(cand)
		mac := hmac.New(sha256.New, kMac)
		mac.Write(iv)
		mac.Write(ct)
		expectedTag := mac.Sum(nil)[:16]
		if !hmac.Equal(tag, expectedTag) {
			continue
		}
		ks := legacyV1Keystream(kEnc, iv, len(ct))
		pt := make([]byte, len(ct))
		for i := range ct {
			pt[i] = ct[i] ^ ks[i]
		}
		return string(pt), true
	}
	log.Printf("[ERROR] CRITICAL: DecryptAPIKey legacy v1 failed: tag mismatch across all %d candidate(s).", len(candidates))
	return "", false
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// DecryptAPIKey decrypts a ciphertext string, trying primary key then rotation keys.
// Supports enc:v2: (AES-256-GCM via HKDF) and legacy enc:v1: (HMAC-SHA256 CTR).
func DecryptAPIKey(encText, secret string) (string, error) {
	if encText == "" {
		return "", nil
	}
	encStr := strings.TrimSpace(encText)
	if !strings.HasPrefix(encStr, "enc:v2:") && !strings.HasPrefix(encStr, "enc:v1:") {
		return encStr, nil
	}

	candidates := getKeyCandidates(secret)
	if len(candidates) == 0 {
		log.Printf("[ERROR] CRITICAL: DecryptAPIKey called but no secret keys are configured in environment!")
		return encStr, nil
	}

	if strings.HasPrefix(encStr, "enc:v2:") {
		payload, err := base64.StdEncoding.DecodeString(encStr[7:])
		if err != nil {
			return encStr, nil
		}
		if pt, ok := decryptV2(payload, candidates); ok {
			return pt, nil
		}
		return encStr, nil
	}

	if strings.HasPrefix(encStr, "enc:v1:") {
		payload, err := base64.StdEncoding.DecodeString(encStr[7:])
		if err != nil {
			return encStr, nil
		}
		if pt, ok := decryptV1(payload, candidates); ok {
			return pt, nil
		}
		return encStr, nil
	}

	return encStr, nil
}

// IsMaskedValue checks if a string is a masked credential placeholder.
func IsMaskedValue(val any) bool {
	s, ok := val.(string)
	if !ok {
		return false
	}
	trimmed := strings.TrimSpace(s)
	return trimmed == "********" || ((strings.Contains(trimmed, "...") || strings.Contains(trimmed, "***")) && len(trimmed) <= 16)
}

func isSensitiveKey(key string, inDenyByDefaultScope bool, val string) bool {
	kLower := strings.ToLower(strings.TrimSpace(key))
	if inDenyByDefaultScope {
		if publicIdentifierFields[kLower] {
			if HasEmbeddedURLCredentials(val) {
				return true
			}
			return false
		}
		return true
	}
	for _, p := range sensitiveKeyPatterns {
		if strings.Contains(kLower, p) {
			return true
		}
	}
	if HasEmbeddedURLCredentials(val) {
		return true
	}
	return false
}

func toMapStringAny(v any) (map[string]any, bool) {
	if v == nil {
		return nil, false
	}
	switch m := v.(type) {
	case map[string]any:
		return m, true
	case entity.JSONMap:
		return map[string]any(m), true
	default:
		return nil, false
	}
}

// EncryptConnectorConfig recursively encrypts sensitive values in a connector config.
func EncryptConnectorConfig(config map[string]any) map[string]any {
	if config == nil {
		return nil
	}
	return encryptConnectorMap(config, false)
}

func encryptConnectorMap(m map[string]any, inScope bool) map[string]any {
	result := make(map[string]any, len(m))
	for k, v := range m {
		kLower := strings.ToLower(k)
		subInScope := inScope || denyByDefaultSections[kLower]
		if subMap, ok := toMapStringAny(v); ok {
			result[k] = encryptConnectorMap(subMap, subInScope)
			continue
		}
		switch val := v.(type) {
		case []any:
			result[k] = encryptConnectorSlice(val, subInScope)
		case string:
			if isSensitiveKey(k, subInScope, val) {
				trimmed := strings.TrimSpace(val)
				if trimmed != "" && !strings.HasPrefix(trimmed, "enc:v2:") && !IsMaskedValue(trimmed) {
					if enc, err := EncryptAPIKey(trimmed, ""); err == nil {
						result[k] = enc
						continue
					}
				}
			}
			result[k] = val
		default:
			result[k] = val
		}
	}
	return result
}

func encryptConnectorSlice(s []any, inScope bool) []any {
	result := make([]any, len(s))
	for i, v := range s {
		if m, ok := toMapStringAny(v); ok {
			result[i] = encryptConnectorMap(m, inScope)
		} else {
			result[i] = v
		}
	}
	return result
}

// DecryptConnectorConfig recursively decrypts any encrypted values in a connector config.
func DecryptConnectorConfig(config map[string]any) map[string]any {
	if config == nil {
		return nil
	}
	result := make(map[string]any, len(config))
	for k, v := range config {
		if subMap, ok := toMapStringAny(v); ok {
			result[k] = DecryptConnectorConfig(subMap)
			continue
		}
		switch val := v.(type) {
		case []any:
			result[k] = decryptConnectorSlice(val)
		case string:
			if IsEncryptedKey(val) {
				if dec, err := DecryptAPIKey(val, ""); err == nil {
					result[k] = dec
					continue
				}
			}
			result[k] = val
		default:
			result[k] = val
		}
	}
	return result
}

func decryptConnectorSlice(s []any) []any {
	result := make([]any, len(s))
	for i, v := range s {
		if m, ok := toMapStringAny(v); ok {
			result[i] = DecryptConnectorConfig(m)
		} else {
			result[i] = v
		}
	}
	return result
}

// MaskConnectorConfig recursively masks sensitive fields for safe API responses.
func MaskConnectorConfig(config map[string]any) map[string]any {
	if config == nil {
		return nil
	}
	return maskConnectorMap(config, false)
}

func maskConnectorMap(m map[string]any, inScope bool) map[string]any {
	result := make(map[string]any, len(m))
	for k, v := range m {
		kLower := strings.ToLower(k)
		subInScope := inScope || denyByDefaultSections[kLower]
		if subMap, ok := toMapStringAny(v); ok {
			result[k] = maskConnectorMap(subMap, subInScope)
			continue
		}
		switch val := v.(type) {
		case []any:
			result[k] = maskConnectorSlice(val, subInScope)
		case string:
			plainVal := val
			if IsEncryptedKey(val) {
				if dec, err := DecryptAPIKey(val, ""); err == nil {
					plainVal = dec
				}
			}
			if strings.Contains(plainVal, "://") && (HasEmbeddedURLCredentials(plainVal) || kLower == "instance_url" || kLower == "url" || kLower == "site_url" || kLower == "rss_url" || kLower == "sitemap_url") {
				result[k] = SanitizeURLCredentials(plainVal)
			} else if isSensitiveKey(k, subInScope, plainVal) {
				if plainVal != "" {
					result[k] = "********"
				} else {
					result[k] = ""
				}
			} else if strings.Contains(plainVal, "://") {
				result[k] = SanitizeURLCredentials(plainVal)
			} else {
				result[k] = plainVal
			}
		default:
			result[k] = val
		}
	}
	return result
}

func maskConnectorSlice(s []any, inScope bool) []any {
	result := make([]any, len(s))
	for i, v := range s {
		if m, ok := toMapStringAny(v); ok {
			result[i] = maskConnectorMap(m, inScope)
		} else {
			result[i] = v
		}
	}
	return result
}

// MergeUpdatedConnectorConfig safely merges an updated config into an existing config,
// preserving existing secrets when incoming is masked.
func MergeUpdatedConnectorConfig(existing, incoming map[string]any) map[string]any {
	if existing == nil {
		existing = make(map[string]any)
	}
	if incoming == nil {
		return EncryptConnectorConfig(existing)
	}
	merged := mergeConnectorMaps(existing, incoming, false)
	return EncryptConnectorConfig(merged)
}

func mergeConnectorMaps(existing, incoming map[string]any, inScope bool) map[string]any {
	result := make(map[string]any, len(existing)+len(incoming))
	for k, v := range existing {
		result[k] = v
	}
	for k, v := range incoming {
		kLower := strings.ToLower(k)
		subInScope := inScope || denyByDefaultSections[kLower]
		existingVal, hasExisting := result[k]
		if incomingMap, ok := toMapStringAny(v); ok {
			if existingMap, ok := toMapStringAny(existingVal); ok {
				result[k] = mergeConnectorMaps(existingMap, incomingMap, subInScope)
				continue
			}
		}
		if IsMaskedValue(v) {
			if hasExisting && existingVal != nil && existingVal != "" {
				// Retain existing encrypted secret
				continue
			}
			result[k] = ""
			continue
		}
		if s, ok := v.(string); ok && HasMaskedURLCredentials(s) && hasExisting && existingVal != nil && existingVal != "" {
			if existingStr, ok := existingVal.(string); ok {
				result[k] = MergeMaskedURL(existingStr, s)
				continue
			}
		}
		if s, ok := v.(string); ok && isSensitiveKey(k, subInScope, s) && strings.TrimSpace(s) == "" && hasExisting && existingVal != nil && existingVal != "" {
			// Empty string for existing secret, retain existing
			continue
		}
		result[k] = v
	}
	return result
}

// MaskConnectorEntity returns a copy of the connector with its Config masked.
func MaskConnectorEntity(conn *entity.Connector) *entity.Connector {
	if conn == nil {
		return nil
	}
	cp := *conn
	if cp.Config != nil {
		cp.Config = entity.JSONMap(MaskConnectorConfig(map[string]any(cp.Config)))
	}
	return &cp
}

// MaskConnectorEntities returns a slice of connectors with Config masked.
func MaskConnectorEntities(conns []*entity.Connector) []*entity.Connector {
	if conns == nil {
		return nil
	}
	res := make([]*entity.Connector, len(conns))
	for i, c := range conns {
		res[i] = MaskConnectorEntity(c)
	}
	return res
}
