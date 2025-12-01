# 🔍 Инструкция по отладке OAuth на AWS

## ✅ Изменения запушены в GitHub

Commit: `Fix OAuth Google login bug - add detailed logging and correct token handling`

## 🚀 Что нужно сделать на AWS сервере

### 1. Обновить код на сервере

```bash
# Подключитесь к AWS серверу и перейдите в папку проекта
cd /path/to/ragflow

# Остановите контейнеры
docker compose down

# Получите последние изменения
git pull origin main

# Пересоберите и запустите контейнеры
docker compose up -d --build
```

### 2. Проверить логи браузера

Откройте сайт в браузере и:
1. Откройте Developer Tools (F12)
2. Перейдите на вкладку **Console**
3. Нажмите "Sign in with Google"
4. Авторизуйтесь через Google
5. **ВАЖНО**: Смотрите логи в консоли

Вы должны увидеть детальные логи вида:
```
[OAuth] ==================== OAuth Callback Start ====================
[OAuth] Received auth token from URL, length: 123
[OAuth] Removing auth parameter from URL...
[OAuth] ✓ Auth parameter removed from URL
[OAuth] Saving token to localStorage...
[OAuth] ✓ Token saved to localStorage
[OAuth] Making request to /v1/user/info...
[OAuth] ✓ User data received successfully
[OAuth] User email: example@gmail.com
[OAuth] ✓ All checks passed, navigating to /knowledge
[OAuth] ==================== OAuth Callback End ====================
```

### 3. Проверить localStorage

В Developer Tools:
1. Перейдите на вкладку **Application** (Chrome) или **Storage** (Firefox)
2. Слева найдите **Local Storage** → ваш домен
3. Проверьте наличие ключей:
   - `Authorization` - должен содержать JWT токен
   - `userInfo` - должен содержать JSON с данными пользователя
   - `Token` - должен содержать тот же токен

### 4. Если проблема всё ещё есть

**Шаг А**: Скопируйте ВСЕ логи из консоли браузера и отправьте мне

**Шаг Б**: Проверьте логи Docker контейнера:
```bash
# На AWS сервере
docker compose logs -f ragflow | grep -E "OAuth|oauth|/v1/user"
```

**Шаг В**: Проверьте Network tab в DevTools:
1. Откройте вкладку **Network** в DevTools
2. Повторите процесс входа через Google
3. Найдите запрос к `/v1/user/info`
4. Посмотрите:
   - **Request Headers**: есть ли заголовок `Authorization: Bearer ...`
   - **Response**: что возвращает сервер (код 200 или ошибка?)

## 🐛 Что исправлено в коде

### Ключевое изменение:
**РАНЬШЕ**: 
1. Сохраняли токен в localStorage
2. Делали запрос к `/v1/user/info`
3. Удаляли параметр `auth` из URL

**Проблема**: `getAuthorization()` сначала проверяет URL параметр `auth`, потом localStorage.  
Поэтому запрос к `/v1/user/info` использовал токен из URL, а после редиректа токена в URL уже не было.

**СЕЙЧАС**:
1. Сохраняем токен в localStorage
2. **✅ УДАЛЯЕМ параметр `auth` из URL**
3. Делаем запрос к `/v1/user/info` (использует токен из localStorage)

### Добавлено детальное логирование:
- `[OAuth]` - логи процесса OAuth callback
- `[Auth]` - логи проверки авторизации
- Каждый шаг логируется с ✓ (успех) или ✗ (ошибка)
- В случае ошибки выводится полный stack trace

## 📊 Ожидаемое поведение

1. ✅ Пользователь нажимает "Sign in with Google"
2. ✅ Авторизуется через Google
3. ✅ Перенаправляется на `/?auth={token}`
4. ✅ Токен сохраняется в localStorage
5. ✅ Параметр `auth` удаляется из URL
6. ✅ Запрашиваются данные пользователя `/v1/user/info`
7. ✅ Данные сохраняются в localStorage
8. ✅ Редирект на `/knowledge`
9. ✅ При переходе на другие страницы пользователь остаётся авторизованным

## ❓ Что делать если не работает

Пришлите мне:
1. ✅ Все логи из консоли браузера (скриншот или текст)
2. ✅ Содержимое localStorage (скриншот Application/Storage tab)
3. ✅ Network запрос к `/v1/user/info` (Headers + Response)
4. ✅ Логи Docker контейнера `docker compose logs ragflow | tail -100`

И я быстро найду проблему!
