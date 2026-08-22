// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Swipies AI Documentation',
  tagline: 'Deep Document Understanding RAG Engine',
  favicon: 'img/favicon.ico',

  url: 'https://docs.swipies.app',
  baseUrl: '/',

  onBrokenLinks: 'ignore',
  onBrokenMarkdownLinks: 'ignore',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          routeBasePath: 'docs',
          path: '../../docs',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        title: 'Swipies AI Docs',
        logo: {
          alt: 'Swipies Logo',
          src: 'img/logo.svg',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'tutorialSidebar',
            position: 'left',
            label: 'User Guides',
          },
          {
            href: 'https://app.swipies.app',
            label: 'Open App',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        copyright: `Copyright © ${new Date().getFullYear()} Swipies AI. All rights reserved.`,
      },
    }),
};

module.exports = config;
