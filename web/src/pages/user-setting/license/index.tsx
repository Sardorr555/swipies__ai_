import Spotlight from '@/components/spotlight';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Key, Sparkles, Hourglass } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';

const LicensePage = () => {
  const { t } = useTranslation();

  return (
    <ProfileSettingWrapperCard
      header={
        <header className="flex flex-col gap-1">
          <h2 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
            <Key className="text-accent-primary" size={24} />
            {t('setting.license', 'License & Billing')}
          </h2>
          <p className="text-text-secondary text-sm">
            Information about commercial licensing and premium plans.
          </p>
        </header>
      }
    >
      <Spotlight />

      <div className="h-full overflow-x-hidden overflow-y-auto space-y-6 pb-8 pr-1">
        <Card className="border border-border-default bg-bg-component/40 backdrop-blur-md relative overflow-hidden p-6">
          <CardHeader className="pb-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-3 bg-accent-primary/10 rounded-full text-accent-primary">
                <Sparkles size={28} />
              </div>
              <div>
                <CardTitle className="text-xl font-bold text-text-primary">Commercial Edition (Coming Soon)</CardTitle>
                <CardDescription className="text-sm text-text-secondary">
                  We are developing a licensed enterprise version of Swipies AI.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-text-secondary text-sm leading-relaxed">
              We are working on the Commercial Edition of Swipies AI, which will offer advanced features, priority support, and custom integrations tailored for enterprise environments.
            </p>
            <div className="flex items-start gap-3 bg-bg-base/30 p-4 rounded-lg border border-border-default/50">
              <Hourglass className="text-accent-primary shrink-0 mt-0.5" size={18} />
              <div>
                <h4 className="font-semibold text-text-primary text-sm">Under Development</h4>
                <p className="text-xs text-text-secondary mt-1">
                  The license activation module and commercial version are currently in development and not ready for release. No limits are applied to your current system.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </ProfileSettingWrapperCard>
  );
};

export default LicensePage;
