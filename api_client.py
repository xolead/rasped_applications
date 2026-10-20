import requests


class ForemAPIError(Exception):
    """Исключение для ошибок Forem API."""
    pass


class ForemClient:
    BASE_URL = "https://dev.to/api"
    ACCEPT_HEADER = "application/vnd.forem.api-v1+json"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def _headers(self, auth: bool = False) -> dict:
        headers = {
            "accept": self.ACCEPT_HEADER,
            "Content-Type": "application/json",
        }
        if auth:
            if not self.api_key:
                raise ForemAPIError(
                    "Для этой операции требуется api-key. "
                    "Выполните аутентификацию."
                )
            headers["api-key"] = self.api_key
        return headers

    def _handle(self, response: requests.Response):
        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise ForemAPIError(
                f"HTTP {response.status_code}: {detail}"
            )
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def verify_key(self) -> dict:
        url = f"{self.BASE_URL}/users/me"
        r = requests.get(url, headers=self._headers(auth=True), timeout=15)
        return self._handle(r)

    def create_article(self, title: str, body_markdown: str,
                       published: bool = False, tags: str = "") -> dict:
        url = f"{self.BASE_URL}/articles"
        payload = {
            "article": {
                "title": title,
                "body_markdown": body_markdown,
                "published": published,
                "tags": tags,
            }
        }
        r = requests.post(url, json=payload,
                          headers=self._headers(auth=True), timeout=15)
        return self._handle(r)

    def get_article(self, article_id: int) -> dict:
        url = f"{self.BASE_URL}/articles/{article_id}"
        r = requests.get(url, headers=self._headers(), timeout=15)
        return self._handle(r)

    def list_my_articles(self) -> list:
        url = f"{self.BASE_URL}/articles/me"
        r = requests.get(url, headers=self._headers(auth=True), timeout=15)
        return self._handle(r)

    def update_article(self, article_id: int, **fields) -> dict:
        url = f"{self.BASE_URL}/articles/{article_id}"
        payload = {"article": fields}
        r = requests.put(url, json=payload,
                         headers=self._headers(auth=True), timeout=15)
        return self._handle(r)

    def unpublish_article(self, article_id: int) -> dict:
        return self.update_article(article_id, published=False)