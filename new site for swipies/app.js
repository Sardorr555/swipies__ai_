/* Swipies AI — App Logic */
/* SVG icon helpers */
const icons = {
  shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
  brain: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z"/><line x1="9" y1="21" x2="15" y2="21"/></svg>',
  lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
  server: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>',
  database: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
  cpu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>',
  tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
  mail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 7L2 7"/></svg>',
  phone: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
  pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
  layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
  building: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="2" width="16" height="20" rx="1"/><line x1="9" y1="6" x2="10" y2="6"/><line x1="14" y1="6" x2="15" y2="6"/><line x1="9" y1="10" x2="10" y2="10"/><line x1="14" y1="10" x2="15" y2="10"/><line x1="9" y1="14" x2="10" y2="14"/><line x1="14" y1="14" x2="15" y2="14"/><path d="M9 18h6v4H9z"/></svg>',
  scale: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 3h5v5"/><path d="M8 3H3v5"/><path d="M12 22V8"/><path d="M21 3l-9 9"/><path d="M3 3l9 9"/></svg>',
};

/* Render all sections */
document.getElementById('app-sections').innerHTML = `
<!-- PROBLEM -->
<section id="problem">
<div class="container reveal">
<div class="section-num" data-i18n="prob_num">01 — The Problem</div>
<h2 class="section-title" data-i18n="prob_title">Why Standard AI Fails Enterprise</h2>
<div class="problem-grid">
<div class="problem-card"><div class="card-icon">${icons.shield}</div><h3 data-i18n="prob1_h">Data Leaves Your Perimeter</h3><p data-i18n="prob1_p">Every API call to external AI providers sends your proprietary data to third-party servers — a compliance nightmare.</p></div>
<div class="problem-card"><div class="card-icon">${icons.brain}</div><h3 data-i18n="prob2_h">Generic AI, Zero Context</h3><p data-i18n="prob2_p">Public models don't understand your business data, documents, or internal knowledge. Answers are shallow and unreliable.</p></div>
<div class="problem-card"><div class="card-icon">${icons.lock}</div><h3 data-i18n="prob3_h">No Control Over Stack</h3><p data-i18n="prob3_p">You can't control the model version, uptime, infrastructure, or update cadence. Your AI is someone else's decision.</p></div>
</div>
</div>
</section>

<!-- SOLUTION -->
<section id="solution">
<div class="container reveal">
<div class="section-num" data-i18n="sol_num">02 — The Solution</div>
<h2 class="section-title" data-i18n="sol_title">On-Premise RAG That Runs on Your Servers</h2>
<p class="section-subtitle" data-i18n="sol_sub">Swipies AI deploys the full AI infrastructure inside your environment. Complete data sovereignty, zero external dependencies.</p>
<div class="feature-grid">
<div class="feature-card"><div class="card-icon">${icons.server}</div><h3 data-i18n="sol1_h">On-Premise RAG Deployment</h3><p data-i18n="sol1_p">Full RAG pipeline — document ingestion, vector indexing, retrieval, and generation — deployed directly on your servers. Built on battle-tested RAGFlow architecture.</p></div>
<div class="feature-card"><div class="card-icon">${icons.database}</div><h3 data-i18n="sol2_h">Works With Your Data</h3><p data-i18n="sol2_p">Connect your existing documents, databases, CRM records, and internal tools. The knowledge base is built from your real data — not generic training sets.</p></div>
<div class="feature-card"><div class="card-icon">${icons.cpu}</div><h3 data-i18n="sol3_h">Any LLM, Your Choice</h3><p data-i18n="sol3_p">Support for OpenAI, Anthropic Claude, xAI Grok, and fully local models via Ollama. Switch models without changing infrastructure.</p></div>
<div class="feature-card"><div class="card-icon">${icons.tag}</div><h3 data-i18n="sol4_h">Full White-Label for SaaS</h3><p data-i18n="sol4_p">Embed Swipies AI into your own product under your brand. Offer AI-powered features to your clients — powered by their data, on your infrastructure.</p></div>
<div class="feature-card"><div class="card-icon">${icons.pin}</div><h3 data-i18n="sol5_h">Uzbekistan Local Deployment</h3><p data-i18n="sol5_p">Deploy AI models on secure high-performance servers physically located within the Republic of Uzbekistan, ensuring compliance with local data localization laws.</p></div>
</div>
</div>
</section>

<!-- HOW IT WORKS -->
<section id="how">
<div class="container reveal">
<div class="section-num" data-i18n="how_num">03 — How It Works</div>
<h2 class="section-title" data-i18n="how_title">Deployed in 10 Business Days</h2>
<div class="steps-list">
<div class="step-row"><div class="step-num">01</div><h3 data-i18n="how1_h">Infrastructure Audit</h3><p data-i18n="how1_p">We audit your servers, data sources, and security requirements to design the optimal deployment architecture.</p></div>
<div class="step-row"><div class="step-num">02</div><h3 data-i18n="how2_h">Deploy RAG + LLM</h3><p data-i18n="how2_p">We deploy the full RAG pipeline and LLM of your choice directly on your infrastructure. Within 10 business days.</p></div>
<div class="step-row"><div class="step-num">03</div><h3 data-i18n="how3_h">Your Team Goes Live</h3><p data-i18n="how3_p">Your team and clients get enterprise-grade AI — fully private, fully controlled, fully yours. Data stays with you.</p></div>
</div>
</div>
</section>

<!-- USE CASES -->
<section id="cases">
<div class="container reveal">
<div class="section-num" data-i18n="cases_num">04 — Use Cases</div>
<h2 class="section-title" data-i18n="cases_title">Built for Industries That Can't Compromise on Data</h2>
<div class="usecase-grid">
<div class="usecase-card"><div class="card-label" data-i18n="case1_label">SaaS / ERP Platforms</div><h3 data-i18n="case1_h">Embed AI Into Your Product</h3><p data-i18n="case1_p">White-label Swipies AI and offer AI-powered features to your own clients. OEM model — your brand, your infrastructure, your clients' data stays private.</p></div>
<div class="usecase-card"><div class="card-label" data-i18n="case2_label">Banks & Finance</div><h3 data-i18n="case2_h">AI on Confidential Data</h3><p data-i18n="case2_p">Deploy AI over transaction records, client profiles, and financial documents. Full regulatory compliance — data never leaves your banking infrastructure.</p></div>
<div class="usecase-card"><div class="card-label" data-i18n="case3_label">Legal & Compliance</div><h3 data-i18n="case3_h">AI Over Case Files & Contracts</h3><p data-i18n="case3_p">Search, summarize, and analyze case law, contracts, and compliance documents with AI that runs entirely within your secure environment.</p></div>
<div class="usecase-card"><div class="card-label" data-i18n="case4_label">Large Enterprises</div><h3 data-i18n="case4_h">Internal Knowledge Base AI</h3><p data-i18n="case4_p">Give every employee instant access to company documentation, HR policies, technical manuals, and institutional knowledge via private AI.</p></div>
</div>
</div>
</section>

<!-- PARTNERS -->
<section id="partners">
<div class="container reveal">
<div class="section-num" data-i18n="partners_num">05 — Partners</div>
<h2 class="section-title" data-i18n="partners_title">Trusted By</h2>
<div class="partners-row">
<a href="https://kpi.com" target="_blank" class="partner-badge anchor">KPI.com — Enterprise ERP/CRM</a>
<span class="partner-badge">OpenAI — GPT Models</span>
<span class="partner-badge">Anthropic — Claude</span>
<span class="partner-badge">xAI — Grok</span>
<span class="partner-badge">Ollama — Local LLMs</span>
</div>
</div>
</section>

<!-- PRICING -->
<section id="pricing">
<div class="container reveal">
<div class="section-num" data-i18n="price_num">06 — Pricing</div>
<h2 class="section-title" data-i18n="price_title">Flexible Deployment Options</h2>
<div class="pricing-grid">
<div class="price-card">
<div class="price-name" data-i18n="starter">Starter</div>
<div class="price-amount"><span data-i18n="starter_price">$40</span><span data-i18n="starter_period">/month</span></div>
<p class="price-desc" data-i18n="starter_desc">For small teams & companies. Full AI functionality running securely on Swipies managed cloud infrastructure.</p>
<ul class="price-features">
<li>${icons.check}<span data-i18n="starter_f1">Cloud deployment</span></li>
<li>${icons.check}<span data-i18n="starter_f2">Full RAG pipeline</span></li>
<li>${icons.check}<span data-i18n="starter_f3">Standard support</span></li>
<li>${icons.check}<span data-i18n="starter_f4">Managed infrastructure</span></li>
</ul>
<a href="https://app.swipies.app/login" target="_blank" class="btn-secondary" style="display:inline-block;text-align:center" data-i18n="starter_cta">Start Building</a>
</div>
<div class="price-card">
<div class="price-name" data-i18n="license">Self-Hosted License</div>
<div class="price-amount"><span data-i18n="license_price">From $190</span><span data-i18n="license_period">/month</span></div>
<p class="price-desc" data-i18n="license_desc">Purchase a license key and run Swipies AI on your own infrastructure. You install, we power up.</p>
<ul class="price-features">
<li>${icons.check}<span data-i18n="license_f1">Self-hosted (Docker/k8s)</span></li>
<li>${icons.check}<span data-i18n="license_f2">Activate via License Key</span></li>
<li>${icons.check}<span data-i18n="license_f3">No ingestion or team limits</span></li>
<li>${icons.check}<span data-i18n="license_f4">GPU & Vector acceleration</span></li>
<li>${icons.check}<span data-i18n="license_f5">Offline / Air-gapped mode</span></li>
<li>${icons.check}<span data-i18n="license_f6">Regular updates</span></li>
</ul>
<a href="https://app.swipies.app/login" target="_blank" class="btn-primary" style="display:inline-block;text-align:center" data-i18n="license_cta">Purchase Key</a>
</div>
<div class="price-card featured">
<div class="price-name" data-i18n="enterprise">Enterprise</div>
<div class="price-amount"><span data-i18n="ent_price">From $700</span><span data-i18n="ent_period">/month</span></div>
<p class="price-desc" data-i18n="ent_desc">Custom-scoped based on your infrastructure and data volume requirements.</p>
<ul class="price-features">
<li>${icons.check}<span data-i18n="ent_f1">On-premise deployment</span></li>
<li>${icons.check}<span data-i18n="ent_f2">Custom LLM config</span></li>
<li>${icons.check}<span data-i18n="ent_f3">Dedicated support</span></li>
<li>${icons.check}<span data-i18n="ent_f4">White-label option</span></li>
<li>${icons.check}<span data-i18n="ent_f5">SLA guarantee</span></li>
<li>${icons.check}<span data-i18n="ent_f6">Data sovereignty</span></li>
</ul>
<a href="#contact" class="btn-primary" style="display:inline-block;text-align:center" data-i18n="ent_cta">Get a Custom Quote</a>
</div>
</div>
</div>
</section>

<!-- FAQ -->
<section id="faq">
<div class="container reveal">
<div class="section-num" data-i18n="faq_num">07 — FAQ</div>
<h2 class="section-title" data-i18n="faq_title">Frequently Asked Questions</h2>
<div class="faq-list">
<div class="faq-item"><button class="faq-question" data-i18n="faq1_q">Does our data leave our servers?${icons.plus}</button><div class="faq-answer"><div class="faq-answer-inner" data-i18n="faq1_a">No, never. Swipies AI is deployed entirely on your own infrastructure. Your documents, databases, and queries stay within your environment. No data is sent to any external servers or third-party APIs.</div></div></div>
<div class="faq-item"><button class="faq-question" data-i18n="faq2_q">How long does deployment take?${icons.plus}</button><div class="faq-answer"><div class="faq-answer-inner" data-i18n="faq2_a">Typical deployment takes 10 business days from kick-off. This includes infrastructure audit, RAG pipeline setup, LLM configuration, testing, and going live with your team.</div></div></div>
<div class="faq-item"><button class="faq-question" data-i18n="faq3_q">Which LLMs do you support?${icons.plus}</button><div class="faq-answer"><div class="faq-answer-inner" data-i18n="faq3_a">We support OpenAI (GPT-4, GPT-4o), Anthropic (Claude 3, Claude 3.5), xAI (Grok), and fully local models via Ollama. You can switch models at any time without re-deploying the infrastructure.</div></div></div>
<div class="faq-item"><button class="faq-question" data-i18n="faq4_q">Do you offer white-label for our product?${icons.plus}</button><div class="faq-answer"><div class="faq-answer-inner" data-i18n="faq4_a">Yes. SaaS and ERP companies can embed Swipies AI under their own brand. Your clients interact with AI that feels native to your product — while all data stays on your servers.</div></div></div>
<div class="faq-item"><button class="faq-question" data-i18n="faq5_q">What is RAG and why does it matter?${icons.plus}</button><div class="faq-answer"><div class="faq-answer-inner" data-i18n="faq5_a">RAG (Retrieval-Augmented Generation) is a technique where AI retrieves relevant information from your specific data before generating an answer. Unlike generic AI, RAG ensures responses are grounded in your actual documents and knowledge — making it accurate, relevant, and trustworthy for enterprise use.</div></div></div>
<div class="faq-item"><button class="faq-question" data-i18n="faq6_q">How does the self-hosted license work?${icons.plus}</button><div class="faq-answer"><div class="faq-answer-inner" data-i18n="faq6_a">You can download our Docker Compose or Kubernetes Helm charts, install Swipies AI on your local servers, and enter the purchased license key in the web interface. This unlocks the full platform capability, removes limits, and enables offline operation without external internet connection.</div></div></div>
<div class="faq-item"><button class="faq-question" data-i18n="faq7_q">Can we deploy AI models on servers in Uzbekistan?${icons.plus}</button><div class="faq-answer"><div class="faq-answer-inner" data-i18n="faq7_a">Yes, absolutely. We support deploying LLMs and RAG pipelines directly on servers located in Uzbekistan. This ensures 100% compliance with local data localization laws (such as Article 27.1 of the Law of the Republic of Uzbekistan 'On Personal Data'), keeping all sensitive data inside the national border.</div></div></div>
</div>
</div>
</section>

<!-- CONTACT -->
<section id="contact">
<div class="container reveal">
<div class="section-num" data-i18n="contact_num">08 — Contact</div>
<h2 class="section-title" data-i18n="contact_title">Let's Talk About Your Deployment</h2>
<div class="contact-grid">
<form class="contact-form" id="contactForm" onsubmit="return handleSubmit(event)">
<div class="form-row">
<div class="form-group"><label data-i18n="form_company">Company Name</label><input type="text" id="f-company" required></div>
<div class="form-group"><label data-i18n="form_name">Full Name</label><input type="text" id="f-name" required></div>
</div>
<div class="form-row">
<div class="form-group"><label data-i18n="form_email">Email</label><input type="email" id="f-email" required></div>
<div class="form-group"><label data-i18n="form_phone">Phone</label><input type="tel" id="f-phone"></div>
</div>
<div class="form-group"><label data-i18n="form_msg">Message</label><textarea id="f-msg" rows="4"></textarea></div>
<button type="submit" class="btn-primary" data-i18n="form_submit">Send Message</button>
</form>
<div class="contact-info">
<div class="contact-info-item">${icons.mail}<div><div class="ci-label" data-i18n="ci_email">Email</div><div class="ci-value">albakiev.sardobek@gmail.com</div></div></div>
<div class="contact-info-item">${icons.phone}<div><div class="ci-label" data-i18n="ci_phone">Phone</div><div class="ci-value">+998 (90) 625-3986</div></div></div>
<div class="contact-info-item">${icons.pin}<div><div class="ci-label" data-i18n="ci_location">Location</div><div class="ci-value" data-i18n="ci_loc_val">Uzbekistan, Andijan</div></div></div>
<p class="contact-note" data-i18n="ci_note">Dedicated account manager for every deployment. SLA guarantees included. Average response time: &lt; 2 hours.</p>
</div>
</div>
</div>
</section>

<!-- FOOTER CTA -->
<div class="footer-cta">
<div class="container">
<h2 data-i18n="fcta_h">Ready to Bring AI Inside Your Infrastructure?</h2>
<p data-i18n="fcta_p">Deploy enterprise-grade AI on your servers. Your data stays yours.</p>
<a href="https://app.swipies.app/login" target="_blank" class="btn-primary" data-i18n="hero_cta1">Try Demo</a>
</div>
</div>

<!-- FOOTER -->
<footer class="footer">
<div class="container">
<div class="footer-grid">
<div class="footer-brand"><div class="nav-logo">Swipies<span>AI</span></div><p data-i18n="footer_desc">Enterprise on-premise AI platform. Deploy RAG pipelines on your own servers with complete data sovereignty.</p><p class="muted" style="margin-top:0.5rem;font-size:var(--t-small)">Uzbekistan, Andijan · +998 (90) 625-3986</p></div>
<div class="footer-col"><h4 data-i18n="footer_platform">Platform</h4><a href="#solution" data-i18n="nav_solution">Solution</a><a href="#how" data-i18n="nav_how">How It Works</a><a href="#cases" data-i18n="nav_cases">Use Cases</a><a href="#pricing" data-i18n="nav_pricing">Pricing</a><a href="https://swipies.app/tutorials.html" target="_blank" data-i18n="footer_tutorials">Tutorials</a></div>
<div class="footer-col"><h4 data-i18n="footer_company">Company</h4><a href="terms.html" data-i18n="footer_terms">Terms of Use</a><a href="privacy.html" data-i18n="footer_privacy">Privacy Policy</a><a href="https://help.swipies.app/docs/dev/" target="_blank" data-i18n="footer_docs">Documentation</a></div>
<div class="footer-col"><h4 data-i18n="footer_connect">Connect</h4><a href="mailto:albakiev.sardobek@gmail.com">Email</a><a href="https://github.com/Sardorr555/swipies__ai_" target="_blank">GitHub</a></div>
</div>
<div class="footer-bottom"><p data-i18n="footer_copy">© 2025 Swipies AI. All rights reserved.</p></div>
</footer>
\`;

/* ===== STATE & LANGUAGE INTERACTIVE SYSTEM ===== */
let currentLang = 'en';

function setLanguage(lang) {
  if (!T[lang]) return;
  currentLang = lang;
  
  // Update buttons
  document.querySelectorAll('#langSwitch button').forEach(btn => {
    if (btn.getAttribute('data-lang') === lang) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Update DOM translations
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (T[lang][key]) {
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        el.placeholder = T[lang][key];
      } else {
        const svg = el.querySelector('svg');
        if (svg) {
          el.textContent = T[lang][key];
          el.appendChild(svg);
        } else {
          el.textContent = T[lang][key];
        }
      }
    }
  });

  // Save selection
  localStorage.setItem('swipies_lang', lang);

  updateAuthStatus();
}

function updateAuthStatus() {
  const isLoggedIn = !!(localStorage.getItem('Authorization') && (localStorage.getItem('UserInfo') || localStorage.getItem('userInfo') || localStorage.getItem('token')));
  const savedLang = localStorage.getItem('swipies_lang') || 'en';

  const consoleTexts = {
    en: 'Go to Console',
    ru: 'Панель управления',
    uz: 'Konsolga o‘tish'
  };

  document.querySelectorAll('[data-i18n="nav_cta"]').forEach(el => {
    if (isLoggedIn) {
      el.textContent = consoleTexts[savedLang] || 'Console';
      el.href = 'https://app.swipies.app/';
      el.target = '_self';
    } else {
      el.textContent = T[savedLang].nav_cta;
      el.href = 'login.html';
      el.target = '_self';
    }
  });

  document.querySelectorAll('[data-i18n="hero_cta1"]').forEach(el => {
    if (isLoggedIn) {
      el.textContent = consoleTexts[savedLang] || 'Console';
      el.href = 'https://app.swipies.app/';
      el.target = '_self';
    } else {
      el.textContent = T[savedLang].hero_cta1;
      el.href = 'login.html';
      el.target = '_self';
    }
  });

  const starterBtn = document.querySelector('[data-i18n="starter_cta"]');
  if (starterBtn) {
    if (isLoggedIn) {
      starterBtn.href = 'https://app.swipies.app/pricing?plan=plus';
      starterBtn.target = '_self';
    } else {
      starterBtn.href = 'https://app.swipies.app/login?redirect=%2Fpricing%3Fplan%3Dplus';
      starterBtn.target = '_self';
    }
  }

  const licenseBtn = document.querySelector('[data-i18n="license_cta"]');
  if (licenseBtn) {
    if (isLoggedIn) {
      licenseBtn.href = 'https://app.swipies.app/pricing?plan=license';
      licenseBtn.target = '_self';
    } else {
      licenseBtn.href = 'https://app.swipies.app/login?redirect=%2Fpricing%3Fplan%3Dlicense';
      licenseBtn.target = '_self';
    }
  }
}

// Language Switch Event Listeners
document.getElementById('langSwitch').addEventListener('click', (e) => {
  const btn = e.target.closest('button');
  if (btn) {
    const lang = btn.getAttribute('data-lang');
    setLanguage(lang);
  }
});

/* ===== FAQ ACCORDION INTERACTIVITY ===== */
document.querySelectorAll('.faq-question').forEach(button => {
  button.addEventListener('click', () => {
    const item = button.parentElement;
    const answer = item.querySelector('.faq-answer');
    
    const isOpen = item.classList.contains('open');
    
    document.querySelectorAll('.faq-item').forEach(el => {
      el.classList.remove('open');
      el.querySelector('.faq-answer').style.maxHeight = null;
    });

    if (!isOpen) {
      item.classList.add('open');
      answer.style.maxHeight = answer.scrollHeight + 'px';
    }
  });
});

/* ===== MOBILE NAVIGATION ===== */
const hamburger = document.getElementById('hamburger');
const mobileMenu = document.getElementById('mobileMenu');
const navLinks = document.getElementById('navLinks');

// Populate mobile menu from navLinks
mobileMenu.innerHTML = navLinks.innerHTML;

// Add Try Demo CTA button to mobile menu bottom
const mobileCta = document.createElement('a');
mobileCta.href = 'https://app.swipies.app/login';
mobileCta.target = '_blank';
mobileCta.className = 'btn-primary';
mobileCta.style.textAlign = 'center';
mobileCta.style.marginTop = '1rem';
mobileCta.setAttribute('data-i18n', 'nav_cta');
mobileCta.textContent = T[currentLang].nav_cta;
mobileMenu.appendChild(mobileCta);
updateAuthStatus();

// Toggle mobile menu
hamburger.addEventListener('click', () => {
  const isOpen = mobileMenu.classList.contains('open');
  if (isOpen) {
    mobileMenu.classList.remove('open');
    hamburger.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`;
  } else {
    mobileMenu.classList.add('open');
    hamburger.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
  }
});

// Close mobile menu on link click
mobileMenu.addEventListener('click', (e) => {
  if (e.target.tagName === 'A') {
    mobileMenu.classList.remove('open');
    hamburger.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`;
  }
});

/* ===== CONTACT FORM SUBMISSION WITH VALIDATION ===== */
window.handleSubmit = function(event) {
  event.preventDefault();
  
  const company = document.getElementById('f-company');
  const name = document.getElementById('f-name');
  const email = document.getElementById('f-email');
  const phone = document.getElementById('f-phone');
  const msg = document.getElementById('f-msg');
  
  let isValid = true;
  
  [company, name, email].forEach(input => {
    if (!input.value.trim()) {
      input.classList.add('error');
      isValid = false;
    } else {
      input.classList.remove('error');
    }
  });

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email.value.trim())) {
    email.classList.add('error');
    isValid = false;
  }
  
  if (!isValid) return false;
  
  const submitBtn = event.target.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  submitBtn.style.background = 'var(--border2)';
  submitBtn.textContent = 'Sending...';
  
  fetch('/api/leads', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      company: company.value.trim(),
      name: name.value.trim(),
      email: email.value.trim(),
      phone: phone.value.trim(),
      message: msg.value.trim()
    })
  })
  .then(res => res.json())
  .then(data => {
    submitBtn.style.background = 'var(--green)';
    submitBtn.style.color = '#fff';
    submitBtn.textContent = currentLang === 'en' ? 'Success! Message Sent' : currentLang === 'ru' ? 'Успешно отправлено!' : 'Muvaffaqiyatli yuborildi!';
    
    setTimeout(() => {
      document.getElementById('contactForm').reset();
      submitBtn.disabled = false;
      submitBtn.style.background = 'var(--accent)';
      submitBtn.style.color = 'var(--bg)';
      setLanguage(currentLang);
    }, 3000);
  })
  .catch(err => {
    console.error('Submission error:', err);
    submitBtn.style.background = 'var(--red)';
    submitBtn.textContent = 'Error. Try again';
    setTimeout(() => {
      submitBtn.disabled = false;
      submitBtn.style.background = 'var(--accent)';
      submitBtn.textContent = T[currentLang].form_submit || 'Send Message';
    }, 3000);
  });
  
  return false;
};

/* ===== SCROLL REVEAL (INTERSECTION OBSERVER) ===== */
const revealCallback = (entries, observer) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
};

const revealObserver = new IntersectionObserver(revealCallback, {
  root: null,
  threshold: 0.15
});

// Since document contents are dynamic, observe once sections are loaded or use mutation observer/delay.
setTimeout(() => {
  document.querySelectorAll('.reveal').forEach(el => {
    revealObserver.observe(el);
  });
}, 200);

window.addEventListener('scroll', () => {
  const nav = document.getElementById('navbar');
  if (window.scrollY > 20) {
    nav.style.background = 'rgba(8,12,20,0.95)';
    nav.style.boxShadow = '0 10px 30px -10px rgba(0,0,0,0.5)';
  } else {
    nav.style.background = 'rgba(8,12,20,0.85)';
    nav.style.boxShadow = 'none';
  }
});

/* ===== COOKIE CONSENT & VISITOR TRACKING ===== */
function getVisitorId() {
  let vId = localStorage.getItem('swipies_visitor_id');
  if (!vId) {
    vId = 'v_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
    localStorage.setItem('swipies_visitor_id', vId);
  }
  return vId;
}

function trackVisitor(consentStatus) {
  try {
    const payload = {
      visitor_id: getVisitorId(),
      screen_res: window.screen ? `${window.screen.width}x${window.screen.height}` : '',
      language: navigator.language || navigator.userLanguage || 'en',
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
      page_url: window.location.href,
      referrer: document.referrer || 'Direct',
      cookie_consent: consentStatus || 'accepted',
      user_agent: navigator.userAgent
    };

    fetch('/api/visitors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).catch(err => console.error('[Telemetry] Visitor tracking error:', err));
  } catch (err) {
    console.error('[Telemetry] Error preparing visitor data:', err);
  }
}

window.handleCookieConsent = function(choice) {
  localStorage.setItem('swipies_cookie_consent', choice);
  const banner = document.getElementById('cookieBanner');
  if (banner) {
    banner.classList.remove('show');
    setTimeout(() => { banner.style.display = 'none'; }, 350);
  }
  trackVisitor(choice);
};

function initCookieBanner() {
  const consent = localStorage.getItem('swipies_cookie_consent');
  const banner = document.getElementById('cookieBanner');

  if (!consent) {
    // New visitor: show cookie banner after short delay
    setTimeout(() => {
      if (banner) {
        banner.style.display = 'block';
        setTimeout(() => banner.classList.add('show'), 50);
      }
    }, 1000);
  } else {
    // Returning visitor with existing decision: automatically log visit
    trackVisitor(consent);
  }
}

/* ===== INITIALIZE ===== */
document.addEventListener('DOMContentLoaded', () => {
  const savedLang = localStorage.getItem('swipies_lang') || 'en';
  setLanguage(savedLang);
  
  setTimeout(() => {
    const hero = document.getElementById('hero');
    if (hero) hero.classList.add('visible');
  }, 100);

  initCookieBanner();
});


