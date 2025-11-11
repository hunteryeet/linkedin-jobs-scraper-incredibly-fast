thonimport logging
from typing import List, Optional

logger = logging.getLogger("proxy_manager")

class ProxyManager:
    """
    Extremely lightweight proxy rotator.

    Expects a list of proxy URLs such as:
      http://user:pass@host:port
      https://host:port
    """

    def __init__(self, proxies: List[str]) -> None:
        self._proxies = proxies
        self._index = 0

    def has_proxies(self) -> bool:
        return bool(self._proxies)

    def get_proxy(self) -> Optional[str]:
        if not self._proxies:
            return None
        proxy = self._proxies[self._index]
        self._index = (self._index + 1) % len(self._proxies)
        logger.debug("Using proxy %s", proxy)
        return proxy

    def add_proxy(self, proxy: str) -> None:
        if proxy not in self._proxies:
            self._proxies.append(proxy)
            logger.info("Added new proxy; total now %d", len(self._proxies))