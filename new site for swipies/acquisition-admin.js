/* Uses existing administrator sessions. No public page changes. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let landings = [], campaigns = [], page = 1, generation = 0;
  const token = localStorage.getItem('swipies_admin_token');
  if (!token) { location.assign('/admin.html'); return; }
  const error = e => { $('message').textContent = e.message || 'Не удалось загрузить данные.'; };
  async function api(path, data) {
    const response = await fetch('/api/admin/acquisition/' + path, {
      method: data ? 'POST' : 'GET', cache: 'no-store',
      headers: {Authorization: 'Bearer ' + token, ...(data ? {'Content-Type':'application/json'} : {})},
      ...(data ? {body: JSON.stringify(data)} : {})
    });
    if (response.status === 401 || response.status === 403) { location.assign('/admin.html'); throw Error('Войдите в админку.'); }
    const result = await response.json();
    if (!response.ok || result.code !== 0) throw Error(result.message || 'Ошибка запроса.');
    return result.data;
  }
  function element(tag, value, cls) {
    const node = document.createElement(tag); if (value !== undefined) node.textContent = value;
    if (cls) node.className = cls; return node;
  }
  function options(id, rows, all) {
    const select = $(id), old = select.value; select.replaceChildren();
    if (all) select.append(new Option(all, ''));
    for (const r of rows) select.append(new Option(r.name, r.slug || r.id));
    if ([...select.options].some(o => o.value === old)) select.value = old;
  }
  function snippet() {
    const slug = $('campaignLanding').value || 'sales';
    $('snippet').textContent = '<script src="https://swipies.app/acquisition-link.js" data-landing="' + slug + '" defer></script>';
  }
  async function loadLandings() {
    landings = await api('landings');
    const previousLanding = $('campaignLanding').value;
    options('filterLanding', landings, 'Все лендинги'); options('campaignLanding', landings);
    if (!previousLanding && landings.some(l => l.slug === 'sales')) $('campaignLanding').value = 'sales';
    $('landings').replaceChildren();
    for (const l of landings) {
      const card = element('div', undefined, 'card');
      card.append(element('b', l.name), element('p', l.url), element('small', l.active ? 'Переходы разрешены' : 'Ожидает запуска', 'state' + (l.active ? ' active' : '')));
      const edit = element('button', 'Настройки', 'secondary'); edit.type = 'button';
      edit.onclick = () => {
        const form = $('landingForm'); form.closest('details').open = true;
        for (const key of ['slug','name','url']) form.elements[key].value = l[key];
        form.elements.active.checked = !!l.active; form.scrollIntoView({behavior:'smooth',block:'center'});
      };
      card.append(element('p'), edit); $('landings').append(card);
    }
    snippet();
  }
  async function loadCampaigns() {
    campaigns = await api('campaigns');
    campaignOptions(); $('campaigns').replaceChildren();
    for (const c of campaigns) {
      const tr = element('tr'), title = element('td', c.name);
      title.append(element('small', (landings.find(l => l.slug === c.landing)?.name || c.landing) + (c.active ? '' : ' · ожидает запуска')));
      const tags = element('td', c.utm_source + ' / ' + c.utm_medium);
      tags.append(element('small', c.utm_campaign));
      const link = element('td'), input = element('input',undefined,'url-input'); input.value=c.url; input.readOnly=true; input.setAttribute('aria-label','Готовая ссылка: '+c.name); input.onclick=()=>input.select();
      const copy = element('button', 'Копировать', 'secondary'); copy.type = 'button';
      copy.onclick = async () => { try { await navigator.clipboard.writeText(c.url); $('message').textContent = 'Ссылка скопирована. Можно вставить её в рекламу или публикацию.'; } catch { input.select(); $('message').textContent = 'Ссылка выделена. Нажмите Ctrl+C, чтобы скопировать её.'; } };
      link.append(input, copy); tr.append(title, tags, link); $('campaigns').append(tr);
    }
    if (!campaigns.length) emptyRow('campaigns','Пока нет ссылок. Создайте первую с помощью формы выше.',3);
  }
  function emptyRow(id,message,columns) {
    const row=element('tr'),cell=element('td',message);cell.colSpan=columns;row.append(cell);$(id).replaceChildren(row);
  }
  function campaignHint() {
    const landing=landings.find(l => l.slug === $('campaignLanding').value);
    if ($('campaignHint')) $('campaignHint').textContent=landing?.active ? 'Ссылка откроет выбранный лендинг. Переход на платформу будет связан с указанной кампанией.' : 'Этот лендинг ожидает запуска. Ссылку можно подготовить заранее; размещайте её после публикации лендинга.';
    snippet();
  }
  function campaignOptions() {
    const slug = $('filterLanding').value;
    options('filterCampaign', campaigns.filter(c => !slug || c.landing === slug), 'Все кампании');
  }
  const time = value => new Date(value).toLocaleString('ru-RU');
  async function report() {
    const requestId = ++generation;
    $('message').textContent = ''; emptyRow('transitions','Загружаем переходы…',6);
    $('prev').disabled=true;$('next').disabled=true;
    const params = new URLSearchParams({start: new Date($('start').value).toISOString(), end: new Date($('end').value).toISOString(), landing:$('filterLanding').value, campaign:$('filterCampaign').value, page:String(page)});
    try {
      const data = await api('report?' + params);
      if (requestId !== generation) return;
      $('summary').replaceChildren();
      const total = element('div', undefined, 'card'); total.append(element('small','Переходов за период'),element('strong',String(data.total))); $('summary').append(total);
      for (const s of data.summary) { const c = element('div', undefined, 'card'); c.append(element('small',landings.find(l => l.slug === s.landing)?.name || s.landing),element('strong',String(s.transitions))); $('summary').append(c); }
      $('accountsStatus').textContent = data.accounts_status === 'ready' ? 'Имя и email показаны там, где переход удалось связать с аккаунтом.' : 'Переходы доступны. Данные аккаунтов временно не удалось получить.';
      $('transitions').replaceChildren();
      for (const r of data.rows) {
        const who = r.accounts.length ? r.accounts.map(a => (a.nickname ? a.nickname + ' · ' : '') + a.email).join('; ') : data.accounts_status === 'ready' ? 'Аккаунт не определён' : 'Данные временно недоступны';
        const tr = element('tr');
        for (const v of [time(r.created_at),landings.find(l => l.slug===r.landing)?.name || r.landing,who,(r.utm_source || 'Без метки') + ' / ' + (r.utm_medium || '—'),r.utm_campaign || '—',(r.utm_content || '—') + ' / ' + (r.utm_term || '—')]) tr.append(element('td',v));
        $('transitions').append(tr);
      }
      if (!data.rows.length) emptyRow('transitions','За этот период переходов пока нет. Они появятся после запуска лендингов и размещения ссылок.',6);
      $('pageInfo').textContent = 'Страница ' + page + ' · всего переходов: ' + data.total;
      $('prev').disabled = page <= 1; $('next').disabled = page * 100 >= data.total;
    } catch (e) { if (requestId === generation) { emptyRow('transitions','Не удалось получить отчёт. Попробуйте ещё раз.',6); $('summary').replaceChildren(); error(e); } }
  }
  const local = date => new Date(date.getTime() - date.getTimezoneOffset()*60000).toISOString().slice(0,16);
  // Include the current minute rather than silently cutting it off.
  $('end').value = local(new Date(Date.now()+60000)); $('start').value = local(new Date(Date.now()-30*86400000));
  $('zone').textContent = 'Время отображается в часовом поясе браузера: ' + Intl.DateTimeFormat().resolvedOptions().timeZone;
  $('filters').onsubmit = e => { e.preventDefault(); page=1; report().catch(error); };
  $('filterLanding').onchange = () => { $('filterCampaign').value=''; campaignOptions(); };
  $('campaignLanding').onchange = campaignHint;
  $('prev').onclick = () => { page--; report().catch(error); }; $('next').onclick = () => { page++; report().catch(error); };
  $('campaignForm').onsubmit = async e => {
    e.preventDefault(); const button = e.submitter; button.disabled = true;
    try { await api('campaigns',Object.fromEntries(new FormData(e.target))); await loadCampaigns(); $('message').textContent='Ссылка готова. Найдите её первой в списке и нажмите «Копировать».'; } catch (e) { error(e); } finally { button.disabled=false; }
  };
  $('landingForm').onsubmit = async e => {
    e.preventDefault(); const button = e.submitter; button.disabled=true;
    try { const data = Object.fromEntries(new FormData(e.target)); data.active=e.target.elements.active.checked; await api('landings', data); await loadLandings(); await loadCampaigns();campaignHint(); $('message').textContent='Настройки сохранены.'; } catch(e) {error(e);} finally {button.disabled=false;}
  };
  (async () => {await loadLandings(); await loadCampaigns();campaignHint(); await report();})().catch(error);
})();
