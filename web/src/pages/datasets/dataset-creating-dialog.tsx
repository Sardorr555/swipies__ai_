import { DataFlowSelect } from '@/components/data-pipeline-select';
import { Button, ButtonLoading } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Switch } from '@/components/ui/switch';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FormLayout } from '@/constants/form';
import { ParseType } from '@/constants/knowledge';
import { useFetchDefaultModelDictionary } from '@/hooks/use-llm-request';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { IModalProps } from '@/interfaces/common';
import { zodResolver } from '@hookform/resolvers/zod';
import { omit } from 'lodash';
import { useEffect, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import {
  ChunkMethodItem,
  EmbeddingModelItem,
  ParseTypeItem,
} from '../dataset/dataset-setting/configuration/common-item';
import {
  Globe,
  FileText,
  Sparkles,
  Terminal,
  Play,
  XCircle,
  Search,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import api from '@/utils/api';
import request from '@/utils/request';
import message from '@/components/ui/message';
import { cn } from '@/lib/utils';

const FormId = 'dataset-creating-form';

const ChunkMethodName = 'chunk_method';

export function InputForm({ onOk }: IModalProps<any>) {
  const { t } = useTranslation();
  const defaultModelDictionary = useFetchDefaultModelDictionary();

  const FormSchema = z
    .object({
      name: z
        .string()
        .min(1, {
          message: t('knowledgeList.namePlaceholder'),
        })
        .trim(),
      parseType: z.nativeEnum(ParseType).optional(),
      embedding_model: z
        .string()
        .min(1, {
          message: t('knowledgeConfiguration.embeddingModelPlaceholder'),
        })
        .trim(),
      [ChunkMethodName]: z.string().optional(),
      pipeline_id: z.string().optional(),
    })
    .superRefine((data, ctx) => {
      // When parseType === BuiltIn, chunk_method is required
      if (
        data.parseType === ParseType.BuiltIn &&
        (!data[ChunkMethodName] || data[ChunkMethodName].trim() === '')
      ) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('knowledgeList.parserRequired'),
          path: [ChunkMethodName],
        });
      }
      // When parseType === Pipeline, pipeline_id required
      if (data.parseType === ParseType.Pipeline && !data.pipeline_id) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: t('knowledgeList.dataFlowRequired'),
          path: ['pipeline_id'],
        });
      }
    });

  const form = useForm<z.infer<typeof FormSchema>>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      name: '',
      parseType: ParseType.BuiltIn,
      [ChunkMethodName]: '',
      embedding_model: defaultModelDictionary?.embd_id,
    },
  });

  const parseType = useWatch({
    control: form.control,
    name: 'parseType',
  });

  function onSubmit(data: z.infer<typeof FormSchema>) {
    const nextData =
      parseType === ParseType.BuiltIn ? data : omit(data, ChunkMethodName);
    onOk?.(nextData);
  }

  useEffect(() => {
    if (parseType === ParseType.BuiltIn) {
      form.setValue('pipeline_id', '');
    }
    if (defaultModelDictionary?.embd_id) {
      form.setValue('embedding_model', defaultModelDictionary?.embd_id);
    }
  }, [parseType, form, defaultModelDictionary]);

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit, (errors) => {
          console.warn(errors);
        })}
        className="space-y-6"
        id={FormId}
      >
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem className="space-y-1">
              <FormLabel required>{t('knowledgeList.name')}</FormLabel>
              <FormControl>
                <Input
                  placeholder={t('knowledgeList.namePlaceholder')}
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <EmbeddingModelItem line={2} isEdit={false} />
        <ParseTypeItem />
        {parseType === ParseType.BuiltIn && (
          <ChunkMethodItem name={ChunkMethodName}></ChunkMethodItem>
        )}
        {parseType === ParseType.Pipeline && (
          <DataFlowSelect
            isMult={false}
            showToDataPipeline={true}
            formFieldName="pipeline_id"
            layout={FormLayout.Vertical}
          />
        )}
      </form>
    </Form>
  );
}

export function WebsiteInputForm({
  onClose,
  onImportStart,
}: {
  onClose?: () => void;
  onImportStart?: () => void;
}) {
  const { t } = useTranslation();
  const defaultModelDictionary = useFetchDefaultModelDictionary();
  const queryClient = useQueryClient();
  const { navigateToDataset } = useNavigatePage();

  const [url, setUrl] = useState('');
  const [crawlMode, setCrawlMode] = useState('website');
  const [maxPages, setMaxPages] = useState(50);
  const [maxDepth, setMaxDepth] = useState(2);
  const [delay, setDelay] = useState(0.5);
  const [respectRobots, setRespectRobots] = useState(true);

  // Advanced toggles
  const [extractMarkdown, setExtractMarkdown] = useState(true);
  const [extractImages, setExtractImages] = useState(true);
  const [extractTables, setExtractTables] = useState(true);
  const [cleanNavAndAds, setCleanNavAndAds] = useState(true);

  // States
  const [analyzing, setAnalyzing] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [importing, setImporting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [createdDatasetId, setCreatedDatasetId] = useState<string | null>(null);
  const [createdDatasetName, setCreatedDatasetName] = useState<string>('');
  const [jobProgress, setJobProgress] = useState<any>(null);

  const WebsiteSchema = z.object({
    name: z
      .string()
      .min(1, { message: t('knowledgeList.namePlaceholder', 'Пожалуйста, введите название датасета') })
      .trim(),
    embedding_model: z
      .string()
      .min(1, { message: t('knowledgeConfiguration.embeddingModelPlaceholder', 'Выберите модель эмбеддингов') })
      .trim(),
  });

  const form = useForm<z.infer<typeof WebsiteSchema>>({
    resolver: zodResolver(WebsiteSchema),
    defaultValues: {
      name: '',
      embedding_model: defaultModelDictionary?.embd_id || '',
    },
  });

  useEffect(() => {
    if (defaultModelDictionary?.embd_id && !form.getValues('embedding_model')) {
      form.setValue('embedding_model', defaultModelDictionary.embd_id);
    }
  }, [defaultModelDictionary, form]);

  // Poll status when activeJobId is present
  useEffect(() => {
    let timer: any = null;
    if (activeJobId && importing) {
      timer = setInterval(async () => {
        try {
          const res = await request.get(api.websiteImportStatus(activeJobId));
          const prog = res?.data?.data || res?.data;
          if (prog) {
            setJobProgress(prog);
            if (['completed', 'failed', 'cancelled'].includes(prog.status)) {
              setImporting(false);
              clearInterval(timer);
              queryClient.invalidateQueries({ queryKey: ['fetchKnowledgeList'] });
              if (prog.status === 'completed') {
                message.success(t('knowledgeList.importCompleted', 'Сбор сайта успешно завершён!'));
              }
            }
          }
        } catch (e) {
          console.error('Failed to poll status', e);
        }
      }, 1500);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [activeJobId, importing, queryClient, t]);

  const handleAnalyze = async () => {
    if (!url.trim()) {
      message.warning('Введите URL веб-сайта');
      return;
    }
    setAnalyzing(true);
    try {
      const res = await request.post(api.websiteImportPreview, {
        url: url.trim(),
        crawl_mode: crawlMode,
        max_pages: maxPages,
      });
      const preview = res?.data?.data || res?.data;
      if (preview) {
        setPreviewData(preview);
        const currentName = form.getValues('name');
        if (!currentName || currentName === 'Website Dataset') {
          if (preview.title) {
            form.setValue('name', preview.title.slice(0, 60));
          } else {
            try {
              form.setValue('name', new URL(url.trim()).hostname);
            } catch {
              form.setValue('name', 'Website Dataset');
            }
          }
        }
      }
    } catch (e: any) {
      message.error(e?.message || 'Ошибка предварительного анализа сайта');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleCancelCrawl = async () => {
    if (activeJobId) {
      try {
        await request.delete(api.websiteImportCancel(activeJobId));
        setImporting(false);
        message.info(t('knowledgeList.importCancelled', 'Сбор сайта отменён'));
      } catch (e) {
        console.error(e);
      }
    }
  };

  const onSubmit = async (data: z.infer<typeof WebsiteSchema>) => {
    if (!url.trim()) {
      message.error('Пожалуйста, укажите URL веб-сайта');
      return;
    }
    setSubmitting(true);
    try {
      const res = await request.post(api.websiteImportStart, {
        url: url.trim(),
        name: data.name.trim(),
        dataset_name: data.name.trim(),
        embedding_model: data.embedding_model,
        crawl_mode: crawlMode,
        max_pages: maxPages,
        max_depth: maxDepth,
        delay,
        respect_robots: respectRobots,
        extract_markdown: extractMarkdown,
        extract_images: extractImages,
        extract_tables: extractTables,
        remove_nav: cleanNavAndAds,
        remove_ads: cleanNavAndAds,
      });

      const responsePayload = res?.data?.data || res?.data;
      if (responsePayload?.job_id) {
        setActiveJobId(responsePayload.job_id);
        setCreatedDatasetId(responsePayload.dataset_id);
        setCreatedDatasetName(responsePayload.dataset_name || data.name);
        setImporting(true);
        onImportStart?.();
        queryClient.invalidateQueries({ queryKey: ['fetchKnowledgeList'] });
        message.success(t('knowledgeList.importJobStarted', 'Датасет успешно создан! Запущен сбор страниц'));
      } else if (res?.data?.message) {
        message.error(res.data.message);
      }
    } catch (e: any) {
      message.error(e?.message || 'Не удалось запустить сбор сайта');
    } finally {
      setSubmitting(false);
    }
  };

  // View: Live Crawl & Progress
  if (activeJobId) {
    const isCompleted = jobProgress?.status === 'completed';
    const isFailed = jobProgress?.status === 'failed';
    const isCancelled = jobProgress?.status === 'cancelled';
    const progressPercent = Math.min(
      100,
      jobProgress?.pages_processed
        ? Math.round((jobProgress.pages_processed / maxPages) * 100)
        : 10,
    );

    return (
      <div className="space-y-4 py-2">
        <div className="flex items-center justify-between border-b pb-3">
          <div className="flex items-center gap-2">
            {isCompleted ? (
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            ) : isFailed || isCancelled ? (
              <AlertCircle className="w-5 h-5 text-red-500" />
            ) : (
              <Play className="w-5 h-5 text-blue-500 animate-pulse" />
            )}
            <div>
              <h4 className="font-semibold text-base leading-tight">
                {isCompleted
                  ? 'Сбор завершён: Датасет готов!'
                  : isFailed
                  ? 'Ошибка сбора сайта'
                  : isCancelled
                  ? 'Сбор сайта отменён'
                  : 'Парсинг сайта и наполнение датасета...'}
              </h4>
              <p className="text-xs text-muted-foreground">
                Датасет: <span className="font-medium text-foreground">{createdDatasetName}</span>
              </p>
            </div>
          </div>
          <Badge
            variant={
              isCompleted
                ? 'default'
                : isFailed || isCancelled
                ? 'destructive'
                : 'secondary'
            }
          >
            {jobProgress?.status || (importing ? 'running' : 'starting')}
          </Badge>
        </div>

        <div className="space-y-1.5">
          <div className="flex justify-between text-xs font-medium text-muted-foreground">
            <span>Прогресс сбора страниц</span>
            <span>{jobProgress?.pages_processed || 0} / {maxPages} стр. ({progressPercent}%)</span>
          </div>
          <Progress value={progressPercent} className="h-2" />
        </div>

        <div className="grid grid-cols-4 gap-2 text-xs bg-muted/60 p-3 rounded-lg border">
          <div>
            <div className="text-muted-foreground">Обработано</div>
            <div className="text-sm font-bold">{jobProgress?.pages_processed || 0} стр.</div>
          </div>
          <div>
            <div className="text-muted-foreground">Документов</div>
            <div className="text-sm font-bold text-blue-600">{jobProgress?.chunks_created || 0}</div>
          </div>
          <div>
            <div className="text-muted-foreground">Время</div>
            <div className="text-sm font-bold">{jobProgress?.elapsed_seconds || 0}с</div>
          </div>
          <div>
            <div className="text-muted-foreground">Статус</div>
            <div className="text-sm font-bold capitalize">{jobProgress?.status || 'Active'}</div>
          </div>
        </div>

        {jobProgress?.current_url && (
          <div className="text-xs text-muted-foreground truncate bg-muted/30 px-2 py-1 rounded">
            Текущий URL: <span className="font-mono text-[11px]">{jobProgress.current_url}</span>
          </div>
        )}

        <div className="bg-zinc-950 text-emerald-400 p-3 rounded-lg h-44 overflow-y-auto font-mono text-xs space-y-1 border border-zinc-800">
          <div className="text-zinc-500 border-b border-zinc-800 pb-1 mb-1 flex items-center gap-1.5 text-[11px]">
            <Terminal className="w-3.5 h-3.5" />
            <span>Логи процесса сбора в реальном времени:</span>
          </div>
          {jobProgress?.logs && jobProgress.logs.length > 0 ? (
            jobProgress.logs.map((log: string, idx: number) => (
              <div key={idx} className="leading-relaxed">{log}</div>
            ))
          ) : (
            <div className="text-zinc-500 italic">Инициализация краулера...</div>
          )}
        </div>

        <div className="flex justify-between items-center pt-2 border-t">
          {importing ? (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleCancelCrawl}
              className="flex items-center gap-1.5 text-xs"
            >
              <XCircle className="w-4 h-4" />
              Остановить сбор
            </Button>
          ) : (
            <Button variant="ghost" size="sm" onClick={onClose}>
              Закрыть
            </Button>
          )}

          {createdDatasetId && (
            <Button
              size="sm"
              onClick={() => {
                onClose?.();
                navigateToDataset(createdDatasetId)();
              }}
              className="flex items-center gap-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              Перейти в датасет
              <ArrowRight className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>
    );
  }

  // View: Setup Form
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 pt-1">
        {/* URL and Analyze */}
        <div className="space-y-1.5">
          <Label className="text-xs font-semibold flex items-center gap-1">
            <Globe className="w-3.5 h-3.5 text-blue-500" />
            URL веб-сайта *
          </Label>
          <div className="flex gap-2">
            <Input
              placeholder="https://example.com или https://docs.site.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="text-xs font-mono"
            />
            <Button
              type="button"
              variant="secondary"
              onClick={handleAnalyze}
              disabled={analyzing || !url.trim()}
              className="shrink-0 text-xs flex items-center gap-1 px-3"
            >
              <Search className={cn('w-3.5 h-3.5', analyzing && 'animate-spin')} />
              {analyzing ? 'Анализ...' : 'Анализ'}
            </Button>
          </div>
        </div>

        {/* Preview Panel if analyzed */}
        {previewData && (
          <div className="bg-muted/70 p-3 rounded-lg border border-border space-y-2 text-xs">
            <div className="font-semibold flex items-center justify-between text-foreground">
              <span className="flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                Предпросмотр структуры: {previewData.title || url}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-2 text-[11px] text-muted-foreground">
              <div>Страниц: <b className="text-foreground">{previewData.detected_pages || 1}</b></div>
              <div>Оценка токенов: <b className="text-foreground">{previewData.estimated_token_count || '~'}</b></div>
              <div>Оценка чанков: <b className="text-foreground">{previewData.estimated_chunks || '~'}</b></div>
              <div>Время сбора: <b className="text-foreground">{previewData.estimated_crawl_time_seconds || '~'}с</b></div>
            </div>
          </div>
        )}

        {/* Dataset Name */}
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem className="space-y-1">
              <FormLabel required className="text-xs">Название датасета</FormLabel>
              <FormControl>
                <Input
                  placeholder="Например: Документация Swipies или Мой сайт"
                  className="text-xs"
                  {...field}
                />
              </FormControl>
              <FormMessage className="text-xs" />
            </FormItem>
          )}
        />

        {/* Embedding Model */}
        <EmbeddingModelItem line={2} isEdit={false} />

        {/* Crawl Mode & Parameters */}
        <div className="grid grid-cols-3 gap-2.5 pt-1">
          <div>
            <Label className="text-xs mb-1 block">Режим парсинга</Label>
            <Select value={crawlMode} onValueChange={setCrawlMode}>
              <SelectTrigger className="text-xs h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="website" className="text-xs">Весь сайт (Внутренние ссылки)</SelectItem>
                <SelectItem value="single_page" className="text-xs">Одна страница</SelectItem>
                <SelectItem value="sitemap" className="text-xs">Sitemap.xml</SelectItem>
                <SelectItem value="recursive" className="text-xs">Рекурсивный обход</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-xs mb-1 block">Макс. страниц</Label>
            <Input
              type="number"
              min={1}
              max={500}
              value={maxPages}
              onChange={(e) => setMaxPages(parseInt(e.target.value, 10) || 10)}
              className="text-xs h-9"
            />
          </div>

          <div>
            <Label className="text-xs mb-1 block">Глубина обхода</Label>
            <Input
              type="number"
              min={1}
              max={10}
              value={maxDepth}
              onChange={(e) => setMaxDepth(parseInt(e.target.value, 10) || 1)}
              className="text-xs h-9"
            />
          </div>
        </div>

        {/* Advanced Options Grid */}
        <div className="border-t pt-3 space-y-2">
          <Label className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            Опции фильтрации и извлечения контента
          </Label>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="extract_markdown"
                checked={extractMarkdown}
                onCheckedChange={(v) => setExtractMarkdown(!!v)}
              />
              <label htmlFor="extract_markdown" className="cursor-pointer">Извлекать Markdown</label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="extract_tables"
                checked={extractTables}
                onCheckedChange={(v) => setExtractTables(!!v)}
              />
              <label htmlFor="extract_tables" className="cursor-pointer">Извлекать таблицы</label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="extract_images"
                checked={extractImages}
                onCheckedChange={(v) => setExtractImages(!!v)}
              />
              <label htmlFor="extract_images" className="cursor-pointer">Извлекать изображения</label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="clean_nav_and_ads"
                checked={cleanNavAndAds}
                onCheckedChange={(v) => setCleanNavAndAds(!!v)}
              />
              <label htmlFor="clean_nav_and_ads" className="cursor-pointer">Очищать рекламу и навигацию</label>
            </div>

            <div className="flex items-center space-x-2 col-span-2 pt-0.5">
              <Switch
                id="respect_robots"
                checked={respectRobots}
                onCheckedChange={setRespectRobots}
              />
              <label htmlFor="respect_robots" className="text-xs cursor-pointer">
                Соблюдать правила robots.txt сайта
              </label>
            </div>
          </div>
        </div>

        <DialogFooter className="pt-3 border-t flex justify-between items-center">
          <Button type="button" variant="ghost" size="sm" onClick={onClose} className="text-xs">
            {t('common.cancel', 'Отмена')}
          </Button>
          <ButtonLoading
            type="submit"
            size="sm"
            loading={submitting}
            disabled={!url.trim()}
            className="text-xs flex items-center gap-1.5"
          >
            <Play className="w-3.5 h-3.5" />
            Создать датасет и спарсить сайт
          </ButtonLoading>
        </DialogFooter>
      </form>
    </Form>
  );
}

export interface DatasetCreatingDialogProps extends IModalProps<any> {
  initialMode?: 'standard' | 'website';
}

export function DatasetCreatingDialog({
  hideModal,
  onOk,
  loading,
  initialMode = 'standard',
}: DatasetCreatingDialogProps) {
  const { t } = useTranslation();
  const [creationMode, setCreationMode] = useState<'standard' | 'website'>(initialMode);
  const [hasStartedImport, setHasStartedImport] = useState(false);

  return (
    <Dialog open onOpenChange={hideModal}>
      <DialogContent
        className={cn(
          'focus-visible:!outline-none flex flex-col transition-all duration-150',
          creationMode === 'website'
            ? 'sm:max-w-[620px] max-h-[88vh] overflow-y-auto'
            : 'sm:max-w-[425px]',
        )}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && creationMode === 'standard') {
            e.preventDefault();
            const form = document.getElementById(FormId) as HTMLFormElement;
            form?.requestSubmit();
          }
        }}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {creationMode === 'website' ? (
              <>
                <Globe className="w-5 h-5 text-blue-500" />
                <span>Создание датасета из веб-сайта</span>
              </>
            ) : (
              t('knowledgeList.createKnowledgeBase')
            )}
          </DialogTitle>
        </DialogHeader>
        <DialogDescription className="sr-only">
          {t('knowledgeList.createKnowledgeBase')}
        </DialogDescription>

        {!hasStartedImport && (
          <Tabs
            value={creationMode}
            onValueChange={(val) => setCreationMode(val as 'standard' | 'website')}
            className="w-full"
          >
            <TabsList className="grid grid-cols-2 mb-2">
              <TabsTrigger value="standard" className="flex items-center gap-1.5 text-xs font-medium">
                <FileText className="w-3.5 h-3.5" />
                Стандартный ввод
              </TabsTrigger>
              <TabsTrigger value="website" className="flex items-center gap-1.5 text-xs font-medium">
                <Globe className="w-3.5 h-3.5 text-blue-500" />
                Парсинг сайта (Web Crawl)
              </TabsTrigger>
            </TabsList>
          </Tabs>
        )}

        {creationMode === 'standard' ? (
          <>
            <InputForm onOk={onOk} />
            <DialogFooter>
              <ButtonLoading type="submit" form={FormId} loading={loading}>
                {t('common.save')}
              </ButtonLoading>
            </DialogFooter>
          </>
        ) : (
          <WebsiteInputForm
            onClose={hideModal}
            onImportStart={() => setHasStartedImport(true)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

