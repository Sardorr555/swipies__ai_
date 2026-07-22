'use client';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  FormControl,
  FormField,
  FormItem,
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
  FileCode,
  FileSpreadsheet,
  HelpCircle,
  Info,
  Plus,
  ShieldAlert,
  Trash2,
  Upload,
} from 'lucide-react';
import React, { useRef, useState } from 'react';
import { useFieldArray, useFormContext, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

interface SensitiveDataFormFieldProps {
  prefix?: string;
}

export function SensitiveDataFormField({ prefix = '' }: SensitiveDataFormFieldProps) {
  const { t } = useTranslation();
  const form = useFormContext();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);

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

  const handleDownloadJsonTemplate = () => {
    const sampleJson = [
      {
        search: 'Иван Иванов',
        replace: '[CLIENT_NAME]',
        case_sensitive: false,
        is_regex: false,
      },
      {
        search: '1234567890123456',
        replace: '[CARD_NUMBER]',
        case_sensitive: false,
        is_regex: false,
      },
      {
        search: '\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b',
        replace: '[EMAIL_ADDRESS]',
        case_sensitive: false,
        is_regex: true,
      },
    ];
    const dataStr =
      'data:text/json;charset=utf-8,' +
      encodeURIComponent(JSON.stringify(sampleJson, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', 'sensitive_data_rules_template.json');
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleDownloadCsvTemplate = () => {
    const sampleCsv = `search,replace,case_sensitive,is_regex
Иван Иванов,[CLIENT_NAME],false,false
1234567890123456,[CARD_NUMBER],false,false
\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\b,[EMAIL_ADDRESS],false,true`;

    const dataStr =
      'data:text/csv;charset=utf-8,' + encodeURIComponent(sampleCsv);
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', 'sensitive_data_rules_template.csv');
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
              search: item.search !== undefined && item.search !== null ? String(item.search) : '',
              replace: item.replace !== undefined && item.replace !== null ? String(item.replace) : '',
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
                search: parts[0] !== undefined && parts[0] !== null ? String(parts[0]).trim() : '',
                replace: parts[1] !== undefined && parts[1] !== null ? String(parts[1]).trim() : '',
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
              <p className="text-[10px] text-yellow-600 dark:text-yellow-500 font-medium">
                {t('chat.sensitiveDataStorageWarning', 'Entered rules and information remain saved on our servers whether this toggle is ON or OFF. By toggling this switch, you agree to these terms.')}{' '}
                <Link to="/privacy-policy" className="underline hover:text-primary transition-colors">
                  {t('privacyPolicy.title', 'Privacy Policy & Data Processing SLA')}
                </Link>
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

      {!isEnabled && (
        <div className="flex items-center gap-2 p-2.5 rounded-md border border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-400 text-xs">
          <Info className="size-4 shrink-0" />
          <span>{t('chat.featureDisabledNotice', 'Replacement feature is currently turned off, but your configured rules remain saved on our servers.')}</span>
        </div>
      )}

      {/* Rules list section - visible always so user can configure/view rules regardless of switch state */}
      <div className="space-y-3 pt-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {t('chat.anonymizationRules', 'Replacement Rules')}
            </span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${isEnabled ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' : 'bg-muted text-muted-foreground'}`}>
              {isEnabled ? 'Active' : 'Saved (Inactive)'}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {/* Import Template Help Modal */}
            <Dialog open={templateDialogOpen} onOpenChange={setTemplateDialogOpen}>
              <DialogTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="xs"
                  className="h-7 text-xs gap-1 text-muted-foreground hover:text-foreground"
                >
                  <HelpCircle className="size-3" />
                  {t('chat.importTemplate', 'Import Template')}
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2 text-base">
                    <FileCode className="size-4 text-primary" />
                    {t('chat.importTemplateDialogTitle', 'Rule Import Format & Examples')}
                  </DialogTitle>
                  <DialogDescription className="text-xs pt-1">
                    {t('chat.importTemplateDialogDesc', 'You can import replacement rules using JSON or CSV format. Download a sample file below or format your file as shown in the examples.')}
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-2">
                  <div>
                    <h4 className="text-xs font-semibold mb-1 flex items-center gap-1.5 text-foreground">
                      <FileCode className="size-3 text-blue-500" /> JSON Format Example
                    </h4>
                    <pre className="p-3 rounded-md bg-zinc-950 text-zinc-100 text-[11px] overflow-x-auto font-mono">
{`[
  {
    "search": "Иван Иванов",
    "replace": "[CLIENT_NAME]",
    "case_sensitive": false,
    "is_regex": false
  },
  {
    "search": "1234567890123456",
    "replace": "[CARD_NUMBER]",
    "case_sensitive": false,
    "is_regex": false
  }
]`}
                    </pre>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold mb-1 flex items-center gap-1.5 text-foreground">
                      <FileSpreadsheet className="size-3 text-emerald-500" /> CSV Format Example
                    </h4>
                    <pre className="p-3 rounded-md bg-zinc-950 text-zinc-100 text-[11px] overflow-x-auto font-mono">
{`search,replace,case_sensitive,is_regex
Иван Иванов,[CLIENT_NAME],false,false
1234567890123456,[CARD_NUMBER],false,false`}
                    </pre>
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleDownloadJsonTemplate}
                    className="gap-1.5 text-xs"
                  >
                    <Download className="size-3.5" />
                    {t('chat.downloadJsonTemplate', 'Download Sample JSON')}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleDownloadCsvTemplate}
                    className="gap-1.5 text-xs"
                  >
                    <Download className="size-3.5" />
                    {t('chat.downloadCsvTemplate', 'Download Sample CSV')}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>

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
                  <TableHead className="py-2 text-xs w-[110px] text-center">{t('chat.caseSensitive', 'Case Sensitive')}</TableHead>
                  <TableHead className="py-2 text-xs w-[90px] text-center">{t('chat.regex', 'Regex')}</TableHead>
                  <TableHead className="py-2 text-xs w-[40px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {fields.map((fieldItem, index) => (
                  <TableRow key={fieldItem.id}>
                    <TableCell className="py-1.5">
                      <FormField
                        control={form.control}
                        name={`${rulesFieldName}.${index}.search`}
                        render={({ field }) => (
                          <FormItem className="space-y-0">
                            <FormControl>
                              <Input
                                {...field}
                                placeholder={t('chat.searchPlaceholder', 'e.g. Ivan')}
                                className="h-8 text-xs"
                              />
                            </FormControl>
                          </FormItem>
                        )}
                      />
                    </TableCell>
                    <TableCell className="py-1.5">
                      <FormField
                        control={form.control}
                        name={`${rulesFieldName}.${index}.replace`}
                        render={({ field }) => (
                          <FormItem className="space-y-0">
                            <FormControl>
                              <Input
                                {...field}
                                placeholder={t('chat.replacePlaceholder', 'e.g. CLIENT_NAME')}
                                className="h-8 text-xs"
                              />
                            </FormControl>
                          </FormItem>
                        )}
                      />
                    </TableCell>
                    <TableCell className="py-1.5 text-center">
                      <FormField
                        control={form.control}
                        name={`${rulesFieldName}.${index}.case_sensitive`}
                        render={({ field }) => (
                          <FormItem className="flex justify-center items-center space-y-0">
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
                    <TableCell className="py-1.5 text-center">
                      <FormField
                        control={form.control}
                        name={`${rulesFieldName}.${index}.is_regex`}
                        render={({ field }) => (
                          <FormItem className="flex justify-center items-center space-y-0">
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
                    <TableCell className="py-1.5 text-right">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => remove(index)}
                        className="size-7 text-muted-foreground hover:text-destructive"
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
    </div>
  );
}
