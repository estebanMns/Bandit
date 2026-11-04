import httpx
import pytest
import respx

from bandit.directory.infrastructure.polite_fetcher import DisallowedUrlError, PoliteFetcher

ROBOTS = "User-agent: *\nDisallow: /index.php/\n"
LISTING = "https://www.policia.gov.co/los-mas-buscados-colombia?page=0"


@pytest.fixture
def fetcher():
    return PoliteFetcher(httpx.AsyncClient(), min_interval=0)


@pytest.fixture
def robots():
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://www.policia.gov.co/robots.txt").mock(
            return_value=httpx.Response(200, text=ROBOTS)
        )
        yield mock


async def test_fetches_the_allowed_listing(fetcher, robots):
    robots.get(LISTING).mock(return_value=httpx.Response(200, text="<main>Listado</main>"))

    assert "Listado" in await fetcher.fetch_text(LISTING)


@pytest.mark.parametrize(
    "url",
    [
        "https://sitio-malicioso.example/los-mas-buscados-colombia",
        "http://www.policia.gov.co/los-mas-buscados-colombia",
        "https://www.policia.gov.co/admin/config",
        "https://www.policia.gov.co/index.php/los-mas-buscados-colombia",
        "https://www.policia.gov.co.sitio-malicioso.example/los-mas-buscados-colombia",
    ],
)
async def test_refuses_urls_outside_the_allowlist(fetcher, robots, url):
    with pytest.raises(DisallowedUrlError):
        await fetcher.fetch_text(url)


async def test_refuses_what_robots_txt_forbids(robots):
    robots.get("https://www.policia.gov.co/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /\n")
    )

    with pytest.raises(DisallowedUrlError):
        await PoliteFetcher(httpx.AsyncClient(), min_interval=0).fetch_text(LISTING)


async def test_limits_the_download_size(fetcher, robots):
    url = "https://www.policia.gov.co/sites/default/files/grande.pdf"
    robots.get(url).mock(return_value=httpx.Response(200, content=b"x" * 2048))

    with pytest.raises(ValueError, match="tamaño"):
        await fetcher.fetch_bytes(url, max_bytes=1024)
