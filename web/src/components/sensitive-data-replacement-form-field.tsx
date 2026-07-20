import React, { useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-[#t]' || 'react';
import { useTranslation as useI18nTranslation } from 'react-i18next';
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  ShieldAlert,
  Plus,
  Trash2,
  Download,
  Upload,
  Eye,
  Check,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { prefixName } from '@/utils/form';

export interface ReplacementRule {
  id: string;
  search_value: string;
  replace_value: string;
  case_sensitive?: boolean;
  is_regex?: boolean;
}

interface SensitiveDataReplacementFormFieldProps {
  prefix?: string;
}

export function SensitiveDataReplacementFormField({
  prefix = '',
}: SensitiveDataReplacementFormFieldProps) {
  const { t } = useI18nTranslation();
  const form = useFormContext();

  const enabledName = prefixName(prefix, 'prompt_config.sensitive_data_replacement.enabled');
  const rulesName = prefixName(prefix, 'prompt_config.sensitive_data_replacement.rules');

  const enabled = useWatch({
    control: form.control,
    name: enabledName,
  });

  const rules: ReplacementRule[] = useWatch({
    control: form.control,
    name: rulesName,
  }) || [];

  const [previewInput, setPreviewInput] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  const handleAddRule = () => {
    const newRule: ReplacementRule = {
      id: Math.random().toString(36).substr(2, 9),
      search_value: '',
      replace_value: '',
      case_sensitive: false,
      is_regex: false,
    };
    const updatedRules = [...rules, newRule];
    form.setValue(rulesName, updatedRules, { shouldDirty: true });
  };

  const handleDeleteRule = (id: string) => {
    const updatedRules = rules.filter((r) => r.id !== id);
    form.setValue(rulesName, updatedRules, { shouldDirty: true });
  };

  const handleRuleChange = (
    id: string,
    field: keyof ReplacementRule,
    value: any,
  ) => {
    const updatedRules = rules.map((r) => {
      if (r.id === id) {
        return { ...r, [field]: value };
      }
      return r;
    });
    form.setValue(rulesName, updatedRules, { shouldDirty: true });
  };

  const handleExportJSON = () => {
    const dataStr =
      'data:text/json;charset=utf-8,' +
      encodeURIComponent(JSON.stringify(rules, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', 'sensitive_replacement_rules.json');
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleImportJSON = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileReader = new FileReader();
    if (e.target.files && e.target.files[0]) {
      fileReader.readAsText(e.target.files[0], 'UTF-8');
      fileReader.onload = (event) => {
        try {
          const parsed = JSON.parse(event.target?.result as string);
          if (Array.isArray(parsed)) {
            const formatted = parsed.map((item: any) => ({
              id: item.id || Math.random().toString(36).substr(2, 9),
              search_value: item.search_value || item.search || '',
              replace_value: item.replace_value || item.replace || '',
              case_sensitive: !!item.case_sensitive,
              is_regex: !!item.is_regex,
            }));
            form.setValue(rulesName, formatted, { shouldDirty: true });
          }
        } catch (err) {
          alert('Invalid JSON file format.');
        }
      };
    }
  };

  // Preview replacement simulation
  const getPreviewResult = () => {
    if (!previewInput) return '';
    let text = previewInput;
    rules.forEach((rule) => {
      if (!rule.search_value || !rule.replace_value) return;
      try {
        if (rule.is_regex) {
          const flags = rule.case_sensitive ? 'g' : 'gi';
          const reg = new RegExp(rule.search_value, flags);
          text = text.replace(reg, rule.replace_value);
        } else {
          if (rule.case_sensitive) {
            text = text.replaceAll(rule.search_value, rule.replace_value);
          } else {
            const reg = new RegExp(
              rule.search_value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
              'gi',
            );
            text = text.replace(reg, rule.replace_value);
          }
        }
      } catch (e) {
        // Fallback simple replace
        text = text.replaceAll(rule.search_value, rule.replace_value);
      }
    });
    return text;
  };

  return (
    <div className="space-y-4 pt-2 border-t border-border/60">
      <FormField
        control={form.control}
        name={enabledName}
        render={({ field }) => (
          <FormItem className="flex flex-row items-center justify-between rounded-xl border border-border/60 bg-bg-component/30 p-3 shadow-sm">
            <div className="space-y-0.5">
              <FormLabel className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
                <ShieldAlert className="size-4 text-amber-500 shrink-0" />
                <span>Sensitive Data Replacement</span>
              </FormLabel>
              <p className="text-xs text-text-secondary">
                Anonymize client PII (names, phones, IDs) before sending to LLM, then restore placeholders in responses.
              </p>
            </div>
            <FormControl>
              <Switch
                checked={field.value}
                onCheckedChange={field.onChange}
              />
            </FormControl>
          </FormItem>
        )}
      />

      {enabled && (
        <Card className="border border-border/80 bg-bg-body/50 backdrop-blur-sm">
          <CardContent className="p-4 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 pb-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-1">
                Privacy & Data Anonymization Rules ({rules.length})
              </h4>

              <div className="flex items-center gap-1.5">
                <label className="cursor-pointer">
                  <input
                    type="file"
                    accept=".json"
                    className="hidden"
                    onChange={handleImportJSON}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 text-[11px] gap-1 px-2"
                  >
                    <Upload className="size-3" />
                    Import
                  </Button>
                </label>

                {rules.length > 0 && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 text-[11px] gap-1 px-2"
                    onClick={handleExportJSON}
                  >
                    <Download className="size-3" />
                    Export
                  </Button>
                )}

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 text-[11px] gap-1 px-2"
                  onClick={() => setShowPreview(!showPreview)}
                >
                  <Eye className="size-3" />
                  {showPreview ? 'Hide Preview' : 'Preview'}
                </Button>

                <Button
                  type="button"
                  size="sm"
                  className="h-7 text-[11px] bg-accent-primary text-white gap-1 px-2 font-semibold"
                  onClick={handleAddRule}
                >
                  <Plus className="size-3" />
                  Add Rule
                </Button>
              </div>
            </div>

            {/* Rules Table */}
            {rules.length === 0 ? (
              <div className="text-center py-6 border border-dashed border-border/60 rounded-xl bg-bg-component/20">
                <AlertCircle className="size-6 text-text-secondary mx-auto mb-1 opacity-60" />
                <p className="text-xs text-text-secondary">
                  No anonymization rules configured. Click <b>Add Rule</b> to add values like names or numbers to redact.
                </p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                <div className="grid grid-cols-12 gap-2 text-[10px] font-bold uppercase tracking-wider text-text-secondary px-1">
                  <div className="col-span-4">Search Value (Original)</div>
                  <div className="col-span-4">Replace With (Placeholder)</div>
                  <div className="col-span-3 text-center">Options</div>
                  <div className="col-span-1 text-right">Delete</div>
                </div>

                {rules.map((rule) => (
                  <div
                    key={rule.id}
                    className="grid grid-cols-12 gap-2 items-center bg-bg-component/60 border border-border/40 p-1.5 rounded-lg text-xs"
                  >
                    <div className="col-span-4">
                      <Input
                        value={rule.search_value}
                        onChange={(e) =>
                          handleRuleChange(rule.id, 'search_value', e.target.value)
                        }
                        placeholder="e.g. Иван Иванов"
                        className="h-7 text-xs bg-bg-input"
                      />
                    </div>
                    <div className="col-span-4">
                      <Input
                        value={rule.replace_value}
                        onChange={(e) =>
                          handleRuleChange(rule.id, 'replace_value', e.target.value)
                        }
                        placeholder="e.g. CLIENT_NAME"
                        className="h-7 text-xs bg-bg-input"
                      />
                    </div>

                    <div className="col-span-3 flex items-center justify-center gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          handleRuleChange(
                            rule.id,
                            'case_sensitive',
                            !rule.case_sensitive,
                          )
                        }
                        title="Case Sensitive (Aa)"
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold border transition-colors ${
                          rule.case_sensitive
                            ? 'bg-accent-primary text-white border-accent-primary'
                            : 'bg-bg-body text-text-secondary border-border/60 hover:text-text-primary'
                        }`}
                      >
                        Aa
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          handleRuleChange(rule.id, 'is_regex', !rule.is_regex)
                        }
                        title="Regular Expression (.*)"
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold border transition-colors ${
                          rule.is_regex
                            ? 'bg-purple-600 text-white border-purple-600'
                            : 'bg-bg-body text-text-secondary border-border/60 hover:text-text-primary'
                        }`}
                      >
                        .*
                      </button>
                    </div>

                    <div className="col-span-1 text-right">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        className="size-6 text-red-400 hover:text-red-500 hover:bg-red-500/10"
                        onClick={() => handleDeleteRule(rule.id)}
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Real-time Test Preview */}
            {showPreview && (
              <div className="p-3 bg-bg-component/40 border border-border/60 rounded-xl space-y-2 text-xs">
                <div className="font-bold text-text-primary flex items-center gap-1.5">
                  <Eye className="size-3.5 text-accent-primary" />
                  <span>Rule Pre-processing Live Tester</span>
                </div>
                <Input
                  value={previewInput}
                  onChange={(e) => setPreviewInput(e.target.value)}
                  placeholder="Type sample query e.g.: Меня зовут Иван Иванов. Телефон +998901234567"
                  className="h-8 text-xs bg-bg-input"
                />
                {previewInput && (
                  <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400 font-mono text-[11px] break-all">
                    <span className="font-bold uppercase tracking-wider text-[9px] text-emerald-500 block mb-0.5">
                      Transformed Prompt Sent to LLM:
                    </span>
                    {getPreviewResult()}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

