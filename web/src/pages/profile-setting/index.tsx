import { PageHeader } from '@/components/page-header';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { useNavigatePage } from '@/hooks/logic-hooks/navigate-hooks';
import { House } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Outlet } from 'umi';
import { SideBar } from './sidebar';

export default function ProfileSetting() {
  const { navigateToHome } = useNavigatePage();
  const { t } = useTranslation();

  return (
    <div className="flex flex-col w-full min-h-screen h-screen bg-background text-foreground overflow-x-hidden">
      <PageHeader>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink onClick={navigateToHome}>
                <House className="w-3 h-3 sm:w-4 sm:h-4" />
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage className="text-sm sm:text-base">{t('setting.profile')}</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </PageHeader>

      <div className="flex flex-col sm:flex-row flex-1 bg-muted/50 w-full">
        <SideBar></SideBar>

        <main className="flex-1 w-full overflow-y-auto p-4 sm:p-6 md:p-8">
          <Outlet></Outlet>
        </main>
      </div>
    </div>
  );
}
