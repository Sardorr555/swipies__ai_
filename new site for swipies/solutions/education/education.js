(() => {
  'use strict';
  const lang = document.documentElement.lang || 'ru';
  const i18n = window.SWIPIES_EDUCATION_I18N?.[lang] || window.SWIPIES_EDUCATION_I18N?.ru;

  // Preserve query string and hash across language switches
  document.querySelectorAll('[data-language]').forEach(link => {
    const url = new URL(link.href, location.origin);
    url.search = location.search;
    url.hash = location.hash;
    link.href = url.toString();
  });

  // Mobile menu
  const menuBtn = document.querySelector('.menu-toggle');
  const nav = document.getElementById('navigation');
  if (menuBtn && nav) {
    const closeMenu = () => {
      menuBtn.setAttribute('aria-expanded', 'false');
      menuBtn.setAttribute('aria-label', i18n?.menuOpen || 'Open menu');
      nav.classList.remove('open');
    };
    menuBtn.addEventListener('click', () => {
      const expanded = menuBtn.getAttribute('aria-expanded') === 'true';
      menuBtn.setAttribute('aria-expanded', String(!expanded));
      menuBtn.setAttribute('aria-label', !expanded ? (i18n?.menuClose || 'Close menu') : (i18n?.menuOpen || 'Open menu'));
      nav.classList.toggle('open', !expanded);
    });
    nav.addEventListener('click', e => {
      if (e.target.closest('a')) closeMenu();
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && menuBtn.getAttribute('aria-expanded') === 'true') {
        closeMenu();
        menuBtn.focus();
      }
    });
  }

  // Scenario tabs
  const tabs = [...document.querySelectorAll('[data-scenario]')];
  const chatMessages = document.getElementById('chatMessages');

  function selectScenario(index, focus = false) {
    const scenario = i18n?.scenarios?.[index];
    if (!scenario || !chatMessages) return;

    tabs.forEach((tab, i) => {
      tab.setAttribute('aria-selected', String(i === index));
      tab.tabIndex = (i === index) ? 0 : -1;
    });

    chatMessages.innerHTML = '';
    scenario.dialog.forEach(msg => {
      const bubble = document.createElement('div');
      bubble.className = `bubble ${msg.role}`;
      bubble.innerHTML = `<span class="bubble-sender">${msg.sender}</span><p>${msg.text}</p>`;
      chatMessages.appendChild(bubble);
    });

    if (focus && tabs[index]) tabs[index].focus();
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectScenario(index));
    tab.addEventListener('keydown', e => {
      let next;
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = (index + 1) % tabs.length;
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = (index + tabs.length - 1) % tabs.length;
      if (e.key === 'Home') next = 0;
      if (e.key === 'End') next = tabs.length - 1;
      if (next !== undefined) {
        e.preventDefault();
        selectScenario(next, true);
      }
    });
  });

  // Initial selection
  selectScenario(0);
})();
