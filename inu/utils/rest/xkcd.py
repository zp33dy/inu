from typing import *
import random

import aiohttp
import hikari
from typing import *

class xkcdComicDict(TypedDict):
    month: str
    num: int
    link: str
    year: str
    news: str
    safe_title: str
    transcript: str
    alt: str
    img: str
    title: str
    day: str
    explanation_url: str

from utils import Colors

class xkcdAPI:
    BaseEndpoint = "https://xkcd.com/"
    ApproximateComicCount = 2800

    @classmethod
    def current_comic_endpoint(cls, *args) -> str:
        return cls.BaseEndpoint + "info.0.json"
    
    @classmethod
    def random_comic_endpoint(cls, *args) -> str:
        return cls.BaseEndpoint + f"{random.randint(1, cls.ApproximateComicCount)}/info.0.json"
    
    @classmethod
    def specific_comic_endpoint(cls, comic_id: int) -> str:
        return cls.BaseEndpoint + f"{comic_id}/info.0.json"
    
    @classmethod
    async def fetch_comic(cls, comic_url: str) -> xkcdComicDict | None:
        """
        Args:
        -----
        comic_url : str
            the url to fetch the comic from. Use one of the classmethods to get a valid url
        """
        json_resp = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(comic_url) as resp:
                    if resp.status >= 400:
                        return None
                    json_resp = await resp.json()
                    if not json_resp.get("link"):
                        if json_resp.get("num"):
                            json_resp["link"] = cls.BaseEndpoint + str(json_resp["num"])
                    if (num := json_resp.get("num")):
                        json_resp["explanation_url"] = f"https://www.explainxkcd.com/wiki/index.php/{num}"
                    return json_resp
        except aiohttp.ClientConnectorCertificateError as e:
                raise e
