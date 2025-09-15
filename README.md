# Auction7 - Аукционная платформа

## Описание проекта
Веб-платформа для проведения аукционов с возможностью регистрации продавцов и покупателей, создания лотов, участия в торгах.

## 🚀 Готовность к деплою

### ✅ Статус готовности к Render
Проект готов к деплою на Render. Все основные зависимости установлены и настроены.

## 🛠 Установка и запуск локально

### Требования
- Python 3.10+
- pip

### Установка зависимостей
```bash
pip install -r requirements.txt
```

### Переменные окружения
Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

Отредактируйте `.env` и установите свои значения:
- `SECRET_KEY` - секретный ключ для Flask (обязательно изменить для продакшена)
- `DATABASE_URL` - URL базы данных (Render предоставит автоматически)

### Запуск локально
```bash
python run.py
```

### Запуск с Gunicorn (как на Render)
```bash
gunicorn run:app
```

## 🌐 Деплой на Render

### Конфигурация Render
1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: `gunicorn run:app` (уже настроен в Procfile)

### Переменные окружения на Render
Установите следующие переменные в настройках Render:
- `SECRET_KEY` - генерируйте надежный секретный ключ
- `DATABASE_URL` - Render предоставит автоматически для PostgreSQL
- `FLASK_ENV` - `production`
- `FLASK_DEBUG` - `false`

### Файлы для деплоя
- ✅ `Procfile` - команда запуска для Render
- ✅ `requirements.txt` - все зависимости включены
- ✅ `.gitignore` - исключает ненужные файлы
- ✅ Конфигурация продакшена в коде

## 📁 Структура проекта
```
auction7/
├── auction7/app/           # Основное приложение Flask
│   ├── models/            # Модели базы данных
│   ├── routes/            # Маршруты (blueprints)
│   ├── templates/         # HTML шаблоны
│   ├── static/           # Статические файлы
│   └── __init__.py       # Фабрика приложения
├── run.py                # Точка входа
├── requirements.txt      # Зависимости Python
├── Procfile              # Конфигурация для Render
└── .env.example         # Пример переменных окружения
```

## ⚠️ Известные проблемы
1. **Blockchain Payment Module**: Модуль `blockchain_payments` временно отключен (закомментирован). Функции оплаты через блокчейн будут возвращать заглушки до исправления путей импорта.
2. **Duplicate Structure**: Обнаружена дублированная структура в `auction7-main/`, но она не влияет на работу основного приложения.

## 🔧 Технологический стек
- **Backend**: Flask, SQLAlchemy, Flask-Login, Flask-Migrate
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLite (разработка), PostgreSQL (продакшн на Render)
- **Server**: Gunicorn
- **Additional**: Web3, OpenAI integration

## 📝 Статус проверки

### ✅ Проверено и готово
- [x] Flask приложение создается без ошибок
- [x] Gunicorn запускается корректно
- [x] Все базовые зависимости установлены
- [x] Импорты исправлены
- [x] Конфигурация поддерживает продакшн переменные
- [x] .gitignore настроен
- [x] Procfile корректен
- [x] Шаблоны находятся в правильных директориях

### ⚠️ Требует внимания
- [ ] Blockchain payment функции (временно отключены)
- [ ] Тестирование всех маршрутов в продакшене
- [ ] Миграции базы данных при первом деплое

## 🚀 Команды для коммита и пуша
```bash
git add .
git commit -m "Ready for Render deployment - all issues fixed"
git push origin main
```

Проект готов к деплою на Render! 🎉