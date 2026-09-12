import api from '../../utils/api';

describe('Website Dataset Creation & Crawling Frontend Test Suite', () => {
  describe('API Endpoints Verification', () => {
    it('provides correct endpoint paths for website import and preview', () => {
      expect(api.websiteImportPreview).toBe('/api/v1/datasets/import/website/preview');
      expect(api.websiteImportStart).toBe('/api/v1/datasets/import/website');
      expect(api.websiteImportStatus('job_123')).toBe('/api/v1/datasets/import/job_123');
      expect(api.websiteImportCancel('job_123')).toBe('/api/v1/datasets/import/job_123');
    });
  });

  describe('Website URL Validation & Normalization', () => {
    const isValidHttpUrl = (stringUrl: string) => {
      let url;
      try {
        url = new URL(stringUrl);
      } catch {
        return false;
      }
      return url.protocol === 'http:' || url.protocol === 'https:';
    };

    const extractDomainOrTitle = (urlStr: string, pageTitle?: string): string => {
      if (pageTitle && pageTitle.trim()) {
        return pageTitle.trim();
      }
      try {
        const parsed = new URL(urlStr);
        return parsed.hostname.replace(/^www\./, '');
      } catch {
        return 'Website Dataset';
      }
    };

    it('validates URLs correctly', () => {
      expect(isValidHttpUrl('https://swipies.com')).toBe(true);
      expect(isValidHttpUrl('http://docs.example.org/guide')).toBe(true);
      expect(isValidHttpUrl('ftp://example.com')).toBe(false);
      expect(isValidHttpUrl('not-a-url')).toBe(false);
      expect(isValidHttpUrl('')).toBe(false);
    });

    it('extracts default dataset name cleanly', () => {
      expect(extractDomainOrTitle('https://docs.docker.com/engine', 'Docker Engine Documentation')).toBe('Docker Engine Documentation');
      expect(extractDomainOrTitle('https://www.github.com/features')).toBe('github.com');
      expect(extractDomainOrTitle('https://stripe.com/docs')).toBe('stripe.com');
      expect(extractDomainOrTitle('invalid-url')).toBe('Website Dataset');
    });
  });

  describe('Crawl Configuration Defaults & Constraints', () => {
    interface CrawlFormValues {
      url: string;
      name: string;
      crawl_mode: 'internal' | 'single_page' | 'sitemap' | 'recursive';
      max_pages: number;
      max_depth: number;
      extract_markdown: boolean;
      extract_tables: boolean;
      extract_images: boolean;
      clean_nav_ads: boolean;
      respect_robots: boolean;
    }

    const defaultFormValues: CrawlFormValues = {
      url: '',
      name: '',
      crawl_mode: 'recursive',
      max_pages: 50,
      max_depth: 3,
      extract_markdown: true,
      extract_tables: true,
      extract_images: true,
      clean_nav_ads: true,
      respect_robots: true,
    };

    it('has safe default values for recursive crawling', () => {
      expect(defaultFormValues.crawl_mode).toBe('recursive');
      expect(defaultFormValues.max_pages).toBe(50);
      expect(defaultFormValues.max_depth).toBe(3);
      expect(defaultFormValues.extract_markdown).toBe(true);
      expect(defaultFormValues.extract_tables).toBe(true);
      expect(defaultFormValues.clean_nav_ads).toBe(true);
      expect(defaultFormValues.respect_robots).toBe(true);
    });

    it('validates range bounds for max_pages and max_depth', () => {
      const validateBounds = (pages: number, depth: number) => {
        const pagesOk = pages >= 1 && pages <= 500;
        const depthOk = depth >= 1 && depth <= 10;
        return pagesOk && depthOk;
      };

      expect(validateBounds(50, 3)).toBe(true);
      expect(validateBounds(1, 1)).toBe(true);
      expect(validateBounds(500, 10)).toBe(true);
      expect(validateBounds(0, 3)).toBe(false);
      expect(validateBounds(501, 3)).toBe(false);
      expect(validateBounds(50, 0)).toBe(false);
      expect(validateBounds(50, 11)).toBe(false);
    });
  });

  describe('Progress and Status Calculations', () => {
    it('computes percentage correctly from pages processed and detected pages', () => {
      const calculateProgress = (processed: number, total: number) => {
        if (!total || total <= 0) return 0;
        return Math.min(100, Math.round((processed / total) * 100));
      };

      expect(calculateProgress(0, 50)).toBe(0);
      expect(calculateProgress(25, 50)).toBe(50);
      expect(calculateProgress(50, 50)).toBe(100);
      expect(calculateProgress(60, 50)).toBe(100); // capped at 100
      expect(calculateProgress(5, 0)).toBe(0);
    });

    it('handles job terminal state transitions', () => {
      type JobStatus = 'idle' | 'analyzing' | 'crawling' | 'completed' | 'cancelled' | 'failed';

      const isTerminal = (status: JobStatus) => {
        return ['completed', 'cancelled', 'failed'].includes(status);
      };

      expect(isTerminal('idle')).toBe(false);
      expect(isTerminal('analyzing')).toBe(false);
      expect(isTerminal('crawling')).toBe(false);
      expect(isTerminal('completed')).toBe(true);
      expect(isTerminal('cancelled')).toBe(true);
      expect(isTerminal('failed')).toBe(true);
    });
  });
});
