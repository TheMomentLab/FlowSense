import requests
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def get_news(stock_code: str, stock_name: str, limit: int = 10) -> list:
    news_list = _get_news_from_api(stock_code, limit)
    if news_list:
        return news_list
    return _get_news_from_scraping(stock_code, limit)


def _get_news_from_api(stock_code: str, limit: int) -> list:
    news_list = []
    try:
        url = f"https://m.stock.naver.com/api/news/stock/{stock_code}?pageSize={limit}"
        response = requests.get(url, headers=_HEADERS, timeout=10)

        if response.status_code != 200:
            return []

        clusters = response.json()
        if not isinstance(clusters, list):
            return []

        for cluster in clusters:
            items = cluster.get("items", [])
            for item in items:
                title = item.get("title", "").strip()
                if not title:
                    continue

                dt_str = item.get("datetime", "")
                date = (
                    f"{dt_str[:4]}.{dt_str[4:6]}.{dt_str[6:8]}"
                    if len(dt_str) >= 8
                    else ""
                )
                body = item.get("body", "").strip()
                office_id = item.get("officeId", "")
                article_id = item.get("articleId", "")
                article_url = (
                    f"https://n.news.naver.com/mnews/article/{office_id}/{article_id}"
                    if office_id and article_id
                    else ""
                )

                if not any(n["title"] == title for n in news_list):
                    news_list.append(
                        {
                            "title": title,
                            "summary": body[:200] if body else title,
                            "date": date,
                            "url": article_url,
                            "type": "news",
                        }
                    )

                if len(news_list) >= limit:
                    return news_list

    except Exception as e:
        print(f"[news_crawler] api error: {e}")

    return news_list


def _get_news_from_scraping(stock_code: str, limit: int) -> list:
    news_list = []
    try:
        url = f"https://finance.naver.com/item/news_news.naver?code={stock_code}"
        response = requests.get(url, headers=_HEADERS, timeout=10)
        response.encoding = "euc-kr"

        if response.status_code != 200:
            return news_list

        soup = BeautifulSoup(response.text, "html.parser")

        for row in soup.select("table.type5 tr")[: limit * 2]:
            title_tag = row.select_one("td.title a")
            date_tag = row.select_one("td.date")

            if title_tag and date_tag:
                title = title_tag.get_text(strip=True)
                date = date_tag.get_text(strip=True)
                href = title_tag.get("href", "")

                if not any(n["title"] == title for n in news_list):
                    news_list.append(
                        {
                            "title": title,
                            "summary": title,
                            "date": date,
                            "url": f"https://finance.naver.com{href}"
                            if href.startswith("/")
                            else href,
                            "type": "news",
                        }
                    )

                if len(news_list) >= limit:
                    break

    except Exception as e:
        print(f"[news_crawler] scraping error: {e}")

    return news_list


def get_disclosures(stock_code: str, limit: int = 10) -> list:
    disclosures = []

    try:
        url = (
            f"https://finance.naver.com/item/news_notice.naver?code={stock_code}&page="
        )
        response = requests.get(url, headers=_HEADERS, timeout=10)
        response.encoding = "euc-kr"

        if response.status_code != 200:
            return disclosures

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("tr")

        for row in rows:
            tds = row.select("td")
            if len(tds) < 3:
                continue

            title_tag = tds[0].select_one("a")
            source = tds[1].get_text(strip=True)
            date = tds[2].get_text(strip=True)

            if title_tag and date:
                raw_title = title_tag.get_text(strip=True)
                href = title_tag.get("href", "")

                corp_prefix = f"{_get_corp_name_from_title(raw_title)} "
                title = (
                    raw_title.replace(corp_prefix, "", 1)
                    if raw_title.startswith(corp_prefix)
                    else raw_title
                )

                disclosures.append(
                    {
                        "title": title,
                        "date": date,
                        "url": f"https://finance.naver.com{href}"
                        if href.startswith("/")
                        else href,
                        "source": source,
                        "type": "disclosure",
                    }
                )

                if len(disclosures) >= limit:
                    break

    except Exception as e:
        print(f"[news_crawler] disclosure error: {e}")

    return disclosures


def _get_corp_name_from_title(title: str) -> str:
    for suffix in ["(주)", "(유)", "(사)"]:
        idx = title.find(suffix)
        if idx > 0:
            return title[: idx + len(suffix)]
    return ""


def get_news_detail(url: str) -> str:
    try:
        response = requests.get(url, headers=_HEADERS, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            content = soup.select_one("#dic_area, #articeBody, .article_body")
            if content:
                return content.get_text(strip=True)[:500]

    except Exception as e:
        print(f"[news_crawler] detail error: {e}")

    return ""
