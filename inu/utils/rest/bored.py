from typing import *
import aiohttp
import hikari

from utils import Colors
{
  "activity": "Make a couch fort",
  "type": "recreational",
  "participants": 1,
  "price": 0,
  "link": "",
  "key": "2352669",
  "accessibility": 0.08
}
class BoredIdea:
    def __init__(self, response: Dict[str, Union[str, float, int]]):
        self.response = response
        self.activity: str = response["activity"]
        self.type: str = response["type"]
        self.participants: int = response["participants"]
        self.price: int = response["price"]
        self.link: str = response["link"]
        self.key: str = response["key"]
        self.accessibility: float = response["accessibility"]

    @property
    def embed(self) -> hikari.Embed:
        return hikari.Embed(
            title=f"{self.activity}",
            description=f"{self.type} | {self.participants} participants | {self.price}€ | {self.accessibility * 100}% accessibility",
            color=Colors.from_name("mediumslateblue"),    
        )

class BoredAPI:
    Endpoint = "https://www.boredapi.com/api/activity/"
    @classmethod
    async def fetch_idea(cls) -> BoredIdea:
        async with aiohttp.ClientSession() as session:
            async with session.get(cls.Endpoint) as resp:
                json_resp = await resp.json()
        return BoredIdea(json_resp)
