#!/bin/bash

# This script automates the setup and execution of the bot for macOS and Linux.

# Check if a virtual environment directory exists
if [ ! -d "venv" ]; then
    echo "Создаю виртуальное окружение..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Ошибка: Не удалось создать виртуальное окружение. Убедитесь, что у вас установлен python3."
        exit 1
    fi
fi

# Activate the virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Устанавливаю/обновляю зависимости из requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Ошибка: Не удалось установить зависимости."
    exit 1
fi

# Run the bot
echo "Запускаю бота... Нажмите CTRL+C для остановки."
python main.py

# Deactivate the environment when the script is stopped
deactivate
