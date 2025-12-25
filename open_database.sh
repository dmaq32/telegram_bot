#!/bin/bash
echo "=== ОТКРЫВАЮ БАЗУ ДАННЫХ ==="

# Останавливаем бота
echo "1. Останавливаю бота..."
pkill -f "python main.py" 2>/dev/null
sleep 1

# Создаем копию БД
echo "2. Создаю копию БД..."
cp data/db.sqlite3 /tmp/bot_database.sqlite3

# Открываем в SQLite Browser
echo "3. Открываю SQLite Browser..."
sqlitebrowser /tmp/bot_database.sqlite3

echo "Готово! База открыта."
echo "Оригинал: ~/projects/tg_bot/data/db.sqlite3"
echo "Копия: /tmp/bot_database.sqlite3"
