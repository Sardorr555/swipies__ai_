# Лендинги и UTM

Дата: 2026-11-08. Опубликовано в рабочей админке по прямому разрешению владельца.

Отдельная страница `/admin/acquisition` использует существующую сессию
администратора. Девять решений добавлены как планируемые, переходы выключены.
Администратор задаёт название и HTTPS-адрес отдельного поддомена Swipies,
включает переходы и сохраняет кампании с пятью стандартными UTM-полями.
Публичный основной лендинг `index.html` не изменяется.

## Подключение

На новом лендинге: `<script src="https://swipies.app/acquisition-link.js"
data-landing="sales" defer></script>`. Кнопки входа в платформу помечаются
`data-swipies-platform`. Скрипт не трогает остальные ссылки. Кампания берётся
из URL; сохранение в sessionStorage разрешено только при существующем
`swipies_cookie_consent=accepted`. При отказе сохранённая атрибуция удаляется.

UTM-ссылка ведёт прямо на лендинг с `sw_campaign`. При клике CTA браузер
переходит через `/api/acquisition/go/<slug>` на фиксированный адрес
`https://api.swipies.app/login`. Центральный сервис проверяет принадлежность
кампании лендингу, записывает переход и передаёт случайный `vid` и UTM.
Существующая регистрация login-next уже сохраняет эти поля: дополнительная
миграция основной платформы не требуется. Интеграция кнопок требует публикации
новых лендингов; одно добавление адреса в админке не подключает DNS и сайт.

## Определения и ограничения

Считаются события перехода через общий маршрут, а не посещения лендинга,
физические люди или регистрации. Повторы и автоматические открытия могут
учитываться. Прямая регистрация вне этого пути не приписывается лендингу.
Публичная ссылка может быть скопирована: атрибуция кампании не доказывает,
что посетитель действительно просмотрел лендинг или пришёл из рекламного кабинета.

Имя/email выдаются только администратору и только из фактической таблицы `user`
через существующее read-only подключение MYSQL, по точному `visitor_id`.
Публичный `/api/platform/events` не используется как доказательство регистрации.
Уже авторизованные пользователи, смена браузера и другие маршруты могут не
сопоставиться. Недоступность MYSQL отображается явно, без ложного вывода
об отсутствии аккаунтов. Сопоставление отражает текущую сохранённую атрибуцию,
не полную историю всех касаний. Прежние посетители основного лендинга
не импортируются в эту новую таблицу.

Отчёт фильтруется по периоду до 366 дней, лендингу и сохранённой кампании;
выдаётся по 100 переходов на страницу. Время показывается в часовом поясе
браузера; границы передаются в UTC. Реестр кампаний ограничен 500 строками
на запрос, при превышении возвращается явная ошибка, а не неполный итог.

## Хранение и публикация

Private `acquisition-state.sqlite` рядом с landing database: реестр, кампании,
переходы. Создаётся при первом обращении, основной schema не меняется.
Нужны права записи сервисного пользователя и резервное копирование. Настроить
политику хранения перед ростом объёма. Данные и конфигурация не публикуются
в `/var/www/html`. Домен/путь существующего кода лендинга неизменяемы,
для нового адреса создаётся другой код.

Публиковать только HTML/CSS/JS в web root; Python — в приватную директорию
сервиса. Добавить acquisition-nginx.conf в существующий HTTPS server block,
проверить `nginx -t` и перезапустить landing service по отдельному разрешению.
Генератор setup_nginx.py содержит те же изолированные маршруты; не запускать
его вслепую поверх действующих настроек. `/acquisition.html` закрыт,
защищённый путь открывается через краткоживущую HttpOnly cookie, а API
заново проверяет исходную администраторскую сессию. Отзыв сессии закрывает доступ.

Код: [модуль](../../new%20site%20for%20swipies/landing_acquisition.py),
[страница](../../new%20site%20for%20swipies/acquisition.html),
[скрипт подключения](../../new%20site%20for%20swipies/acquisition-link.js).
Проверки: test/test_landing_acquisition.py и test/landing_acquisition_browser.cjs.

## UI / release update 2026-11-08

Owner explicitly authorized publishing only this admin section. The new page
uses the production admin palette, fonts and 4px radius. Added a three-step
workflow, plain-language field labels, inactive-landing guidance and copyable
read-only URL inputs. Main public index.html must remain byte-for-byte unchanged.
Release uses narrow server-side edits and backups; no platform workflow push.

## Production release

Release: `acquisition-20261108-ede872ac`. Published 2026-11-08 by explicit owner instruction.
Only new acquisition files, an added admin menu script, the API extension hook
and isolated Nginx locations were published. Both private and served index.html
SHA-256 values match the pre-release baseline. Existing public landing assets
were not replaced. Nginx validation, service restart and HTTPS health passed.

The page uses the existing dark/amber administrator tokens. A private local
database-reading configuration now reuses the existing local platform connection;
no identity values leave the server. Queries use the existing READ ONLY transaction
adapter; platform tables and accounts were not modified. The configuration is 0600
and has a server-local backup beside the scoped release rollback files.

Validation: 17 acquisition Python tests, 4 browser logic checks and actual Chrome
creation/mobile/color checks passed. Existing reporting/auth regression: 48 passed.
Deployed in-process route checks passed, and the actual platform account schema
was read successfully without selecting account rows. Public API calls without
authentication return 401; raw acquisition.html returns 404. Cloudflare Access
continues to protect the admin routes, so public probes correctly reach its login
page. No browser-authenticated production session was created for release checks.
Nine planned landings are inactive, campaigns and production transitions are empty.
New landing publication and CTA integration remain the next task.
