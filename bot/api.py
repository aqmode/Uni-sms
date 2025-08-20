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
        if not api_key or api_key == "YOUR_SMS_ACTIVATE_API_KEY":
            raise ValueError("SMS_ACTIVATE_API_KEY is not set or is invalid.")
        self.sa = SMSActivateAPI(api_key)

    async def _run_sync(self, func, *args, **kwargs):
        """Runs a synchronous function in an async-friendly way."""
        try:
            # Use asyncio.to_thread to run the sync function in a separate thread
            return await asyncio.to_thread(func, *args, **kwargs)
        except Exception as e:
            logging.error(f"Error calling SMSActivate library function {func.__name__}: {e}")
            return {'error': str(e)}

    # Main methods
    async def get_balance(self):
        return await self._run_sync(self.sa.getBalance)

    async def get_countries(self):
        return await self._run_sync(self.sa.getCountries)

    async def get_prices(self, country: int, service: str = None):
        params = {'country': country}
        if service:
            params['service'] = service
        return await self._run_sync(self.sa.getPrices, **params)

    async def get_number(self, service: str, country: int):
        return await self._run_sync(self.sa.getNumber, service=service, country=country)

    async def get_status(self, activation_id: int):
        return await self._run_sync(self.sa.getStatus, id=activation_id)

    async def set_status(self, activation_id: int, status: int):
        return await self._run_sync(self.sa.setStatus, id=activation_id, status=status)

    # Rent methods
    async def get_rent_services_and_countries(self):
        return await self._run_sync(self.sa.getRentServicesAndCountries)

    async def get_rent_number(self, service: str, country: int, rent_time: int):
        return await self._run_sync(self.sa.getRentNumber, service=service, country=country, time=rent_time)

    async def get_rent_status(self, rent_id: int):
        return await self._run_sync(self.sa.getRentStatus, id=rent_id)

    async def set_rent_status(self, rent_id: int, status: int):
        return await self._run_sync(self.sa.setRentStatus, id=rent_id, status=status)
