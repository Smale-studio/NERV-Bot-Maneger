# 🔵 MAGI Bot — Система NERV

Telegram-бот на базе трёх суперкомпьютеров MAGI из Евангелиона.  
Работает через OpenRouter (DeepSeek + Qwen-VL). Запускается как systemd-сервис на Ubuntu.

---

## ⚡ Установка на VPS (Ubuntu 24.04)

### 1. Загрузи файлы на сервер

```bash
scp -r magi_bot/ root@ВАШ_IP:/root/
```

### 2. Подключись к серверу и перейди в папку

```bash
ssh root@ВАШ_IP
cd /root/magi_bot
```

### 3. Создай виртуальное окружение и установи зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Создай .env файл с твоими данными

```bash
cp .env.example .env
nano .env
```

Заполни три значения:
- `TELEGRAM_TOKEN` — токен от @BotFather
- `OPENROUTER_API_KEY` — ключ с openrouter.ai
- `ADMIN_ID` — твой Telegram ID (узнать у @userinfobot)

### 5. Проверь что бот запускается

```bash
source venv/bin/activate
python bot.py
```

Если всё ок — Ctrl+C и идём дальше.

### 6. Установи systemd сервис

```bash
cp magi_bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable magi_bot
systemctl start magi_bot
```

### 7. Проверь статус

```bash
systemctl status magi_bot
```

---

## 📋 Команды бота

| Команда | Кто | Описание |
|---------|-----|----------|
| `/help` | все | Справка |
| `/think [вопрос]` | все | Совет трёх MAGI |
| `/view_thinking` | все | Последнее рассуждение совета |
| `/clear` | admin | Очистить память текущего чата |
| `/clear all` | admin | Очистить всю память |
| `/clear [chat_id]` | admin | Очистить память конкретного чата |

Панель администратора (инлайн-кнопки) появляется в **личке с ботом**.

---

## 🔧 Полезные команды systemd

```bash
# Логи в реальном времени
journalctl -u magi_bot -f

# Перезапуск
systemctl restart magi_bot

# Остановить
systemctl stop magi_bot
```

---

## 🗂 Структура проекта

```
magi_bot/
├── bot.py              # Точка входа
├── config.py           # Конфигурация
├── database.py         # SQLite (память)
├── magi_ai.py          # ИИ логика и промпты
├── handlers/
│   ├── messages.py     # Обработка сообщений
│   ├── commands.py     # /команды
│   └── admin.py        # Панель администратора
├── data/               # База данных (создаётся автоматически)
├── .env                # Твои секреты (не коммить!)
├── .env.example        # Шаблон
├── requirements.txt
└── magi_bot.service    # systemd
```
