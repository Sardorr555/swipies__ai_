/* Swipies MCP setup: local configuration generation only; no requests or storage. */
function buildSwipiesSetup(client, os, interpreter, file) {
  if (!['codex', 'claude', 'cursor'].includes(client) || !['windows', 'posix'].includes(os) || !['python', 'python3', 'py'].includes(interpreter)) return null;
  if (typeof file !== 'string' || /[\x00-\x1f\x7f]/.test(file)) return null;
  if (!(os === 'windows' ? /^[A-Za-z]:[\\/]/.test(file) : file.startsWith('/')) || !file.endsWith('.py')) return null;
  const quote = value => os === 'windows' ? "'" + value.replace(/'/g, "''") + "'" : "'" + value.replace(/'/g, "'\"'\"'") + "'";
  if (client === 'cursor') return JSON.stringify({mcpServers: {swipies: {command: interpreter, args: [file]}}}, null, 2);
  const prefix = client === 'codex' ? 'codex mcp add swipies -- ' : 'claude mcp add --transport stdio --scope user swipies -- ';
  return prefix + interpreter + ' ' + quote(file);
}

/* UI initialization */
(() => {
  'use strict';
  const root = document.getElementById('swipies-setup');
  if (!root) return;
  const translations = {
    en: {
      title: 'Connect your AI client', intro: 'Set up once, then describe your tasks in chat.',
      downloadTitle: '1. Save the client', download: 'Download Python client', save: 'Requires Python 3.10+ and your installed AI client. Save the download as swipies_agent_client.py, removing any final .txt extension. Review the source before connecting.',
      configure: '2. Choose your client', os: 'Your terminal', windows: 'Windows · PowerShell', posix: 'macOS / Linux · shell', interpreter: 'Python command', path: 'Absolute path to the saved .py file', pathHint: 'Use the path on the machine where your AI client runs. The website cannot locate or verify local files.',
      empty: 'Enter an absolute path ending in .py to generate your configuration.', copy: 'Copy configuration', copied: 'Configuration copied.', copyError: 'Select the configuration above and copy it manually.',
      codexHelp: 'Run this command in the terminal above. It adds a personal MCP connection. Check it with codex mcp list, then reopen your AI session if needed. If swipies is already configured, inspect it before changing the connection.',
      claudeHelp: 'Run this command in the terminal above. The user scope makes it available across your projects. Check with claude mcp get swipies and /mcp in Claude Code. Inspect any existing swipies connection first.',
      cursorHelp: 'Merge the swipies entry into mcpServers in ~/.cursor/mcp.json (personal) or .cursor/mcp.json (this project). Keep your other servers. Restart Cursor and check that Swipies is enabled in its MCP settings.',
      terminalLabel: 'Command for your selected terminal', jsonLabel: 'Cursor mcp.json configuration', docs: 'Official client instructions',
      account: 'Existing account or Plus/Pro? Configure its SWIPIES_API_KEY securely in the MCP process environment before first use; follow the account guide. Without a key, first use creates a separate Free workspace. Never enter your key on this page.',
      accountLink: 'Account and credential guide', verify: '3. Ask your AI to check the connection', task: 'Read https://swipies.app/llms.txt. Check the configured Swipies connection and list available dataset operations. Before creating a new workspace, confirm whether an existing account connection is configured.',
      permissions: 'Your AI client may ask you to enable or approve the tools. This page generates configuration; it does not install software or check whether you are connected.', language: 'Setup language', nojs: 'JavaScript is needed for the generator. The connection guide below and full agent instructions work without it.'
    },
    ru: {
      title: 'Подключите свой ИИ-клиент', intro: 'Настройте подключение один раз, затем ставьте задачи в чате.',
      downloadTitle: '1. Сохраните клиент', download: 'Скачать Python-клиент', save: 'Нужны Python 3.10+ и установленный ИИ-клиент. Сохраните файл как swipies_agent_client.py, убрав конечное .txt. Перед подключением просмотрите исходник.',
      configure: '2. Выберите ИИ-клиент', os: 'Ваш терминал', windows: 'Windows · PowerShell', posix: 'macOS / Linux · shell', interpreter: 'Команда Python', path: 'Полный путь к сохранённому файлу .py', pathHint: 'Укажите путь на компьютере, где работает ИИ-клиент. Сайт не может найти или проверить локальный файл.',
      empty: 'Введите полный путь к файлу с расширением .py, чтобы получить конфигурацию.', copy: 'Скопировать конфигурацию', copied: 'Конфигурация скопирована.', copyError: 'Выделите конфигурацию выше и скопируйте её вручную.',
      codexHelp: 'Выполните команду в выбранном выше терминале. Она добавляет личное MCP-подключение. Проверьте его через codex mcp list и при необходимости заново откройте сессию ИИ. Если swipies уже настроен, сначала проверьте существующее подключение.',
      claudeHelp: 'Выполните команду в выбранном выше терминале. Область user делает подключение доступным в ваших проектах. Проверка: claude mcp get swipies и /mcp в Claude Code. Сначала проверьте, нет ли уже подключения swipies.',
      cursorHelp: 'Добавьте запись swipies в mcpServers файла ~/.cursor/mcp.json (личный) или .cursor/mcp.json (этот проект). Сохраните другие серверы. Перезапустите Cursor и проверьте, что Swipies включён в настройках MCP.',
      terminalLabel: 'Команда для выбранного терминала', jsonLabel: 'Конфигурация mcp.json для Cursor', docs: 'Официальная инструкция клиента',
      account: 'Уже есть аккаунт или подписка Plus/Pro? До первого запуска безопасно настройте его SWIPIES_API_KEY в окружении MCP-процесса по руководству. Без ключа при первом обращении создаётся отдельный Free-аккаунт. Не вводите ключ на этой странице.',
      accountLink: 'Аккаунт и безопасная настройка доступа', verify: '3. Попросите ИИ проверить подключение', task: 'Прочитай https://swipies.app/llms.txt. Проверь настроенное подключение Swipies и покажи доступные операции для датасетов. Прежде чем создавать новый аккаунт, проверь, настроен ли доступ к существующему.',
      permissions: 'ИИ-клиент может запросить включение или одобрение инструментов. Эта страница формирует конфигурацию; она не устанавливает программы и не проверяет статус подключения.', language: 'Язык инструкции', nojs: 'Для генератора нужен JavaScript. Руководство ниже и полная инструкция для ИИ доступны без него.'
    },
    uz: {
      title: 'AI klientingizni ulang', intro: 'Bir marta sozlang, keyin vazifalarni chatda yozing.',
      downloadTitle: '1. Klientni saqlang', download: 'Python klientini yuklab olish', save: 'Python 3.10+ va o‘rnatilgan AI klienti kerak. Faylni swipies_agent_client.py nomi bilan saqlang, oxirgi .txt kengaytmasini olib tashlang. Ulashdan oldin kodini ko‘rib chiqing.',
      configure: '2. AI klientini tanlang', os: 'Terminalingiz', windows: 'Windows · PowerShell', posix: 'macOS / Linux · shell', interpreter: 'Python buyrug‘i', path: 'Saqlangan .py faylining to‘liq yo‘li', pathHint: 'AI klienti ishlaydigan kompyuterdagi yo‘lni kiriting. Sayt lokal faylni topa yoki tekshira olmaydi.',
      empty: 'Konfiguratsiya olish uchun .py bilan tugaydigan to‘liq fayl yo‘lini kiriting.', copy: 'Konfiguratsiyani nusxalash', copied: 'Konfiguratsiya nusxalandi.', copyError: 'Yuqoridagi konfiguratsiyani belgilang va qo‘lda nusxalang.',
      codexHelp: 'Buyruqni yuqorida tanlangan terminalda bajaring. U shaxsiy MCP ulanishini qo‘shadi. codex mcp list orqali tekshiring va kerak bo‘lsa AI sessiyasini qayta oching. swipies avvaldan sozlangan bo‘lsa, avval mavjud ulanishni tekshiring.',
      claudeHelp: 'Buyruqni yuqorida tanlangan terminalda bajaring. user doirasi ulanishni loyihalaringizda mavjud qiladi. claude mcp get swipies va Claude Code ichida /mcp orqali tekshiring. Avval mavjud swipies ulanishini tekshiring.',
      cursorHelp: 'swipies yozuvini ~/.cursor/mcp.json (shaxsiy) yoki .cursor/mcp.json (shu loyiha) faylidagi mcpServers ichiga qo‘shing. Boshqa serverlarni saqlang. Cursor’ni qayta ishga tushiring va MCP sozlamalarida Swipies yoqilganini tekshiring.',
      terminalLabel: 'Tanlangan terminal uchun buyruq', jsonLabel: 'Cursor uchun mcp.json konfiguratsiyasi', docs: 'Klientning rasmiy qo‘llanmasi',
      account: 'Mavjud akkaunt yoki Plus/Pro bormi? Birinchi ishga tushirishdan oldin uning SWIPIES_API_KEY qiymatini qo‘llanma bo‘yicha MCP jarayoni muhitida xavfsiz sozlang. Kalitsiz birinchi murojaatda alohida Free akkaunt yaratiladi. Kalitni bu sahifaga kiritmang.',
      accountLink: 'Akkaunt va xavfsiz ulanish qo‘llanmasi', verify: '3. AI’dan ulanishni tekshirishni so‘rang', task: 'https://swipies.app/llms.txt manzilini o‘qi. Sozlangan Swipies ulanishini tekshir va datasetlar uchun mavjud amallarni ko‘rsat. Yangi akkaunt yaratishdan oldin mavjud akkauntga ulanish sozlanganini tekshir.',
      permissions: 'AI klienti vositalarni yoqish yoki tasdiqlashni so‘rashi mumkin. Bu sahifa konfiguratsiya yaratadi; dastur o‘rnatmaydi va ulanish holatini tekshirmaydi.', language: 'Qo‘llanma tili', nojs: 'Generator uchun JavaScript kerak. Quyidagi qo‘llanma va AI uchun to‘liq ko‘rsatmalar JavaScript’siz ishlaydi.'
    }
  };
  const byId = id => document.getElementById('sw-setup-' + id);
  let selected = 'codex', lang = 'en', output = null, revision = 0;
  const docs = {codex: 'https://developers.openai.com/codex/mcp/', claude: 'https://code.claude.com/docs/en/mcp', cursor: 'https://cursor.com/help/customization/mcp'};
  function render() {
    lang = root.dataset.standalone === 'true' ? byId('language').value : document.documentElement.lang;
    if (!translations[lang]) lang = 'en';
    root.lang = lang;
    const text = translations[lang];
    root.querySelectorAll('[data-setup-i18n]').forEach(el => { el.textContent = text[el.dataset.setupI18n]; });
    root.querySelectorAll('[data-setup-client]').forEach(el => el.setAttribute('aria-pressed', String(el.dataset.setupClient === selected)));
    const os = byId('os').value;
    byId('path').placeholder = os === 'windows' ? 'C:\\Users\\YourName\\Downloads\\swipies_agent_client.py' : '/home/yourname/swipies_agent_client.py';
    output = buildSwipiesSetup(selected, os, byId('interpreter').value, byId('path').value);
    byId('output').textContent = output || text.empty;
    byId('path').setAttribute('aria-invalid', String(byId('path').value !== '' && output === null));
    byId('output-label').textContent = text[selected === 'cursor' ? 'jsonLabel' : 'terminalLabel'];
    byId('help').textContent = text[selected + 'Help'];
    byId('copy').disabled = !output;
    byId('docs').href = docs[selected];
    byId('status').textContent = '';
    revision++;
  }
  root.querySelectorAll('[data-setup-client]').forEach(el => el.addEventListener('click', () => { selected = el.dataset.setupClient; render(); }));
  byId('os').addEventListener('change', () => { byId('interpreter').value = byId('os').value === 'windows' ? 'python' : 'python3'; render(); });
  byId('path').addEventListener('input', render);
  byId('interpreter').addEventListener('change', render);
  byId('language').addEventListener('change', render);
  byId('copy').addEventListener('click', async () => {
    if (!output) return;
    const current = revision, value = output;
    try { await navigator.clipboard.writeText(value); if (current === revision) byId('status').textContent = translations[lang].copied; }
    catch (_) { if (current === revision) byId('status').textContent = translations[lang].copyError; }
  });
  new MutationObserver(render).observe(document.documentElement, {attributes: true, attributeFilter: ['lang']});
  render();
})();
