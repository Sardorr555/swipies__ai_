import { useState } from 'react';
import request from '@/utils/request';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  LucideBookOpen,
  LucideSparkles,
  LucideCopy,
  LucideDownload,
  LucideCheck,
} from 'lucide-react';
import message from '@/components/ui/message';

interface WikiData {
  project_name: string;
  title: string;
  wiki_markdown: string;
  generated_at: number;
  extracted_sections_count: number;
}

export function IntelligenceWikiBuilderView() {
  const [projectName, setProjectName] = useState('Swipies AI');
  const [loading, setLoading] = useState(false);
  const [wiki, setWiki] = useState<WikiData | null>(null);
  const [copied, setCopied] = useState(false);

  const handleBuildWiki = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!projectName.trim()) return;

    setLoading(true);
    try {
      const res = await request.post('/api/v1/intelligence/wiki/build?global=true', {
        project_name: projectName.trim(),
      });
      if (res?.data?.code === 0) {
        setWiki(res.data.data);
      }
    } catch {
      setWiki(null);
      message.error('Failed to generate wiki for the specified project.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!wiki) return;
    navigator.clipboard.writeText(wiki.wiki_markdown);
    setCopied(true);
    message.success('Wiki documentation copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!wiki) return;
    const blob = new Blob([wiki.wiki_markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${wiki.project_name.toLowerCase().replace(/\s+/g, '_')}_wiki_spec.md`;
    a.click();
    URL.revokeObjectURL(url);
    message.success('Markdown documentation file downloaded successfully!');
  };

  return (
    <div className="flex flex-col gap-6 w-full max-w-5xl mx-auto">
      {/* Header Box */}
      <div className="bg-background rounded-2xl p-6 border border-border shadow-lg space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
            <LucideBookOpen className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-bold text-xl">Autonomous Project Wiki & Documentation Builder</h3>
            <p className="text-xs text-muted-foreground">
              AI automatically synthesizes all discussions, architectural decisions, and tasks into structured Wiki documentation
            </p>
          </div>
        </div>

        <form onSubmit={handleBuildWiki} className="flex gap-3">
          <Input
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="Enter project or component name..."
            className="h-12 text-sm rounded-xl flex-1"
          />
          <Button type="submit" disabled={loading} className="h-12 px-6 font-medium gap-2">
            <LucideSparkles className="w-4 h-4" />
            {loading ? 'Building Wiki...' : 'Generate Wiki'}
          </Button>
        </form>
      </div>

      {/* Generated Wiki Render */}
      {wiki && (
        <div className="bg-background rounded-2xl p-6 border border-border space-y-4 shadow-md">
          <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-border">
            <div>
              <h4 className="font-bold text-lg text-primary">{wiki.title}</h4>
              <p className="text-xs text-muted-foreground">
                Extracted {wiki.extracted_sections_count} sections • Generated from knowledge base
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={handleCopy} className="gap-1.5 text-xs">
                {copied ? <LucideCheck className="w-3.5 h-3.5 text-emerald-400" /> : <LucideCopy className="w-3.5 h-3.5" />}
                {copied ? 'Copied' : 'Copy'}
              </Button>
              <Button size="sm" onClick={handleDownload} className="gap-1.5 text-xs">
                <LucideDownload className="w-3.5 h-3.5" />
                Download Markdown
              </Button>
            </div>
          </div>

          <div className="p-5 rounded-xl bg-muted/30 font-mono text-xs text-foreground whitespace-pre-wrap leading-relaxed border border-border">
            {wiki.wiki_markdown}
          </div>
        </div>
      )}
    </div>
  );
}
