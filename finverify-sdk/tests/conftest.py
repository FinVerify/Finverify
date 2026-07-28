import pytest

from finverify.client import FinVerify
from finverify.async_client import AsyncFinVerify
from finverify.config import ClientConfig


@pytest.fixture
def cfg():
    return ClientConfig.resolve(base_url="https://test.finverify.local", max_retries=2)


@pytest.fixture
def sync_client(cfg):
    client = FinVerify(base_url=cfg.base_url, max_retries=cfg.max_retries)
    yield client
    client.close()


@pytest.fixture
async def async_client(cfg):
    client = AsyncFinVerify(base_url=cfg.base_url, max_retries=cfg.max_retries)
    yield client
    await client.aclose()
