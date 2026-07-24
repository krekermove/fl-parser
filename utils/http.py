"""Асинхронный HTTP-клиент с ретраями, таймаутами, UA-ротацией и прокси."""
from __future__ import annotations

import asyncio
import random
from types import TracebackType

import aiohttp
from loguru import logger

from utils.user_agents import default_headers


class HttpClient:
    """Обёртка над aiohttp.ClientSession с защитой от блокировок.

    Возможности:
      * случайная задержка между запросами;
      * ротация User-Agent на каждый запрос;
      * повторные попытки с экспоненциальной паузой;
      * таймаут запроса;
      * поддержка HTTP-прокси.
    """

    def __init__(
        self,
        *,
        timeout: int = 20,
        retries: int = 3,
        delay_min: float = 1.5,
        delay_max: float = 4.0,
        proxy: str | None = None,
    ) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._retries = max(1, retries)
        self._delay_min = delay_min
        self._delay_max = delay_max
        self._proxy = proxy
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "HttpClient":
        self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _sleep_random(self) -> None:
        """Случайная пауза, имитирующая поведение человека."""
        await asyncio.sleep(random.uniform(self._delay_min, self._delay_max))

    async def get_text(self, url: str, **kwargs: object) -> str | None:
        """Выполняет GET и возвращает тело ответа как текст.

        При ошибках делает повторные попытки. Возвращает None, если все
        попытки исчерпаны.
        """
        if self._session is None:
            raise RuntimeError("HttpClient используется вне контекстного менеджера")

        last_error: Exception | None = None

        for attempt in range(1, self._retries + 1):
            await self._sleep_random()
            headers = default_headers()
            try:
                async with self._session.get(
                    url,
                    headers=headers,
                    proxy=self._proxy,
                    ssl=False,
                    allow_redirects=True,
                    **kwargs,  # type: ignore[arg-type]
                ) as response:
                    if response.status == 200:
                        return await response.text()

                    # 403/429 — вероятная блокировка/капча: логируем и пробуем ещё раз.
                    logger.warning(
                        "GET {} -> HTTP {} (попытка {}/{})",
                        url,
                        response.status,
                        attempt,
                        self._retries,
                    )
                    last_error = aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status,
                    )
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                last_error = err
                logger.warning(
                    "Ошибка запроса {} (попытка {}/{}): {}",
                    url,
                    attempt,
                    self._retries,
                    err,
                )

            # Экспоненциальная пауза перед следующей попыткой.
            await asyncio.sleep(min(2 ** attempt, 10))

        logger.error("Не удалось получить {} после {} попыток: {}", url, self._retries, last_error)
        return None


__all__ = ["HttpClient"]
