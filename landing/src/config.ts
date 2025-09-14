/// <reference types="vite/client" />
export const DEMO_VIDEO_URL: string =
  import.meta.env.VITE_DEMO_VIDEO_URL ?? "https://www.youtube.com/watch?v=dQw4w9WgXcQ";



export const LINKS = {
  getStarted: import.meta.env.VITE_GET_STARTED_URL ?? "https://swipies.app/",
  social: {
    twitter: import.meta.env.VITE_TWITTER_URL ?? "#",
    github: import.meta.env.VITE_GITHUB_URL ?? "#",
    linkedin: import.meta.env.VITE_LINKEDIN_URL ?? "#",
    email: import.meta.env.VITE_SUPPORT_EMAIL ?? "albakiev.sardobek@gmail.com"
  },
  product: {
    features: import.meta.env.VITE_PRODUCT_FEATURES_URL ?? "#",
    pricing: import.meta.env.VITE_PRODUCT_PRICING_URL ?? "#",
    integrations: import.meta.env.VITE_PRODUCT_INTEGRATIONS_URL ?? "#",
    api: import.meta.env.VITE_PRODUCT_API_URL ?? "#",
    changelog: import.meta.env.VITE_PRODUCT_CHANGELOG_URL ?? "#"
  },
  support: {
    helpCenter: import.meta.env.VITE_HELP_CENTER_URL ?? "#",
    documentation: import.meta.env.VITE_DOCUMENTATION_URL ?? "#",
    tutorials: import.meta.env.VITE_TUTORIALS_URL ?? "#",
    community: import.meta.env.VITE_COMMUNITY_URL ?? "#",
    contact: import.meta.env.VITE_SUPPORT_CONTACT_URL ?? "#",
    liveChat: import.meta.env.VITE_LIVE_CHAT_URL ?? "#"
  },
  company: {
    about: import.meta.env.VITE_COMPANY_ABOUT_URL ?? "#",
    blog: import.meta.env.VITE_COMPANY_BLOG_URL ?? "#",
    careers: import.meta.env.VITE_COMPANY_CAREERS_URL ?? "#",
    press: import.meta.env.VITE_COMPANY_PRESS_URL ?? "#",
    partners: import.meta.env.VITE_COMPANY_PARTNERS_URL ?? "#"
  },
  policies: {
    privacy: import.meta.env.VITE_PRIVACY_URL ?? "#",
    terms: import.meta.env.VITE_TERMS_URL ?? "#",
    cookies: import.meta.env.VITE_COOKIES_URL ?? "#"
  },
  sales: {
    contactSales: import.meta.env.VITE_CONTACT_SALES_URL ?? ("mailto:" + (import.meta.env.VITE_SALES_EMAIL ?? "sales@example.com")),
    bookDemo: import.meta.env.VITE_BOOK_DEMO_URL ?? "#"
  },
  contact: {
    email: import.meta.env.VITE_CONTACT_EMAIL ?? "albakiev.sardobek@gmail.com",
    phone: import.meta.env.VITE_CONTACT_PHONE ?? "+998 (90) 625-3986",
    addressLine1: import.meta.env.VITE_CONTACT_ADDRESS_LINE1 ?? "Uzbekistan, Andijan"
  }
};

