'use client';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { SensitiveDataRule } from '@/interfaces/database/chat';
import { prefixName } from '@/utils/form';
import {
  Download,
  Plus,
  ShieldAlert,
  Trash2,
  Upload,
} from 'lucide-react';
import React, { useRef } from 'react';
import { useFieldArray, useFormContext, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';

interface SensitiveDataFormFieldProps {
  prefix?: string;
}

export function SensitiveDataFormField({ prefix = '' }: SensitiveDataFormFieldProps) {
  const { t } = useTranslation();
  const form = useFormContext();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const enabledFieldName = prefixName(
    prefix,
    'prompt_config.sensitive_data_replacement.enabled',
  );
  const rulesFieldName = prefixName(
    prefix,
    'prompt_config.sensitive_data_replacement.rules',
  );

  const isEnabled = useWatch({
    control: form.control,
    name: enabledFieldName,
  });

  const { fields, append, remove, replace: replaceAllFields } = useFieldArray({
    control: form.control,
    name: rulesFieldName,
  });

  const handleAddRule = () => {
    append({
      id: Date.now().toString(),
      search: '',
      replace: '',
      case_sensitive: false,
      is_regex: false,
    });
  };

  const handleExport = () => {
    const rules = form.getValues(rulesFieldName) || [];
    const dataStr =
      'data:text/json;charset=utf-8,' +
      encodeURIComponent(JSON.stringify(rules, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', 'sensitive_data_rules.json');
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const content = event.target?.result as string;
        let importedRules: SensitiveDataRule[] = [];

        if (file.name.endsWith('.json')) {
          const parsed = JSON.parse(content);
          if (Array.isArray(parsed)) {
            importedRules = parsed.map((item, idx) => ({
              id: item.id || `${Date.now()}_${idx}`,
              search: item.search || '',
              replace: item.replace || '',
              case_sensitive: Boolean(item.case_sensitive),
              is_regex: Boolean(item.is_regex),
            }));
          }
        } else if (file.name.endsWith('.csv')) {
          const lines = content.split(/\r?\n/);
          importedRules = lines
            .filter((line) => line.trim().length > 0)
            .map((line, idx) => {
              const parts = line.split(',');
              return {
                id: `${Date.now()}_${idx}`,
                search: parts[0]?.trim() || '',
                replace: parts[1]?.trim() || '',
                case_sensitive: parts[2]?.trim().toLowerCase() === 'true',
                is_regex: parts[3]?.trim().toLowerCase() === 'true',
              };
            });
        }

        if (importedRules.length > 0) {
          const currentRules = form.getValues(rulesFieldName) || [];
          replaceAllFields([...currentRules, ...importedRules]);
        }
      } catch (err) {
        console.error('Failed to import rules', err);
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  return (
    <div className="space-y-4 rounded-lg border border-border p-4 bg-background/50">
      <FormField
        control={form.control}
        name={enabledFieldName}
        render={({ field }) => (
          <FormItem className="flex flex-row items-center justify-between space-y-0">
            <div className="space-y-1">
              <div className="flex items-center space-x-2 font-medium text-sm">
                <ShieldAlert className="size-4 text-primary" />
                <span>{t('chat.sensitiveDataReplacement', 'Sensitive Data Replacement')}</span>
              </div>
              <p className="text-xs text-muted-foreground">
                {t('chat.sensitiveDataReplacementTip', 'Automatically anonymize user data before sending queries to LLM.')}
              </p>
            </div>
            <FormControl>
              <Switch
                checked={Boolean(field.value)}
                onCheckedChange={field.onChange}
              />
            </FormControl>
          </FormItem>
        )}
      />

      {isEnabled && (
        <div className="space-y-3 pt-2">
          <div className="flex justify-between items-center">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t('chat.anonymizationRules', 'Replacement Rules')}
            </span>
            <div className="flex items-center space-x-2">
              <Button
                type="button"
                variant="outline"
                size="xs"
                onClick={handleImportClick}
                className="h-7 text-xs gap-1"
              >
                <Upload className="size-3" />
                {t('common.import', 'Import')}
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,.csv"
                className="hidden"
                onChange={handleFileChange}
              />

              <Button
                type="button"
                variant="outline"
                size="xs"
                onClick={handleExport}
                className="h-7 text-xs gap-1"
              >
                <Download className="size-3" />
                {t('common.export', 'Export')}
              </Button>

              <Button
                type="button"
                variant="secondary"
                size="xs"
                onClick={handleAddRule}
                className="h-7 text-xs gap-1"
              >
                <Plus className="size-3" />
                {t('common.add', 'Add Rule')}
              </Button>
            </div>
          </div>

          {fields.length === 0 ? (
            <div className="text-center py-6 border border-dashed rounded-md text-xs text-muted-foreground">
              {t('chat.noSensitiveRules', 'No rules added yet. Click "Add Rule" to create one.')}
            </div>
          ) : (
            <div className="border rounded-md overflow-hidden bg-card">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="py-2 text-xs">{t('chat.searchValue', 'Search Value')}</TableHead>
                    <TableHead className="py-2 text-xs">{t('chat.replaceValue', 'Replace Value')}</TableHead>
                    <TableHead className="py-2 text-xs w-20 text-center">{t('chat.caseSensitive', 'Case')}</TableHead>
                    <TableHead className="py-2 text-xs w-16 text-center">{t('chat.regex', 'Regex')}</TableHead>
                    <TableHead className="py-2 text-xs w-12 text-right"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {fields.map((fieldItem, index) => (
                    <TableRow key={fieldItem.id} className="hover:bg-muted/40">
                      <TableCell className="p-2">
                        <FormField
                          control={form.control}
                          name={`${rulesFieldName}.${index}.search`}
                          render={({ field }) => (
                            <FormItem className="space-y-0">
                              <FormControl>
                                <Input
                                  {...field}
                                  placeholder={t('chat.searchPlaceholder', 'e.g. Иван Иванов')}
                                  className="h-8 text-xs bg-background"
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      </TableCell>

                      <TableCell className="p-2">
                        <FormField
                          control={form.control}
                          name={`${rulesFieldName}.${index}.replace`}
                          render={({ field }) => (
                            <FormItem className="space-y-0">
                              <FormControl>
                                <Input
                                  {...field}
                                  placeholder={t('chat.replacePlaceholder', 'e.g. CLIENT_NAME')}
                                  className="h-8 text-xs bg-background"
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      </TableCell>

                      <TableCell className="p-2 text-center">
                        <FormField
                          control={form.control}
                          name={`${rulesFieldName}.${index}.case_sensitive`}
                          render={({ field }) => (
                            <FormItem className="space-y-0 flex justify-center">
                              <FormControl>
                                <Checkbox
                                  checked={Boolean(field.value)}
                                  onCheckedChange={field.onChange}
                                />
                              </FormControl>
                            </FormItem>
                          )}
                        />
                      </TableCell>

                      <TableCell className="p-2 text-center">
                        <FormField
                          control={form.control}
                          name={`${rulesFieldName}.${index}.is_regex`}
                          render={({ field }) => (
                            <FormItem className="space-y-0 flex justify-center">
                              <FormControl>
                                <Checkbox
                                  checked={Boolean(field.value)}
                                  onCheckedChange={field.onChange}
                                />
                              </FormControl>
                            </FormItem>
                          )}
                        />
                      </TableCell>

                      <TableCell className="p-2 text-right">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-xs"
                          onClick={() => remove(index)}
                          className="h-7 w-7 text-muted-foreground hover:text-destructive"
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
