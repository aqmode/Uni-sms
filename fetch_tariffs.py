import asyncio
import json
import logging
from bot.api import OnlineSimAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def fetch_and_save_tariffs():
    """
    Fetches both 'buy' and 'rent' tariffs from the API and saves them
    to a local JSON file.
    """
    logging.info("Инициализация API...")
    # This will use the key from settings.py or environment variables
    api = OnlineSimAPI()

    tariffs_data = {
        "buy": None,
        "rent": None
    }

    try:
        logging.info("Загрузка тарифов для покупки (getTariffs)...")
        buy_tariffs = await api.get_tariffs()
        if buy_tariffs.get("response") == "1":
            tariffs_data["buy"] = buy_tariffs
            logging.info("Тарифы для покупки успешно загружены.")
        else:
            logging.error(f"Не удалось загрузить тарифы для покупки: {buy_tariffs.get('error_msg', 'Неизвестная ошибка')}")

        logging.info("Загрузка тарифов для аренды (tariffsRent)...")
        rent_tariffs = await api.get_tariffs_rent()
        if rent_tariffs.get("response") == "1":
            tariffs_data["rent"] = rent_tariffs
            logging.info("Тарифы для аренды успешно загружены.")
        else:
            logging.error(f"Не удалось загрузить тарифы для аренды: {rent_tariffs.get('error_msg', 'Неизвестная ошибка')}")

    except Exception as e:
        logging.error(f"Произошла критическая ошибка при загрузке тарифов: {e}")
        return

    if tariffs_data["buy"] and tariffs_data["rent"]:
        try:
            with open("tariffs.json", "w", encoding="utf-8") as f:
                json.dump(tariffs_data, f, ensure_ascii=False, indent=4)
            logging.info("✅ Все тарифы успешно сохранены в файл `tariffs.json`.")
        except IOError as e:
            logging.error(f"Не удалось записать данные в файл: {e}")
    else:
        logging.warning("⚠️ Не все данные были получены, файл `tariffs.json` не был создан/обновлен.")


if __name__ == "__main__":
    # This check is needed because the script is outside the main bot logic
    # and needs to be able to find the `bot` package.
    # It assumes you run it from the project root directory.
    import sys
    import os
    sys.path.append(os.getcwd())

    from config import ONLINE_SIM_API_KEY
    if not ONLINE_SIM_API_KEY or ONLINE_SIM_API_KEY == "YOUR_ONLINE_SIM_API_KEY":
        logging.error("Пожалуйста, сначала заполните ONLINE_SIM_API_KEY в файле settings.py")
    else:
        asyncio.run(fetch_and_save_tariffs())
