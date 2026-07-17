import { Outlet } from 'react-router';
import { Header } from './components/header';
import { LeftSidebar } from './components/left-sidebar';
import { LicenseActivationModal } from '@/components/license-activation-modal';

export function RootLayoutContainer({ children }: React.PropsWithChildren) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg-base">
      {/* Left Sidebar on desktop */}
      <LeftSidebar className="hidden md:flex shrink-0" />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <Header className="px-5 py-4 shrink-0" />

        <main className="flex-1 min-w-0 overflow-hidden relative">
          {children}
        </main>
      </div>
      
      <LicenseActivationModal />
    </div>
  );
}

export default function RootLayout() {
  return (
    <RootLayoutContainer>
      <Outlet />
    </RootLayoutContainer>
  );
}
