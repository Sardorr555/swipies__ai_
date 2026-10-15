//
// Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//

package connector

import (
	"context"
	"os"
	"strings"
	"testing"

	"ragflow/internal/dao"
	"ragflow/internal/entity"
	"ragflow/internal/utility"
)

type mockBuiltinConnector struct {
	cfg map[string]any
}

func (m *mockBuiltinConnector) Validate(ctx context.Context) error { return nil }
func (m *mockBuiltinConnector) OpenSync(ctx context.Context, req SyncRequest) (SyncSession, error) {
	return nil, nil
}
func (m *mockBuiltinConnector) OpenPrune(ctx context.Context, req PruneRequest) (PruneSession, error) {
	return nil, nil
}

func TestBuiltin_RegisterBuiltIn_DecryptionMutation(t *testing.T) {
	testSecret := "test-master-secret-key-32bytes-ok!"
	os.Setenv("RAGFLOW_SECRET_KEY", testSecret)
	defer os.Unsetenv("RAGFLOW_SECRET_KEY")

	// 1. Prepare raw secret and encrypt it into enc:v2: format
	rawToken := "super-confidential-jira-pat-999"
	encToken, err := utility.EncryptAPIKey(rawToken, testSecret)
	if err != nil {
		t.Fatalf("failed to encrypt token: %v", err)
	}
	if !strings.HasPrefix(encToken, "enc:v2:") {
		t.Fatalf("expected enc:v2: prefix, got: %s", encToken)
	}

	encConfig := map[string]any{
		"credentials": map[string]any{
			"token": encToken,
		},
	}

	registry := NewRegistry()
	var receivedConfig map[string]any

	registerBuiltIn(registry, "mock_source", func(cfg map[string]any) (*mockBuiltinConnector, error) {
		receivedConfig = cfg
		return &mockBuiltinConnector{cfg: cfg}, nil
	})

	// 2. Open via TaskFactory (runtime path in syncer)
	taskCtx := dao.SyncTaskContext{
		Connector: entity.Connector{
			Source: "mock_source",
			Config: entity.JSONMap(encConfig),
		},
	}

	_, err = registry.Open(context.Background(), taskCtx)
	if err != nil {
		t.Fatalf("registry.Open failed: %v", err)
	}

	creds, ok := receivedConfig["credentials"].(map[string]any)
	if !ok {
		t.Fatalf("missing credentials map in factory: %v", receivedConfig)
	}

	tokenVal, _ := creds["token"].(string)
	if tokenVal != rawToken {
		t.Fatalf("DECRYPTION MUTATION TRIGGER: expected plaintext '%s', got '%s'", rawToken, tokenVal)
	}

	// 3. Open via ConfigFactory (test-connection path)
	receivedConfig = nil
	_, err = registry.OpenFromConfig("mock_source", encConfig)
	if err != nil {
		t.Fatalf("registry.OpenFromConfig failed: %v", err)
	}

	creds2, ok := receivedConfig["credentials"].(map[string]any)
	if !ok {
		t.Fatalf("missing credentials map in config factory: %v", receivedConfig)
	}
	tokenVal2, _ := creds2["token"].(string)
	if tokenVal2 != rawToken {
		t.Fatalf("DECRYPTION MUTATION TRIGGER: expected plaintext '%s', got '%s'", rawToken, tokenVal2)
	}
}
