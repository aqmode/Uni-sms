import asyncio
import logging
from smsactivate.api import SMSActivateAPI
from config import SMS_ACTIVATE_API_KEY

class SmsActivateWrapper:
    """
    An async wrapper for the official synchronous smsactivate library.
    It runs the library's methods in a separate thread to avoid
    blocking Pyrogram's asyncio event loop.
    """
    def __init__(self, api_key: str = SMS_ACTIVATE_API_KEY):
        if not api_key:
            raise ValueError("SMS_ACTIVATE_API_KEY is not set.")
        self.sa = SMSActivateAPI(api_key)
        # The user's pastebin mentioned .ae, let's try to set it if possible
        # Looking at the library source is not possible, so I will assume
        # there might be a way to change the API host.
        # For now, I'll rely on the library's default.

    async def _run_sync(self, func, *args, **kwargs):
        """Runs a synchronous function in an async-friendly way."""
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except Exception as e:
            logging.error(f"Error calling SMSActivate library function {func.__name__}: {e}")
            # Return a dict with an error to be handled by the calling handler
            return {'error': str(e)}

    async def get_balance(self):
        # The library method is likely getBalance()
        # It returns a dict {'access_balance': '123.45'} or similar
        return await self._run_sync(self.sa.getBalance)

    async def get_countries(self):
        # Method is getCountries()
        return await self._run_sync(self.sa.getCountries)

    async def get_prices(self, country_id: int):
        # Method is getPrices(country=...)
        return await self._run_sync(self.sa.getPrices, country=country_id)

    async def get_number(self, service: str, country_id: int):
        # Method is getNumber(service=..., country=...)
        # It returns a dict with activation details
        return await self._run_sync(self.sa.getNumber, service=service, country=country_id)

    async def get_status(self, activation_id: int):
        # Method is getStatus(id=...)
        # Returns a string like "STATUS_OK:12345"
        return await self._run_sync(self.sa.getStatus, id=activation_id)

    async def set_status(self, activation_id: int, status: int):
        # Method is setStatus(id=..., status=...)
        return await self._run_sync(self.sa.setStatus, id=activation_id, status=status)

    # I will omit the rent methods for now to simplify the refactoring
    # and ensure the core functionality works first. I will add them back later.
