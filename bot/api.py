import asyncio
import logging
import aiohttp
from config import SMS_ACTIVATE_API_KEY

class SmsActivateAPI:
    """
    An asynchronous wrapper for the sms-activate.ru API (v2).
    """
    BASE_URL = "https://api.sms-activate.ru/stubs/handler_api.php" # Using stub for safety, can be changed

    def __init__(self, api_key: str = SMS_ACTIVATE_API_KEY):
        self.api_key = api_key

    async def _request(self, action: str, params: dict = None):
        """Makes a request to the API."""
        if params is None:
            params = {}
        params['api_key'] = self.api_key
        params['action'] = action

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params, timeout=30) as response:
                    response.raise_for_status()
                    # The API returns plain text for some calls, JSON for others.
                    text_response = await response.text()
                    try:
                        # Try to parse as JSON
                        return await response.json(content_type=None)
                    except aiohttp.ContentTypeError:
                        # If it fails, return the plain text
                        return text_response
        except asyncio.TimeoutError:
            raise Exception("TimeoutError")
        except aiohttp.ClientError as e:
            raise Exception(f"Network error: {e}")

    async def get_balance(self):
        """Get account balance."""
        return await self._request("getBalance")

    async def get_prices(self, service: str = '', country: int = None):
        """Get prices and counts for services."""
        params = {'service': service}
        if country is not None:
            params['country'] = country
        return await self._request("getPrices", params)

    async def get_number(self, service: str, country: int, operator: str = None):
        """Get a number for activation."""
        params = {'service': service, 'country': country}
        if operator:
            params['operator'] = operator
        # Using V2 for the structured JSON response
        return await self._request("getNumberV2", params)

    async def get_status(self, activation_id: int):
        """Get the status of an activation."""
        return await self._request("getStatus", {'id': activation_id})

    async def set_status(self, activation_id: int, status: int):
        """
        Set the status of an activation.
        status: 1=ready, 3=request another sms, 6=finish, 8=cancel
        """
        return await self._request("setStatus", {'id': activation_id, 'status': status})

    # --- Rent Methods ---

    async def get_rent_services_and_countries(self):
        """Get available services and countries for rent."""
        return await self._request("getRentServicesAndCountries")

    async def get_rent_number(self, service: str, country: int, rent_time: int = 4, operator: str = None):
        """Rent a number."""
        params = {
            'service': service,
            'country': country,
            'rent_time': rent_time
        }
        if operator:
            params['operator'] = operator
        return await self._request("getRentNumber", params)

    async def get_rent_status(self, activation_id: int):
        """Get the status and SMS list for a rental."""
        return await self._request("getRentStatus", {'id': activation_id})

    async def set_rent_status(self, activation_id: int, status: int):
        """Set the status of a rental. 1=finish, 2=cancel."""
        return await self._request("setRentStatus", {'id': activation_id, 'status': status})

    async def continue_rent_number(self, activation_id: int, rent_time: int = 4):
        """Extend a rental."""
        return await self._request("continueRentNumber", {'id': activation_id, 'rent_time': rent_time})
