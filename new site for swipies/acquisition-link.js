/* Include only in NEW solution landings; existing swipies.app is untouched. */
(() => {
  'use strict';
  const script = document.currentScript, slug = script?.dataset.landing;
  if (!/^[a-z][a-z0-9-]{0,63}$/.test(slug || '')) return;
  const keys = ['sw_campaign','utm_source','utm_medium','utm_campaign','utm_term','utm_content'];
  const current = new URLSearchParams(location.search), storageKey='swipies_acquisition_' + slug;
  let stored = {};
  // Persist marketing attribution only with the existing analytics choice.
  try {
    if (localStorage.getItem('swipies_cookie_consent') === 'accepted') {
      stored = JSON.parse(sessionStorage.getItem(storageKey) || '{}');
      if (!stored || typeof stored !== 'object' || Array.isArray(stored)) stored = {};
      if (keys.some(k => current.has(k))) {
        stored = Object.fromEntries(keys.filter(k => current.has(k)).map(k => [k,current.get(k).slice(0,160)]));
        sessionStorage.setItem(storageKey, JSON.stringify(stored));
      }
    } else sessionStorage.removeItem(storageKey);
  } catch { stored = {}; }
  function decorate(anchor) {
    const query = new URLSearchParams();
    for (const key of keys) {
      const value = current.has(key) ? current.get(key) : stored[key];
      if (typeof value === 'string' && value.length <= 160) query.set(key,value);
    }
    anchor.href = 'https://swipies.app/api/acquisition/go/' + slug + '?' + query;
  }
  document.querySelectorAll('a[data-swipies-platform]').forEach(decorate);
  for (const name of ['click','auxclick']) document.addEventListener(name, event => {
    const anchor = event.target.closest?.('a[data-swipies-platform]');
    if (anchor && !event.defaultPrevented) decorate(anchor);
  }, true);
})();
