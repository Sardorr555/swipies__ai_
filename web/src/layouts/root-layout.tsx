import { Outlet, useLocation } from 'react-router';
import { Header } from './components/header';
import { LeftSidebar } from './components/left-sidebar';

export function RootLayoutContainer({ children }: React.PropsWithChildren) {
  const { pathname } = useLocation();

  const isDetailWorkspace =
    pathname.startsWith('/dataset') ||
    pathname.startsWith('/chat/') ||
    pathname === '/chat' ||
    pathname.startsWith('/agent/') ||
    pathname === '/agent';

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg-base">
      {/* Left Sidebar on desktop */}
      {!isDetailWorkspace && (
        <LeftSidebar className="hidden md:flex shrink-0" />
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <Header className="px-5 py-4 shrink-0" />

        <main className="flex-1 min-w-0 overflow-hidden relative">
          {children}
        </main>
      </div>
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
