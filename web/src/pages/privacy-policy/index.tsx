import { useState, useRef, useEffect, useCallback } from 'react';
import { BRAND } from '@/constants/branding';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';
import { Button } from '@/components/ui/button';
import { 
  ArrowLeft, 
  ShieldCheck, 
  ChevronUp, 
  CreditCard, 
  RotateCcw, 
  FileText, 
  Mail 
} from 'lucide-react';
import './index.less';

const PrivacyPolicy = () => {
  const { t } = useTranslation('translation', { keyPrefix: 'privacyPolicy' });
  const navigate = useNavigate();

  const [scrollProgress, setScrollProgress] = useState(0);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const pageRef = useRef<HTMLDivElement>(null);

  const updateScrollState = useCallback(() => {
    const el = pageRef.current;
    const scrollTop = el?.scrollTop || window.scrollY || document.documentElement.scrollTop || 0;
    const scrollHeight = el?.scrollHeight || document.documentElement.scrollHeight || 0;
    const clientHeight = el?.clientHeight || window.innerHeight || 0;
    const maxScroll = scrollHeight - clientHeight;
    if (maxScroll > 0) {
      setScrollProgress(Math.min(100, Math.max(0, (scrollTop / maxScroll) * 100)));
    }
    setShowScrollTop(scrollTop > 250);
  }, []);

  useEffect(() => {
    const container = pageRef.current;
    if (container) {
      container.addEventListener('scroll', updateScrollState, { passive: true });
    }
    window.addEventListener('scroll', updateScrollState, { passive: true });

    updateScrollState();

    return () => {
      if (container) {
        container.removeEventListener('scroll', updateScrollState);
      }
      window.removeEventListener('scroll', updateScrollState);
    };
  }, [updateScrollState]);

  const scrollToTop = () => {
    if (pageRef.current && pageRef.current.scrollTop > 0) {
      pageRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const scrollToId = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div 
      className="privacy-policy-page"
      ref={pageRef}
      onScroll={updateScrollState}
    >
      {/* Top Reading Scroll Progress Bar */}
      <div 
        className="fixed top-0 left-0 h-1 bg-gradient-to-r from-teal-400 via-indigo-500 to-emerald-400 z-50 transition-all duration-100 ease-out"
        style={{ width: `${scrollProgress}%` }}
      />

      {/* Floating Scroll to Top Button */}
      {showScrollTop && (
        <button
          type="button"
          onClick={scrollToTop}
          className="fixed bottom-6 right-6 p-3 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white shadow-2xl shadow-indigo-600/40 border border-indigo-400/40 transition-all duration-300 z-50 flex items-center justify-center cursor-pointer hover:scale-110 active:scale-95"
          title={t('scrollToTop', { defaultValue: 'Наверх' })}
          aria-label={t('scrollToTop', { defaultValue: 'Наверх' })}
        >
          <ChevronUp size={22} />
        </button>
      )}

      <div className="privacy-policy-container">
        <div className="privacy-policy-header">
          <Button
            variant="ghost"
            onClick={() => navigate(-1)}
            className="back-button gap-1.5"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            {t('back')}
          </Button>
          <div className="header-brand">
            <img src="/logo.svg" alt="logo" className="w-8 h-8 mr-3" />
            <span className="brand-name">{BRAND.name}</span>
          </div>
        </div>

        <div className="privacy-policy-content">
          <h1 className="policy-title">{t('title')}</h1>
          <p className="policy-effective-date">{t('effectiveDate')}: 18.06.2026</p>

          {/* Quick Navigation Scroll Anchor Chips */}
          <div className="flex items-center gap-2 overflow-x-auto pb-4 mb-8 text-xs border-b border-white/10 scrollbar-none">
            <span className="text-text-secondary font-medium shrink-0 flex items-center gap-1">
              <FileText size={13} className="text-accent-primary" /> {t('quickNav', { defaultValue: 'Быстрый переход:' })}
            </span>
            <button
              type="button"
              onClick={() => scrollToId('sec-data')}
              className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 transition-colors shrink-0 cursor-pointer"
            >
              {t('quickNavData', { defaultValue: 'Сбор данных' })}
            </button>
            <button
              type="button"
              onClick={() => scrollToId('sec-security')}
              className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 transition-colors shrink-0 cursor-pointer"
            >
              {t('quickNavSecurity', { defaultValue: 'Безопасность' })}
            </button>
            <button
              type="button"
              onClick={() => scrollToId('sec-atmos')}
              className="px-3 py-1.5 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/30 text-indigo-300 font-semibold transition-colors shrink-0 flex items-center gap-1.5 cursor-pointer"
            >
              <CreditCard size={13} /> {t('quickNavAtmos', { defaultValue: 'Оплата Atmos' })}
            </button>
            <button
              type="button"
              onClick={() => scrollToId('sec-refund')}
              className="px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 font-semibold transition-colors shrink-0 flex items-center gap-1.5 cursor-pointer"
            >
              <RotateCcw size={13} /> {t('quickNavRefund', { defaultValue: 'Возврат средств' })}
            </button>
            <button
              type="button"
              onClick={() => scrollToId('sec-contacts')}
              className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 transition-colors shrink-0 flex items-center gap-1 cursor-pointer"
            >
              <Mail size={13} /> {t('quickNavContacts', { defaultValue: 'Контакты' })}
            </button>
          </div>

          {/* Section 1 */}
          <section className="policy-section" id="sec-intro">
            <h2>{t('section1Title')}</h2>
            <p>{t('section1Text')}</p>
          </section>

          {/* Section 2 */}
          <section className="policy-section" id="sec-data">
            <h2>{t('section2Title')}</h2>
            <p>{t('section2Text')}</p>
            <ul>
              <li>{t('section2Item1')}</li>
              <li>{t('section2Item2')}</li>
              <li>{t('section2Item3')}</li>
              <li>{t('section2Item4')}</li>
            </ul>
          </section>

          {/* Section 3 */}
          <section className="policy-section">
            <h2>{t('section3Title')}</h2>
            <p>{t('section3Text')}</p>
            <ul>
              <li>{t('section3Item1')}</li>
              <li>{t('section3Item2')}</li>
              <li>{t('section3Item3')}</li>
              <li>{t('section3Item4')}</li>
              <li>{t('section3Item5')}</li>
            </ul>
          </section>

          {/* Section 4 */}
          <section className="policy-section" id="sec-security">
            <h2>{t('section4Title')}</h2>
            <p>{t('section4Text')}</p>
          </section>

          {/* Section 5 */}
          <section className="policy-section">
            <h2>{t('section5Title')}</h2>
            <p>{t('section5Text')}</p>
          </section>

          {/* Section 6 */}
          <section className="policy-section">
            <h2>{t('section6Title')}</h2>
            <p>{t('section6Text')}</p>
            <ul>
              <li>{t('section6Item1')}</li>
              <li>{t('section6Item2')}</li>
              <li>{t('section6Item3')}</li>
            </ul>
          </section>

          {/* Section 7 */}
          <section className="policy-section">
            <h2>{t('section7Title')}</h2>
            <p>{t('section7Text')}</p>
          </section>

          {/* Section 8: Atmos Payments & Security */}
          <section className="policy-section" id="sec-atmos">
            <h2>{t('section8Title')}</h2>
            <p>{t('section8Text')}</p>

            {/* Atmos Security Trust Box */}
            <div className="p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-300 my-4 space-y-2">
              <div className="flex items-center gap-2 font-bold text-sm text-indigo-400">
                <ShieldCheck size={18} />
                <span>{t('trustBoxTitle', { defaultValue: 'Платежный шлюз Atmos (atmos.uz) • Стандарт PCI DSS Level 1' })}</span>
              </div>
              <p className="text-slate-300 leading-relaxed">
                {t('trustBoxDesc', { defaultValue: 'Все онлайн-платежи защищены криптографическим шифрованием TLS/SSL 256-bit. Реквизиты банковских карт вводятся в защищенном контуре шлюза Atmos и не сохраняются серверами Swipies.' })}
              </p>
              <div className="flex flex-wrap gap-2 pt-1">
                <span className="px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-500/30 text-[11px] font-semibold text-indigo-200">Uzcard</span>
                <span className="px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-500/30 text-[11px] font-semibold text-indigo-200">HUMO</span>
                <span className="px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-500/30 text-[11px] font-semibold text-indigo-200">Visa</span>
                <span className="px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-500/30 text-[11px] font-semibold text-indigo-200">MasterCard</span>
                <span className="px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 text-[11px] font-semibold text-emerald-300">PCI DSS Level 1</span>
                <span className="px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 text-[11px] font-semibold text-emerald-300">3-D Secure / SMS OTP</span>
              </div>
            </div>

            <ul>
              <li>{t('section8Item1')}</li>
              <li>{t('section8Item2')}</li>
              <li>{t('section8Item3')}</li>
              <li>{t('section8Item4')}</li>
            </ul>
          </section>

          {/* Section 9: Digital Fulfillment & Refund Policy */}
          <section className="policy-section" id="sec-refund">
            <h2>{t('section9Title')}</h2>
            <p>{t('section9Text')}</p>
            <ul>
              <li>{t('section9Item1')}</li>
              <li>{t('section9Item2')}</li>
              <li>{t('section9Item3')}</li>
            </ul>
          </section>

          {/* Section 10: Policy Changes */}
          <section className="policy-section">
            <h2>{t('section10Title')}</h2>
            <p>{t('section10Text')}</p>
          </section>

          {/* Section 11: Contacts & Details */}
          <section className="policy-section" id="sec-contacts">
            <h2>{t('section11Title')}</h2>
            <p>{t('section11Text')}</p>
          </section>
        </div>
      </div>
    </div>
  );
};

export default PrivacyPolicy;
