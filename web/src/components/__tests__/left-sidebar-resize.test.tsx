import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  LeftSidebar,
  SIDEBAR_WIDTH_KEY,
  SIDEBAR_COLLAPSED_KEY,
  DEFAULT_SIDEBAR_WIDTH,
  COLLAPSED_SIDEBAR_WIDTH,
} from '../../layouts/components/left-sidebar';

// Mock react-router
jest.mock('react-router', () => {
  const ReactLib = jest.requireActual('react');
  return {
    Link: ReactLib.forwardRef(({ to, children, ...props }: any, ref: any) => (
      <a href={to} ref={ref} {...props}>
        {children}
      </a>
    )),
    useLocation: () => ({ pathname: '/' }),
  };
});

// Mock routes
jest.mock('@/routes', () => ({
  Routes: {
    Root: '/',
    Datasets: '/datasets',
    DatasetBase: '/dataset',
    Chats: '/chats',
    Chat: '/chat',
    Searches: '/searches',
    Search: '/search',
    Agents: '/agents',
    AgentTemplates: '/agent-templates',
    Memories: '/memories',
    Memory: '/memory',
    MemoryMessage: '/memory-message',
    Files: '/files',
  },
}));

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        'header.home': 'Home',
        'header.dataset': 'Datasets',
        'header.chat': 'Chat',
        'header.search': 'Search',
        'header.flow': 'Agents',
        'header.memories': 'Memories',
        'header.fileManager': 'Files',
      };
      return map[key] || key;
    },
  }),
}));

describe('LeftSidebar Resizable and Collapsible Test Suite', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  const renderSidebar = () => render(<LeftSidebar />);

  it('renders expanded sidebar by default with default width 220px', () => {
    const { container } = renderSidebar();
    const aside = container.querySelector('aside');
    expect(aside).toBeInTheDocument();
    expect(aside?.style.width).toBe(`${DEFAULT_SIDEBAR_WIDTH}px`);

    expect(screen.getByText('Swipies')).toBeInTheDocument();
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Datasets')).toBeInTheDocument();
    expect(screen.getByText('Chat')).toBeInTheDocument();
  });

  it('collapses into icon-only mode when clicking collapse button', () => {
    const { container } = renderSidebar();
    const aside = container.querySelector('aside');
    expect(aside?.style.width).toBe(`${DEFAULT_SIDEBAR_WIDTH}px`);

    // Click collapse button
    const collapseBtn = screen.getByTitle('Свернуть боковую панель');
    fireEvent.click(collapseBtn);

    expect(aside?.style.width).toBe(`${COLLAPSED_SIDEBAR_WIDTH}px`);
    expect(localStorage.getItem(SIDEBAR_COLLAPSED_KEY)).toBe('true');

    // Logo text "Swipies" is hidden
    expect(screen.queryByText('Swipies')).not.toBeInTheDocument();

    // Expand button is now visible
    const expandBtn = screen.getByTitle('Развернуть боковую панель');
    expect(expandBtn).toBeInTheDocument();

    // Click expand button to restore
    fireEvent.click(expandBtn);
    expect(aside?.style.width).toBe(`${DEFAULT_SIDEBAR_WIDTH}px`);
    expect(localStorage.getItem(SIDEBAR_COLLAPSED_KEY)).toBe('false');
  });

  it('toggles collapse on separator double-click', () => {
    const { container } = renderSidebar();
    const aside = container.querySelector('aside');
    const separator = screen.getByRole('separator');

    // Double click to collapse
    fireEvent.doubleClick(separator);
    expect(aside?.style.width).toBe(`${COLLAPSED_SIDEBAR_WIDTH}px`);

    // Double click to expand
    fireEvent.doubleClick(separator);
    expect(aside?.style.width).toBe(`${DEFAULT_SIDEBAR_WIDTH}px`);
  });

  it('resizes sidebar via mouse drag', () => {
    const { container } = renderSidebar();
    const aside = container.querySelector('aside');
    const separator = screen.getByRole('separator');

    // Start dragging
    fireEvent.mouseDown(separator);

    // Move mouse to 300px
    fireEvent.mouseMove(document, { clientX: 300 });
    expect(aside?.style.width).toBe('300px');

    // Release mouse
    fireEvent.mouseUp(document);

    expect(localStorage.getItem(SIDEBAR_WIDTH_KEY)).toBe('300');
  });

  it('snaps to collapsed mode when dragged below collapse threshold', () => {
    const { container } = renderSidebar();
    const aside = container.querySelector('aside');
    const separator = screen.getByRole('separator');

    // Start dragging
    fireEvent.mouseDown(separator);

    // Drag far to the left (e.g. 50px)
    fireEvent.mouseMove(document, { clientX: 50 });
    expect(aside?.style.width).toBe(`${COLLAPSED_SIDEBAR_WIDTH}px`);

    // Release mouse
    fireEvent.mouseUp(document);
    expect(localStorage.getItem(SIDEBAR_COLLAPSED_KEY)).toBe('true');
  });

  it('restores saved width and collapsed state from localStorage', () => {
    localStorage.setItem(SIDEBAR_WIDTH_KEY, '350');
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, 'false');

    const { container } = renderSidebar();
    const aside = container.querySelector('aside');
    expect(aside?.style.width).toBe('350px');
  });
});
