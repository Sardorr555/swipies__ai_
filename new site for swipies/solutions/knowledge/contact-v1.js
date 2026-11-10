(() => {
  const copy = {
    ru: [
      'Контакты',
      'Остались вопросы? Напишите нам',
      'Компания / Проект (необязательно)',
      'Имя *',
      'Телефон / WhatsApp',
      'Telegram юзернейм / номер (необязательно)',
      'Сообщение (необязательно)',
      'Отправить',
      'Отправляем…',
      'Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.',
      'Не удалось отправить. Проверьте поля и попробуйте ещё раз.',
      'Закрыть',
      'Связаться с нами',
      'Укажите хотя бы один способ связи: телефон или email.'
    ],
    en: [
      'Contact',
      'Questions? Write to us',
      'Company / Project (optional)',
      'Full name *',
      'Phone / WhatsApp',
      'Telegram username / number (optional)',
      'Message (optional)',
      'Send',
      'Sending…',
      'Message sent successfully! We will get back to you shortly.',
      'Could not send your message. Please try again.',
      'Close',
      'Contact Us',
      'Please provide at least one contact method: phone or email.'
    ],
    uz: [
      'Aloqa',
      'Savollaringiz bormi? Bizga yozing',
      'Kompaniya / Loyiha (ixtiyoriy)',
      'Ism *',
      'Telefon / WhatsApp',
      'Telegram foydalanuvchi nomi / raqami (ixtiyoriy)',
      'Xabar (ixtiyoriy)',
      'Yuborish',
      'Yuborilmoqda…',
      'Xabar muvaffaqiyatli yuborildi! Tez orada siz bilan bog‘lanamiz.',
      'Xabar yuborilmadi. Maydonlarni tekshiring va qayta urinib ko‘ring.',
      'Yopish',
      'Biz bilan bog‘lanish',
      'Kamida bitta aloqa usulini kiriting: telefon yoki email.'
    ]
  };

  const currentLang = () => {
    const raw = (document.documentElement.lang || 'ru').split('-')[0].toLowerCase();
    return copy[raw] || copy.ru;
  };

  const host = document.querySelector('[data-contact-inline]');
  const dialog = document.createElement('dialog');
  dialog.className = 'sw-contact-dialog';
  dialog.setAttribute('aria-labelledby', 'sw-contact-title');
  dialog.innerHTML = '<button class="sw-contact-close" type="button" aria-label="Close">×</button><p class="sw-contact-kicker"></p><h2 id="sw-contact-title"></h2><div data-contact-dialog-slot></div>';

  const closeBtn = dialog.querySelector('.sw-contact-close');
  const form = document.createElement('form');
  form.className = 'sw-contact-form';
  form.innerHTML = `
    <div class="sw-contact-fields">
      <label><span></span><input name="name" required maxlength="120" autocomplete="name"></label>
      <label><span></span><input name="company" maxlength="150" autocomplete="organization"></label>
      <label><span>Email</span><input type="email" name="email" maxlength="120" autocomplete="email"></label>
      <label><span></span><input type="tel" name="phone" maxlength="40" autocomplete="tel"></label>
    </div>
    <label><span></span><input name="telegram" maxlength="120" autocomplete="off"></label>
    <label><span></span><textarea name="message" rows="3" maxlength="2850"></textarea></label>
    <div hidden aria-hidden="true"><input name="hp_field" tabindex="-1" autocomplete="off"></div>
    <button type="submit"></button>
    <p class="sw-contact-status" role="status" aria-live="polite"></p>
  `;

  const labels = form.querySelectorAll('label span');
  const submitBtn = form.querySelector('[type=submit]');
  const statusEl = form.querySelector('[role=status]');
  const launcherBtn = document.querySelector('[data-contact-launcher]');

  const localize = () => {
    const t = currentLang();
    dialog.querySelector('.sw-contact-kicker').textContent = '— ' + t[0];
    dialog.querySelector('#sw-contact-title').textContent = t[1];
    labels[0].textContent = t[3]; // Name *
    labels[1].textContent = t[2]; // Company
    labels[2].textContent = 'Email';
    labels[3].textContent = t[4]; // Phone
    labels[4].textContent = t[5]; // Telegram
    labels[5].textContent = t[6]; // Message
    if (!submitBtn.disabled) submitBtn.textContent = t[7];
    closeBtn.setAttribute('aria-label', t[11]);
    if (launcherBtn) launcherBtn.textContent = t[12];
  };

  document.body.append(dialog);
  if (host) host.append(form);
  localize();
  new MutationObserver(localize).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });

  let trigger = null;
  const openModal = (element) => {
    if (dialog.open) return;
    trigger = element || null;
    statusEl.textContent = '';
    statusEl.classList.remove('is-error');
    dialog.querySelector('[data-contact-dialog-slot]').append(form);
    dialog.showModal();
    const nameInput = form.elements.name;
    if (nameInput) nameInput.focus();
  };

  closeBtn.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    if (host) host.append(form);
    trigger?.focus();
  });

  document.addEventListener('click', (event) => {
    const target = event.target.closest('[data-contact-open]');
    if (!target || event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    openModal(target);
  }, true);

  if (new URLSearchParams(location.search).get('contact') === '1') {
    openModal();
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (submitBtn.disabled) return;
    const t = currentLang();

    const data = Object.fromEntries(new FormData(form));
    for (const key of Object.keys(data)) {
      data[key] = (typeof data[key] === 'string') ? data[key].trim() : data[key];
    }

    // Require at least one contact method: email or phone
    if (!data.email && !data.phone) {
      statusEl.classList.add('is-error');
      statusEl.textContent = t[13];
      if (form.elements.phone) form.elements.phone.focus();
      return;
    }

    // Determine verified landing slug
    const hostParts = location.hostname.split('.');
    const hostSub = hostParts[0].toLowerCase();
    const knownLandings = {
      sales: 1, support: 1, knowledge: 1, booking: 1,
      education: 1, hr: 1, operations: 1, enterprise: 1
    };
    const currentScript = document.currentScript || document.querySelector('script[src*="contact-v1"]');
    const scriptSlug = currentScript?.getAttribute('data-landing-slug') || '';
    const slug = (hostSub in knownLandings) ? hostSub : (scriptSlug || 'b2c');

    data.landing_slug = slug;
    data.source = (slug === 'enterprise' || location.hostname === 'enterprise.swipies.app') ? 'enterprise' : 'b2c';

    try {
      data.referral_code = localStorage.getItem('swipies_ref') || '';
    } catch {
      data.referral_code = '';
    }

    submitBtn.disabled = true;
    submitBtn.textContent = t[8];
    statusEl.textContent = '';
    statusEl.classList.remove('is-error');

    try {
      const response = await fetch('/api/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      if (!response.ok || result.code !== 0 || !result.data?.id) {
        throw new Error(result.message || 'Submission failed');
      }

      form.reset();
      statusEl.classList.remove('is-error');
      statusEl.textContent = t[9];
      if (typeof window.trackAnalyticsEvent === 'function') {
        window.trackAnalyticsEvent('form_submit', { landing: slug });
      }
    } catch (err) {
      statusEl.classList.add('is-error');
      statusEl.textContent = t[10];
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = t[7];
    }
  });
})();
