/* Hosts the platform's native floating widget; no management key is used here. */
(() => {
  'use strict';
  if (document.getElementById('swipies-support-button')) return;
  const apiOrigin = 'https://api.swipies.app';
  let buttonFrame, chatFrame, masterUrl, previousOverflow, fullscreen = false, expanded = false;
  const mobile = () => window.innerWidth <= 640;
  const sizeWindow = () => {
    if (!chatFrame) return;
    chatFrame.style.cssText = fullscreen || mobile()
      ? 'position:fixed;inset:0;width:100%;height:100%;height:100dvh;border:0;background:transparent;z-index:100001;border-radius:0'
      : `position:fixed;bottom:104px;right:24px;width:${expanded?'520':'380'}px;max-width:calc(100vw - 48px);height:${expanded?'640':'500'}px;max-height:calc(100dvh - 128px);border:0;background:transparent;z-index:100000`;
  };
  const lockScroll = lock => {
    if (lock && previousOverflow === undefined) {
      previousOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
    } else if (!lock && previousOverflow !== undefined) {
      document.body.style.overflow = previousOverflow;
      previousOverflow = undefined;
    }
  };
  const relay = (data, source) => {
    for (const frame of [buttonFrame, chatFrame]) {
      if (frame && frame.contentWindow !== source) frame.contentWindow.postMessage(data, apiOrigin);
    }
  };
  const toggle = (open, source) => {
    if (!chatFrame) return;
    if (open) sizeWindow();
    chatFrame.hidden = !open;
    chatFrame.style.display = open ? 'block' : 'none';
    lockScroll(open && (mobile() || fullscreen));
    relay({type:'TOGGLE_CHAT',isOpen:open}, source);
    if (open) chatFrame.focus();
    else buttonFrame?.focus();
  };
  window.addEventListener('message', event => {
    if (event.origin !== apiOrigin || !event.data || typeof event.data !== 'object') return;
    if (event.source !== buttonFrame?.contentWindow && event.source !== chatFrame?.contentWindow) return;
    const data = event.data;
    if (data.type === 'CREATE_CHAT_WINDOW' && event.source === buttonFrame?.contentWindow) {
      if (chatFrame || !masterUrl) return;
      const url = new URL(masterUrl);
      url.searchParams.set('mode','window');
      chatFrame = document.createElement('iframe');
      chatFrame.id = 'swipies-support-window';
      chatFrame.title = 'Swipies AI support conversation';
      chatFrame.src = url.toString();
      chatFrame.referrerPolicy = 'no-referrer';
      chatFrame.hidden = true;
      sizeWindow();
      chatFrame.style.display = 'none';
      document.body.appendChild(chatFrame);
    } else if (data.type === 'TOGGLE_CHAT' && typeof data.isOpen === 'boolean') {
      toggle(data.isOpen, event.source);
    } else if (data.type === 'SET_FULLSCREEN' && typeof data.isFullscreen === 'boolean') {
      fullscreen = data.isFullscreen;
      sizeWindow();
      lockScroll(!!chatFrame && !chatFrame.hidden && (fullscreen || mobile()));
    } else if (data.type === 'RESIZE_CHAT_WINDOW' && event.source === chatFrame?.contentWindow && !mobile() && !fullscreen) {
      expanded = data.width === '520px';
      const hidden = chatFrame.hidden;
      sizeWindow();
      if (hidden) chatFrame.style.display = 'none';
    } else if (data.type === 'SCROLL_PASSTHROUGH' && Number.isFinite(data.deltaY)) {
      window.scrollBy(0, Math.max(-600, Math.min(600, data.deltaY)));
    }
  });
  window.addEventListener('resize', () => {
    if (chatFrame && !chatFrame.hidden) {
      sizeWindow();
      lockScroll(mobile() || fullscreen);
    }
  });
  window.addEventListener('keydown', event => {
    if (event.key === 'Escape' && chatFrame && !chatFrame.hidden) toggle(false);
  });
  fetch('/support-chat-config.json', {credentials:'omit',cache:'no-store'})
    .then(response => {
      if (!response.ok) throw new Error('Widget configuration unavailable');
      return response.json();
    })
    .then(config => {
      if (config.origin !== apiOrigin || !/^[a-f0-9]{32}$/.test(config.chatId) || typeof config.embedAuthorization !== 'string' || !config.embedAuthorization) throw new Error('Invalid widget configuration');
      const locale = ['en','ru','uz'].includes(document.documentElement.lang) ? document.documentElement.lang : 'en';
      const url = new URL('/chats/widget', apiOrigin);
      const query = {shared_id:config.chatId,from:'chat',auth:config.embedAuthorization,mode:'master',streaming:'true',muted:'true',locale,
        widget_title:'Swipies AI',widget_subtitle:locale==='ru'?'Помощь с платформой':locale==='uz'?'Platforma bo‘yicha yordam':'Platform help',
        widget_footer:'Powered by Swipies.app',widget_footer_link:'https://swipies.app',widget_accent_color:'#e8a820',widget_background_color:'#0d1119',widget_text_color:'#e8e6e0',widget_header_text_color:'#241b0c',widget_footer_text_color:'#aab2bf'};
      for (const [key,value] of Object.entries(query)) url.searchParams.set(key,value);
      masterUrl = url.toString();
      buttonFrame = document.createElement('iframe');
      buttonFrame.id = 'swipies-support-button';
      buttonFrame.title = 'Swipies AI — open support chat';
      buttonFrame.src = masterUrl;
      buttonFrame.referrerPolicy = 'no-referrer';
      buttonFrame.style.cssText = 'position:fixed;bottom:0;right:0;width:100px;height:100px;border:0;background:transparent;z-index:100000';
      document.body.appendChild(buttonFrame);
    })
    .catch(() => {
      // Preserve access to a human if the native widget cannot be initialized.
      const link = document.createElement('a');
      link.href = 'https://t.me/swipies_ai';
      link.textContent = 'Swipies Support';
      link.id = 'swipies-support-fallback';
      link.style.cssText = 'position:fixed;bottom:24px;right:24px;background:#e8a820;color:#241b0c;padding:12px 16px;border-radius:4px;z-index:100000';
      document.body.appendChild(link);
    });
})();
