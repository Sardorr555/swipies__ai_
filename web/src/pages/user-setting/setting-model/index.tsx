/*
 *  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

import Spotlight from '@/components/spotlight';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import message from '@/components/ui/message';
import { useTranslate } from '@/hooks/common-hooks';
import {
  LlmKeys,
  useAddProviderInstance,
  useFetchAddedProviders,
  useFetchProviderInstances,
  useUpdateProviderInstance,
} from '@/hooks/use-llm-request';
import { IProviderInstance } from '@/interfaces/database/llm';
import { getUserAllowedModels } from '@/services/ai-management-service';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Plus, Sparkles, Zap } from 'lucide-react';
import { FC, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { ProviderInstanceCardRef } from './instance-card/interface';
import { ProviderInstanceCard } from './instance-card/provider-instance-card';
import { ProviderHeaderBar } from './layout/provider-header-bar';
import { Sidebar, SidebarSelection } from './layout/sidebar';
import SystemSetting from './layout/system-setting';

/**
 * Sidebar-driven model provider settings page.
 *
 * Layout:
 *  - Left: `Sidebar` (Default-models entry, search, provider list).
 *  - Right:
 *      * 'default' selection -> `SystemSetting`.
 *      * provider selection  -> a sticky `ProviderHeaderBar` at the top
 *        (with a batch Save button), a vertical stack of
 *        `ProviderInstanceCard` in the middle, and a sticky "+ Instance"
 *        button at the bottom. Each click of that button adds a new
 *        draft card; multiple drafts can coexist.
 *
 * Save flow: the top Save button validates every visible card through
 * the imperative ref API; if all are valid it collects each card's
 * payload (skipping non-dirty saved cards) and dispatches one API call
 * per dirty card - `addProviderInstance` for drafts and
 * `updateProviderInstance` for saved cards.
 *
 * Special-case providers (handled inside `ProviderInstanceCard`):
 *  - `Bedrock`: rendered inline via `BedrockInstanceCard`.
 *  - All other providers (including SoMark) use the generic
 *    `GenericProviderInstanceCard` path.
 */
const SettingModelV2: FC = () => {
  const navigate = useNavigate();
  const { t: tSetting } = useTranslate('setting');
  const [selection, setSelection] = useState<SidebarSelection>('default');
  const [upgradeModalVisible, setUpgradeModalVisible] = useState(false);

  // Swipies allowed models & PRO BYOK gating
  const { data: allowedModelsRes } = useQuery({
    queryKey: ['userAllowedModels'],
    queryFn: async () => {
      const res = await getUserAllowedModels();
      return (res as any)?.data?.data ?? (res as any)?.data;
    },
  });

  const canAddCustom = useMemo(() => {
    return Boolean(
      allowedModelsRes?.is_superuser ||
      allowedModelsRes?.can_add_custom ||
      ['pro', 'enterprise'].includes((allowedModelsRes?.plan?.id || '').toLowerCase()) ||
      allowedModelsRes?.plan?.allow_byok
    );
  }, [allowedModelsRes]);

  // Stack of draft-instance identifiers, rendered as `ProviderInstanceCard`
  // entries below the persisted instances. Each draft can be cancelled
  // independently; saving is driven by the top Save button.
  const [draftIds, setDraftIds] = useState<string[]>([]);

  const [saving, setSaving] = useState(false);

  // Tracks the instance name that was just persisted by the top Save
  // button. The corresponding saved card mounts expanded so the user
  // can immediately see (and edit) what was just saved. Reset on every
  // selection change so it does not bleed across providers.
  const [newlySavedInstanceName, setNewlySavedInstanceName] = useState<
    string | null
  >(null);

  // Monotonic counter so each draft card has a stable, unique React key.
  const draftIdCounterRef = useRef(0);
  // Tracks whether the user explicitly cancelled the auto-shown draft
  // for the current selection. Reset on every selection change.
  const cancelledRef = useRef(false);

  // Imperative refs to every visible card, keyed by the card's React key
  // (instance name for saved cards, draft id for drafts). Used by the
  // top Save button to validate + collect payloads in a single batch.
  const cardRefs = useRef<Map<string, ProviderInstanceCardRef | null>>(
    new Map(),
  );

  const setCardRef = useCallback(
    (id: string) => (ref: ProviderInstanceCardRef | null) => {
      if (ref) {
        cardRefs.current.set(id, ref);
      } else {
        cardRefs.current.delete(id);
      }
    },
    [],
  );

  const queryClient = useQueryClient();

  // Active provider query string, empty when on the 'default' entry.
  const providerQueryName = selection === 'default' ? '' : selection;

  const { data: instances = [], isLoading: instancesLoading } =
    useFetchProviderInstances(providerQueryName);

  // The sidebar needs added-providers query invalidated on successful saves.
  useFetchAddedProviders();

  // Reset selection-scoped transient state when switching providers.
  useEffect(() => {
    setDraftIds([]);
    setNewlySavedInstanceName(null);
    cancelledRef.current = false;
    cardRefs.current.clear();
  }, [selection]);

  const addDraft = useCallback(() => {
    if (!canAddCustom) {
      setUpgradeModalVisible(true);
      return;
    }
    const newId = `draft-${++draftIdCounterRef.current}`;
    setDraftIds((ids) => [...ids, newId]);
  }, [canAddCustom]);

  const removeDraft = useCallback((id: string) => {
    setDraftIds((ids) => ids.filter((draftId) => draftId !== id));
    cardRefs.current.delete(id);
  }, []);

  // Auto-show a single draft card when navigating to an unconfigured provider,
  // so the form is ready immediately without requiring an extra click. If the
  // user explicitly clicks Cancel on that draft, do NOT re-spawn it.
  useEffect(() => {
    if (selection === 'default' || cancelledRef.current) return;
    if (instancesLoading) return;
    if (!canAddCustom) return;
    if (instances.length === 0 && draftIds.length === 0) {
      addDraft();
    }
  }, [selection, instances, instancesLoading, draftIds, addDraft, canAddCustom]);

  const { addProviderInstance } = useAddProviderInstance();
  const { updateProviderInstance } = useUpdateProviderInstance();

  // Batch save handler, wired to the top Save button.
  const handleSaveAll = useCallback(async () => {
    if (!canAddCustom) {
      setUpgradeModalVisible(true);
      return;
    }

    const refs = Array.from(cardRefs.current.values()).filter(
      (r): r is ProviderInstanceCardRef => r !== null,
    );
    if (refs.length === 0) return;

    const dirty = refs
      .map((r) => ({ ref: r, payload: r.getSavePayload() }))
      .filter((e) => e.payload !== null);
    if (dirty.length === 0) return;

    // Reject duplicate instance names before any API call: a draft may
    // not reuse the name of a persisted instance, nor of another draft
    // in the same batch. Without this the backend would either error or
    // silently create a second instance sharing the name.
    const takenNames = new Set(instances.map((i) => i.instance_name));
    for (const { payload } of dirty) {
      if (!payload) continue;
      const name = payload.instanceName.trim();
      if (payload.isDraft && takenNames.has(name)) {
        message.error(tSetting('instanceNameExists'));
        return;
      }
      takenNames.add(name);
    }

    const validations = await Promise.all(
      dirty.map(async (e) => ({ ...e, valid: await e.ref.validate() })),
    );
    if (validations.some((v) => !v.valid)) {
      return;
    }

    setSaving(true);
    cancelledRef.current = true;
    try {
      for (const { ref, payload } of validations) {
        if (!payload) continue;
        if (payload.apiKind === 'add') {
          const ret = await addProviderInstance(payload.payload as any);
          if (ret?.code !== 0) {
            return;
          }
          if (payload.isDraft) {
            setNewlySavedInstanceName(payload.instanceName);
          }
        } else {
          const ret = await updateProviderInstance(payload.payload as any);
          if (ret?.code !== 0) {
            return;
          }
          ref.markSaved();
        }
      }
      setDraftIds([]);
      queryClient.invalidateQueries({
        queryKey: LlmKeys.providerInstances(providerQueryName),
      });
    } finally {
      setSaving(false);
    }
  }, [
    addProviderInstance,
    updateProviderInstance,
    queryClient,
    providerQueryName,
    instances,
    tSetting,
    canAddCustom,
  ]);

  const canSave = !saving && (draftIds.length > 0 || instances.length > 0);

  const handleDraftCancel = useCallback(
    (id: string) => {
      cancelledRef.current = true;
      removeDraft(id);
    },
    [removeDraft],
  );

  const draftInstance: IProviderInstance = useMemo(
    () => ({ instance_name: '' }) as IProviderInstance,
    [],
  );

  return (
    <div className="flex w-full h-full border-[0.5px] border-border-button rounded-lg relative overflow-hidden">
      <Spotlight />
      <section className="flex flex-col gap-4 w-[320px] shrink-0 px-5 border-r-[0.5px] border-border-button overflow-auto scrollbar-auto">
        <Sidebar selection={selection} onSelect={setSelection} />
      </section>
      <section className="flex-1 flex flex-col overflow-hidden">
        {selection === 'default' ? (
          <div className="flex-1 overflow-auto scrollbar-auto">
            <SystemSetting />
          </div>
        ) : (
          <>
            {/* Sticky top: provider name + doc-link arrow + batch Save */}
            <ProviderHeaderBar
              providerName={selection as string}
              onSave={handleSaveAll}
              saving={saving}
              canSave={canSave}
            />

            {/* Scrollable middle: instance cards + optional draft cards */}
            <div className="flex-1 overflow-auto scrollbar-auto p-4 flex flex-col gap-4">
              {instances.length === 0 && draftIds.length === 0 && (
                <div className="text-text-secondary text-sm py-6 text-center">
                  {tSetting('noInstancesConfigured')}
                </div>
              )}
              {instances.map((instance, index) => (
                <ProviderInstanceCard
                  key={instance.instance_name}
                  ref={setCardRef(instance.instance_name)}
                  providerName={selection as string}
                  instance={instance}
                  defaultOpen={
                    index === 0 ||
                    instance.instance_name === newlySavedInstanceName
                  }
                />
              ))}
              {draftIds.map((id) => (
                <ProviderInstanceCard
                  key={id}
                  ref={setCardRef(id)}
                  providerName={selection as string}
                  instance={draftInstance}
                  isDraft
                  onDelete={() => handleDraftCancel(id)}
                />
              ))}
              <div className="z-10 border-border-button py-4">
                <button
                  type="button"
                  className="w-full flex items-center justify-center gap-2 px-3 py-1 rounded-md border border-dashed border-border-button text-text-secondary hover:bg-bg-input hover:text-text-primary transition-colors"
                  onClick={addDraft}
                  data-testid="add-instance-bottom"
                >
                  <Plus className="size-4" />
                  <span className="text-sm">{tSetting('addInstanceText')}</span>
                </button>
              </div>
            </div>
          </>
        )}
      </section>

      {/* Pro Plan Upgrade Dialog */}
      <Dialog open={upgradeModalVisible} onOpenChange={setUpgradeModalVisible}>
        <DialogContent className="sm:max-w-md bg-bg-base border border-border-button shadow-2xl rounded-2xl p-6">
          <DialogHeader className="space-y-3 text-center sm:text-left">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-purple-500/15 text-purple-500 border border-purple-500/20">
                <Sparkles className="size-6" />
              </div>
              <div>
                <DialogTitle className="text-xl font-bold text-text-primary">
                  Connect Your Own AI
                </DialogTitle>
                <DialogDescription className="text-xs text-text-secondary mt-0.5">
                  Bring Your Own Key (BYOK) AI Integration
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="py-4 space-y-4">
            <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs leading-relaxed text-text-primary">
              Connect your own AI provider and use your own AI models through API.
              <div className="mt-2 font-semibold text-purple-400">
                This feature is available with the PRO subscription.
              </div>
            </div>

            <div className="space-y-2 text-xs text-text-secondary">
              <div className="flex items-center gap-2.5">
                <Check className="size-4 text-emerald-500 font-bold shrink-0" />
                <span>Connect OpenAI, Anthropic, Google Gemini & custom endpoints</span>
              </div>
              <div className="flex items-center gap-2.5">
                <Check className="size-4 text-emerald-500 font-bold shrink-0" />
                <span>Zero rate limits on personal model API keys</span>
              </div>
              <div className="flex items-center gap-2.5">
                <Check className="size-4 text-emerald-500 font-bold shrink-0" />
                <span>Highest priority generation and token bandwidth</span>
              </div>
            </div>
          </div>

          <DialogFooter className="flex flex-col sm:flex-row gap-2 pt-2">
            <Button
              variant="outline"
              onClick={() => setUpgradeModalVisible(false)}
              className="w-full sm:w-auto text-xs"
            >
              Maybe later
            </Button>
            <Button
              onClick={() => {
                setUpgradeModalVisible(false);
                navigate('/user-setting/subscription');
              }}
              className="w-full sm:w-auto bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white text-xs font-semibold gap-1.5 shadow-md"
            >
              <Zap className="size-4 fill-current" />
              Upgrade to PRO
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SettingModelV2;
