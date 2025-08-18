import aiohttp
from config import ONLINE_SIM_API_KEY

class OnlineSimAPI:
    """
    An asynchronous wrapper for the onlinesim.io API.
    """
    BASE_URL = "https://onlinesim.io/api"

    def __init__(self, api_key: str = ONLINE_SIM_API_KEY):
        self.api_key = api_key

    async def _request(self, endpoint: str, params: dict = None):
        """Makes a request to the API."""
        if params is None:
            params = {}
        params['apikey'] = self.api_key

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/{endpoint}", params=params, timeout=15) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            # Re-raise as a generic exception that handlers can catch
            raise Exception(f"Network error communicating with Onlinesim API: {e}")

    async def get_balance(self):
        """Get account balance."""
        return await self._request("getBalance.php")

    async def get_tariffs(self):
        """Get tariffs for purchasing numbers."""
        return await self._request("getTariffs.php")

    async def get_num(self, service: str, country: int):
        """Purchase a number."""
        params = {'service': service, 'country': country}
        return await self._request("getNum.php", params)

    async def get_state(self, tzid: int):
        """Get the state of an operation."""
        params = {'tzid': tzid}
        return await self._request("getState.php", params)

    async def set_operation_ok(self, tzid: int):
        """Set operation as completed."""
        params = {'tzid': tzid}
        return await self._request("setOperationOk.php", params)

    async def get_tariffs_rent(self):
        """Get tariffs for renting numbers."""
        return await self._request("tariffsRent.php")

    async def get_rent_num(self, service: str, country: int, days: int = 30):
        """Rent a number."""
        params = {'service': service, 'country': country, 'days': days}
        return await self._request("getRentNum.php", params)

    async def extend_rent_state(self, tzid: int, days: int = 30):
        """Extend a number rental."""
        params = {'tzid': tzid, 'days': days}
        return await self._request("extendRentState.php", params)

    async def get_rent_state(self, tzid: int):
        """Get the state of a rental."""
        params = {'tzid': tzid}
        return await self._request("getRentState.php", params)

    async def close_rent_num(self, tzid: int):
        """Close a number rental."""
        params = {'tzid': tzid}
        return await self._request("closeRentNum.php", params)

    async def get_free_list(self):
        """Get the list of free numbers."""
        return await self._request("getFreeList.php")
