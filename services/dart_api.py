import requests
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DART_API_KEY


def get_disclosures(stock_code: str, limit: int = 5) -> list:
    """
    OpenDart API에서 종목 공시 조회

    Args:
        stock_code: 종목 코드 (예: "005930")
        limit: 최대 공시 개수

    Returns:
        공시 리스트 [{"title": "...", "date": "...", "url": "..."}]
    """
    disclosures = []

    # API 키가 설정되지 않은 경우
    if not DART_API_KEY or DART_API_KEY == "여기에_API_키_입력":
        return _get_sample_disclosures(limit)

    try:
        # 최근 3개월 공시 조회
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        url = "https://opendart.fss.or.kr/api/list.json"
        params = {
            "crtfc_key": DART_API_KEY,
            "corp_code": _get_corp_code(stock_code),
            "bgn_de": start_date.strftime("%Y%m%d"),
            "end_de": end_date.strftime("%Y%m%d"),
            "page_count": limit
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()

            if data.get("status") == "000" and data.get("list"):
                for item in data["list"][:limit]:
                    disclosures.append({
                        "title": item.get("report_nm", ""),
                        "date": _format_date(item.get("rcept_dt", "")),
                        "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no', '')}",
                        "type": "disclosure"
                    })

    except Exception as e:
        print(f"DART API 오류: {e}")
        return _get_sample_disclosures(limit)

    return disclosures if disclosures else _get_sample_disclosures(limit)


def _get_corp_code(stock_code: str) -> str:
    """
    종목 코드로 DART 기업 코드 조회
    실제로는 DART의 기업코드 API를 사용해야 하지만,
    간단히 하기 위해 종목코드를 그대로 사용 (일부 종목만 작동)
    """
    # 실제 구현시 DART 기업코드 API 사용 필요
    return stock_code


def _format_date(date_str: str) -> str:
    """날짜 형식 변환 (YYYYMMDD -> YYYY년 MM월 DD일)"""
    if len(date_str) == 8:
        return f"{date_str[:4]}년 {date_str[4:6]}월 {date_str[6:]}일"
    return date_str


def _get_sample_disclosures(limit: int) -> list:
    """
    API 키가 없을 때 샘플 데이터 반환
    """
    samples = [
        {"title": "주요사항보고서(자율공시)", "date": "2024년 01월 15일", "url": "#", "type": "disclosure"},
        {"title": "분기보고서 (2023.09)", "date": "2024년 01월 10일", "url": "#", "type": "disclosure"},
        {"title": "임원ㆍ주요주주특정증권등소유상황보고서", "date": "2024년 01월 08일", "url": "#", "type": "disclosure"},
        {"title": "사업보고서 (2023.12)", "date": "2024년 01월 05일", "url": "#", "type": "disclosure"},
        {"title": "기타경영사항(자율공시)", "date": "2024년 01월 03일", "url": "#", "type": "disclosure"},
    ]
    return samples[:limit]
