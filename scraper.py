import asyncio
import subprocess
from time import sleep

from pyppeteer import launch
from pyppeteer.page import Page
from trafilatura import extract

NUM_RELOADS = 1

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/83.0.4103.97 Safari/537.36",
}
EXTRA_HTTP_HEADERS = {"Accept-Language": "en-US;q=0.8,en;q=0.7"}

WAIT_COND = ["domcontentloaded", "networkidle0"]


async def extract_article(url: str) -> str:
    """
    Extract the article from the URL with Python's Trafilatura library and Pyppeteer
    """
    # Scrape the page with Pyppeteer headless browser
    scraper = Scraper()
    await scraper.set_browser()
    try:
        page: Page = await scraper.get_response(url)
    except:
        await kill_browser_badly(scraper.browser)
        await scraper.set_browser()
        page: Page = await scraper.get_response(url)

    content = await page.content()

    # Extract content from the HTML page
    article = extract(content, favor_recall=True)
    return article


async def kill_browser_badly(browser):
    browser.pages().close()
    pid = browser.process.pid
    await browser.close()
    subprocess.Popen(f"pkill -f -P {pid}", shell=True)
    subprocess.Popen(f"pkill -f {pid}", shell=True)
    sleep(3)


class Scraper:
    def __init__(self, attempts=1, timeout: int = 25, headless=True):
        self.attempts = attempts
        self.timeout = timeout
        self.headless = headless
        self.browser = None

    async def set_browser(self):
        if self.browser:
            # await kill_browser_badly(self.browser)
            pass
        else:
            self.browser = await launch(**self._get_browser_args())

    def _get_browser_args(self) -> dict:
        return {
            "headless": self.headless,
            "args": [
                "--lang=en-GB",
                # "--no-sandbox",
                # "--single-process",
                # "--disable-dev-shm-usage",
                # "--no-zygote",
                # "--ignore-certificate-errors",
                # "--ignore-certificate-errors-spki-list",
                '--user-agent="{}"'.format(HEADERS["User-Agent"]),
            ],
            # "handleSIGINT": False,
            # "handleSIGTERM": False,
            # "handleSIGHUP": False,
            # "ignoreHTTPSErrors": True,
        }

    async def get_response(self, url: str) -> Page:
        print("check the browser")
        if not self.browser:
            await self.set_browser()
        page: Page = (await self.browser.pages())[0]

        # set http headers
        _ = await asyncio.wait_for(
            page.setExtraHTTPHeaders(EXTRA_HTTP_HEADERS), timeout=self.timeout
        )
        # set user agent
        _ = await asyncio.wait_for(
            asyncio.create_task(page.setUserAgent(HEADERS["User-Agent"])),
            timeout=self.timeout,
        )
        # bring page to front
        _ = await asyncio.wait_for(
            asyncio.create_task(page.bringToFront()), timeout=self.timeout
        )
        # load webpage
        load_task = asyncio.create_task(
            page.goto(url, waitUntil=WAIT_COND, timeout=30000)
        )
        response = await asyncio.wait_for(load_task, timeout=self.timeout)
        status_code = response.status
        if status_code != 200:
            raise Exception("Bad status code")
        return page
