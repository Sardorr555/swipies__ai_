import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Globe, Shield, Sparkles, Terminal, FileText, Search, Play, XCircle } from 'lucide-react';
import api from '@/utils/api';
import request from '@/utils/request';

interface WebsiteImportModalProps {
  visible: boolean;
  datasetId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function WebsiteImportModal({
  visible,
  datasetId,
  onClose,
  onSuccess,
}: WebsiteImportModalProps) {
  const [url, setUrl] = useState('');
  const [crawlMode, setCrawlMode] = useState('website');
  const [maxPages, setMaxPages] = useState(100);
  const [maxDepth, setMaxDepth] = useState(3);
  const [allowedDomains, setAllowedDomains] = useState('');
  const [includePaths, setIncludePaths] = useState('');
  const [excludePaths, setExcludePaths] = useState('');
  const [delay, setDelay] = useState(0.5);
  const [userAgent, setUserAgent] = useState('RAGFlow-WebCrawler/1.0');
  const [respectRobots, setRespectRobots] = useState(true);

  // Advanced Toggles
  const [extractMarkdown, setExtractMarkdown] = useState(true);
  const [extractImages, setExtractImages] = useState(true);
  const [ocrImages, setOcrImages] = useState(false);
  const [extractTables, setExtractTables] = useState(true);
  const [extractPdfs, setExtractPdfs] = useState(true);
  const [jsRendering, setJsRendering] = useState(false);
  const [ignoreNav, setIgnoreNav] = useState(true);
  const [ignoreFooter, setIgnoreFooter] = useState(true);
  const [ignoreHeader, setIgnoreHeader] = useState(false);
  const [ignoreSidebar, setIgnoreSidebar] = useState(true);
  const [removeCookieBanner, setRemoveCookieBanner] = useState(true);
  const [removeAds, setRemoveAds] = useState(true);
  const [removeDuplicates, setRemoveDuplicates] = useState(true);

  // States
  const [analyzing, setAnalyzing] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [importing, setImporting] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState<any>(null);

  // Poll job status if importing
  useEffect(() => {
    let timer: any = null;
    if (activeJobId && importing) {
      timer = setInterval(async () => {
        try {
          const res = await request.get(api.websiteImportStatus(activeJobId));
          if (res?.data) {
            setJobProgress(res.data);
            if (['completed', 'failed', 'cancelled'].includes(res.data.status)) {
              setImporting(false);
              clearInterval(timer);
              if (res.data.status === 'completed') {
                onSuccess();
              }
            }
          }
        } catch (e) {
          console.error(e);
        }
      }, 1500);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [activeJobId, importing]);

  const handleAnalyze = async () => {
    if (!url) return;
    setAnalyzing(true);
    try {
      const res = await request.post(api.websiteImportPreview, {
        url,
        crawl_mode: crawlMode,
        max_pages: maxPages,
      });
      if (res?.data) {
        setPreviewData(res.data);
      }
    } catch (e) {
      console.error('Analyze failed', e);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleStartImport = async () => {
    if (!url) return;
    setImporting(true);
    setJobProgress(null);
    try {
      const res = await request.post(api.websiteImportStart, {
        dataset_id: datasetId,
        url,
        crawl_mode: crawlMode,
        max_pages: maxPages,
        max_depth: maxDepth,
        delay,
        user_agent: userAgent,
        respect_robots: respectRobots,
        js_rendering: jsRendering,
        ignore_nav: ignoreNav,
        ignore_footer: ignoreFooter,
        ignore_header: ignoreHeader,
        ignore_sidebar: ignoreSidebar,
        remove_cookie_banner: removeCookieBanner,
        remove_ads: removeAds,
        extract_images: extractImages,
        extract_pdfs: extractPdfs,
      });
      if (res?.data?.job_id) {
        setActiveJobId(res.data.job_id);
      }
    } catch (e) {
      console.error('Start import failed', e);
      setImporting(false);
    }
  };

  const handleCancelImport = async () => {
    if (activeJobId) {
      try {
        await request.delete(api.websiteImportCancel(activeJobId));
      } catch (e) {
        console.error(e);
      }
    }
  };

  if (!visible) return null;

  return (
    <Dialog open={visible} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl font-semibold">
            <Globe className="w-6 h-6 text-blue-500" />
            Website → Dataset Importer
          </DialogTitle>
        </DialogHeader>

        {/* Source Selector Tabs */}
        <Tabs defaultValue="website" className="w-full">
          <TabsList className="grid grid-cols-4 mb-4">
            <TabsTrigger value="local" disabled>Local Files</TabsTrigger>
            <TabsTrigger value="cloud" disabled>Cloud Storage</TabsTrigger>
            <TabsTrigger value="api" disabled>API</TabsTrigger>
            <TabsTrigger value="website" className="font-bold border-b-2 border-blue-500">
              Website (NEW)
            </TabsTrigger>
          </TabsList>

          <TabsContent value="website" className="space-y-6">
            {!importing ? (
              <>
                {/* Basic Configuration */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <Label className="font-medium">Website URL *</Label>
                    <Input
                      placeholder="https://example.com or https://docs.example.com"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                    />
                  </div>

                  <div>
                    <Label>Crawl Mode</Label>
                    <Select value={crawlMode} onValueChange={setCrawlMode}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="single_page">Single Page</SelectItem>
                        <SelectItem value="website">Website (Internal Links)</SelectItem>
                        <SelectItem value="sitemap">Sitemap.xml</SelectItem>
                        <SelectItem value="url_list">URL List</SelectItem>
                        <SelectItem value="recursive">Recursive Crawl</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Maximum Pages</Label>
                    <Input
                      type="number"
                      value={maxPages}
                      onChange={(e) => setMaxPages(parseInt(e.target.value) || 10)}
                    />
                  </div>

                  <div>
                    <Label>Maximum Crawl Depth</Label>
                    <Input
                      type="number"
                      value={maxDepth}
                      onChange={(e) => setMaxDepth(parseInt(e.target.value) || 1)}
                    />
                  </div>

                  <div>
                    <Label>Request Delay (seconds)</Label>
                    <Input
                      type="number"
                      step="0.1"
                      value={delay}
                      onChange={(e) => setDelay(parseFloat(e.target.value) || 0.5)}
                    />
                  </div>

                  <div>
                    <Label>User-Agent</Label>
                    <Input value={userAgent} onChange={(e) => setUserAgent(e.target.value)} />
                  </div>

                  <div className="flex items-center space-x-2 pt-6">
                    <Switch
                      id="robots"
                      checked={respectRobots}
                      onCheckedChange={setRespectRobots}
                    />
                    <Label htmlFor="robots">Respect robots.txt</Label>
                  </div>
                </div>

                {/* Advanced Options */}
                <div className="border-t pt-4">
                  <h4 className="font-semibold text-sm mb-3 flex items-center gap-1">
                    <Sparkles className="w-4 h-4 text-amber-500" />
                    Advanced Scraping & Extraction Options
                  </h4>

                  <div className="grid grid-cols-3 gap-3 text-sm">
                    <div className="flex items-center space-x-2">
                      <Checkbox id="markdown" checked={extractMarkdown} onCheckedChange={(v) => setExtractMarkdown(!!v)} />
                      <label htmlFor="markdown">Extract Markdown</label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox id="images" checked={extractImages} onCheckedChange={(v) => setExtractImages(!!v)} />
                      <label htmlFor="images">Extract Images</label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox id="tables" checked={extractTables} onCheckedChange={(v) => setExtractTables(!!v)} />
                      <label htmlFor="tables">Extract Tables</label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox id="pdfs" checked={extractPdfs} onCheckedChange={(v) => setExtractPdfs(!!v)} />
                      <label htmlFor="pdfs">Extract PDFs</label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox id="js" checked={jsRendering} onCheckedChange={(v) => setJsRendering(!!v)} />
                      <label htmlFor="js">JavaScript Rendering (Playwright)</label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox id="nav" checked={ignoreNav} onCheckedChange={(v) => setIgnoreNav(!!v)} />
                      <label htmlFor="nav">Ignore Navigation</label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox id="footer" checked={ignoreFooter} onCheckedChange={(v) => setIgnoreFooter(!!v)} />
                      <label htmlFor="footer">Ignore Footer</label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox id="cookies" checked={removeCookieBanner} onCheckedChange={(v) => setRemoveCookieBanner(!!v)} />
                      <label htmlFor="cookies">Remove Cookie Banner</label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox id="ads" checked={removeAds} onCheckedChange={(v) => setRemoveAds(!!v)} />
                      <label htmlFor="ads">Remove Ads</label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Checkbox id="dedup" checked={removeDuplicates} onCheckedChange={(v) => setRemoveDuplicates(!!v)} />
                      <label htmlFor="dedup">Remove Duplicates</label>
                    </div>
                  </div>
                </div>

                {/* Preview Results Panel */}
                {previewData && (
                  <div className="bg-muted p-4 rounded-lg space-y-2 text-sm">
                    <h5 className="font-bold flex items-center gap-1">
                      <FileText className="w-4 h-4" />
                      Website Analysis Preview
                    </h5>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>Title: <b>{previewData.title}</b></div>
                      <div>Detected Pages: <b>{previewData.detected_pages}</b></div>
                      <div>Est. Tokens: <b>{previewData.estimated_token_count}</b></div>
                      <div>Est. Chunks: <b>{previewData.estimated_chunks}</b></div>
                      <div>Est. Embedding Cost: <b>${previewData.estimated_embedding_cost}</b></div>
                      <div>Est. Time: <b>{previewData.estimated_crawl_time_seconds}s</b></div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              /* Live Progress View */
              <div className="space-y-4 py-4">
                <div className="flex justify-between items-center">
                  <h4 className="font-bold text-lg flex items-center gap-2">
                    <Play className="w-5 h-5 text-green-500 animate-pulse" />
                    Crawling & Importing Website...
                  </h4>
                  <Badge variant={jobProgress?.status === 'completed' ? 'default' : 'outline'}>
                    {jobProgress?.status || 'running'}
                  </Badge>
                </div>

                <Progress
                  value={
                    jobProgress?.pages_processed
                      ? Math.min(100, (jobProgress.pages_processed / maxPages) * 100)
                      : 10
                  }
                />

                <div className="grid grid-cols-4 gap-2 text-sm bg-muted p-3 rounded">
                  <div>Pages Processed: <b>{jobProgress?.pages_processed || 0}</b></div>
                  <div>Chunks Created: <b>{jobProgress?.chunks_created || 0}</b></div>
                  <div>Elapsed Time: <b>{jobProgress?.elapsed_seconds || 0}s</b></div>
                  <div>Status: <b>{jobProgress?.status || 'Processing'}</b></div>
                </div>

                <div className="bg-black text-green-400 p-3 rounded h-48 overflow-y-auto font-mono text-xs space-y-1">
                  <div className="text-gray-400 border-b border-gray-700 pb-1 mb-2 flex items-center gap-1">
                    <Terminal className="w-3.5 h-3.5" />
                    Live Import Logs
                  </div>
                  {jobProgress?.logs?.map((log: string, idx: number) => (
                    <div key={idx}>{log}</div>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>

        <DialogFooter className="flex justify-between border-t pt-4">
          {!importing ? (
            <div className="flex gap-2 w-full justify-between">
              <Button variant="outline" onClick={handleAnalyze} disabled={analyzing || !url}>
                {analyzing ? 'Analyzing...' : 'Analyze Website'}
              </Button>
              <div className="flex gap-2">
                <Button variant="ghost" onClick={onClose}>
                  Cancel
                </Button>
                <Button onClick={handleStartImport} disabled={!url}>
                  Start Import
                </Button>
              </div>
            </div>
          ) : (
            <Button variant="destructive" onClick={handleCancelImport}>
              <XCircle className="w-4 h-4 mr-2" />
              Cancel Crawl Job
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
