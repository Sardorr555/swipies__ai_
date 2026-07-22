import { BRAND } from '@/constants/branding';
import { useTranslation } from 'react-i18next';
import { ShieldCheck, Server, Lock, Bot } from 'lucide-react';
import './index.less';

const PrivacyPolicy = () => {
  const { t } = useTranslation('translation', { keyPrefix: 'privacyPolicy' });

  return (
    <div className="privacy-policy-page">
      <div className="privacy-policy-container">
        <div className="privacy-policy-header">
          <div className="header-brand">
            <img src="/logo.svg" alt="logo" className="w-8 h-8 mr-3" />
            <span className="brand-name">{BRAND.name}</span>
          </div>
          <div className="header-title-tag">
            Enterprise SLA & Data Policy
          </div>
        </div>

        <div className="privacy-policy-content">
          <h1 className="policy-title">{t('title')}</h1>
          <p className="policy-effective-date">{t('effectiveDate')}: 22.07.2026</p>

          {/* SLA Key Feature Badges */}
          <div className="policy-sla-badges grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
            <div className="sla-badge flex items-center p-3 rounded-lg border border-border bg-card/60">
              <Server className="w-5 h-5 text-primary mr-2.5 shrink-0" />
              <span className="text-xs font-semibold">{t('slaBadge1', '99.9% Uptime SLA')}</span>
            </div>
            <div className="sla-badge flex items-center p-3 rounded-lg border border-border bg-card/60">
              <Lock className="w-5 h-5 text-primary mr-2.5 shrink-0" />
              <span className="text-xs font-semibold">{t('slaBadge2', 'AES-256 Encryption')}</span>
            </div>
            <div className="sla-badge flex items-center p-3 rounded-lg border border-border bg-card/60">
              <ShieldCheck className="w-5 h-5 text-primary mr-2.5 shrink-0" />
              <span className="text-xs font-semibold">{t('slaBadge3', 'Multi-Tenant Isolation')}</span>
            </div>
            <div className="sla-badge flex items-center p-3 rounded-lg border border-border bg-card/60">
              <Bot className="w-5 h-5 text-primary mr-2.5 shrink-0" />
              <span className="text-xs font-semibold">{t('slaBadge4', 'Zero AI Training')}</span>
            </div>
          </div>

          {/* Section 1 */}
          <section className="policy-section">
            <h2>{t('section1Title')}</h2>
            <p>{t('section1Text')}</p>
          </section>

          {/* Section 2 */}
          <section className="policy-section">
            <h2>{t('section2Title')}</h2>
            <p>{t('section2Text')}</p>
            <ul>
              <li>{t('section2Item1')}</li>
              <li>{t('section2Item2')}</li>
              <li>{t('section2Item3')}</li>
              <li>{t('section2Item4')}</li>
              {t('section2Item5') && <li>{t('section2Item5')}</li>}
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
          <section className="policy-section">
            <h2>{t('section4Title')}</h2>
            <p>{t('section4Text')}</p>
          </section>

          {/* Section 5 */}
          <section className="policy-section">
            <h2>{t('section5Title')}</h2>
            <p>{t('section5Text')}</p>
            {t('section5Item1') && (
              <ul>
                <li>{t('section5Item1')}</li>
                <li>{t('section5Item2')}</li>
                <li>{t('section5Item3')}</li>
              </ul>
            )}
          </section>

          {/* Section 6 */}
          <section className="policy-section">
            <h2>{t('section6Title')}</h2>
            <p>{t('section6Text')}</p>
            {t('section6Item1') && (
              <ul>
                <li>{t('section6Item1')}</li>
                <li>{t('section6Item2')}</li>
              </ul>
            )}
          </section>

          {/* Section 7 */}
          <section className="policy-section">
            <h2>{t('section7Title')}</h2>
            <p>{t('section7Text')}</p>
            {t('section7Item1') && (
              <ul>
                <li>{t('section7Item1')}</li>
                <li>{t('section7Item2')}</li>
                <li>{t('section7Item3')}</li>
              </ul>
            )}
          </section>

          {/* Section 8 */}
          <section className="policy-section">
            <h2>{t('section8Title')}</h2>
            <p>{t('section8Text')}</p>
          </section>

          {/* Section 9 */}
          <section className="policy-section">
            <h2>{t('section9Title')}</h2>
            <p>{t('section9Text')}</p>
            {t('section9Item1') && (
              <ul>
                <li>{t('section9Item1')}</li>
                <li>{t('section9Item2')}</li>
                <li>{t('section9Item3')}</li>
                <li>{t('section9Item4')}</li>
              </ul>
            )}
          </section>

          {/* Section 10 */}
          <section className="policy-section">
            <h2>{t('section10Title')}</h2>
            <p>{t('section10Text')}</p>
          </section>

          {/* Section 11 */}
          <section className="policy-section">
            <h2>{t('section11Title')}</h2>
            <p>{t('section11Text')}</p>
          </section>

          {/* Section 12 */}
          <section className="policy-section">
            <h2>{t('section12Title')}</h2>
            <p>{t('section12Text')}</p>
          </section>

          {/* Section 13 */}
          <section className="policy-section">
            <h2>{t('section13Title')}</h2>
            <p>{t('section13Text')}</p>
          </section>

          {/* Section 14 */}
          <section className="policy-section">
            <h2>{t('section14Title')}</h2>
            <p>{t('section14Text')}</p>
          </section>

          {/* Section 15 */}
          <section className="policy-section">
            <h2>{t('section15Title')}</h2>
            <p>{t('section15Text', { email: 'support@swipies.io' })}</p>
          </section>
        </div>
      </div>
    </div>
  );
};

export default PrivacyPolicy;
