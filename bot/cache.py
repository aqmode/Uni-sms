import json
import logging

# In-memory cache for the tariffs file
_tariffs_cache = {}

def load_tariffs_from_file():
    """
    Loads the tariffs from the local tariffs.json file into memory.
    Returns the cached data. Raises an exception if the file is not found.
    """
    global _tariffs_cache
    if _tariffs_cache:
        return _tariffs_cache

    try:
        logging.info("Загрузка локальных тарифов из `tariffs.json`...")
        with open("tariffs.json", "r", encoding="utf-8") as f:
            _tariffs_cache = json.load(f)
        logging.info("Локальные тарифы успешно загружены в кэш.")
        return _tariffs_cache
    except FileNotFoundError:
        logging.error("Файл `tariffs.json` не найден! Пожалуйста, запустите `python fetch_tariffs.py` для его создания.")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка при чтении файла `tariffs.json`: {e}")
        raise

def get_buy_tariffs():
    """Returns the 'buy' part of the tariffs cache."""
    cache = load_tariffs_from_file()
    return cache.get("buy")

def get_rent_tariffs():
    """Returns the 'rent' part of the tariffs cache."""
    cache = load_tariffs_from_file()
    return cache.get("rent")
