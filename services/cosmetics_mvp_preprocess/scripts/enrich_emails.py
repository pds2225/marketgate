"""
이메일 확보 파이프라인
- 입력: buyer_candidate.csv (기업명, 국가, 웹사이트)
- 출력: 이메일이 채워진 buyer_candidate.csv
"""

import re
import requests
import pandas as pd
from urllib.parse import urlparse

def extract_domain_from_name(name: str) -> str:
    """기업명에서 도메인 추정"""
    # 간단한 휴리스틱
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    return f"{cleaned}.com"  # 추정

def search_hunter_email(domain: str, hunter_api_key: str) -> list:
    """Hunter.io API로 이메일 패턴 검색"""
    try:
        url = f"https://api.hunter.io/v2/domain-search"
        params = {"domain": domain, "api_key": hunter_api_key}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            emails = [e['value'] for e in data.get('data', {}).get('emails', [])]
            return emails
    except:
        pass
    return []

def scrape_contact_page(website: str) -> list:
    """기업 홈페이지에서 이메일 스크래핑 (공개 정보)"""
    try:
        resp = requests.get(website, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            # 이메일 정규식
            pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(pattern, resp.text)
            # 흔한 필터링
            filtered = [e for e in emails if not any(x in e.lower() for x in ['noreply', 'no-reply', 'example', 'domain'])]
            return list(set(filtered))
    except:
        pass
    return []

def enrich_emails(df: pd.DataFrame, hunter_api_key: str = "") -> pd.DataFrame:
    """데이터프레임에 이메일 확보"""
    df = df.copy()

    for idx, row in df.iterrows():
        emails = []

        # 1. 웹사이트가 있으면 스크래핑
        website = str(row.get('contact_website', ''))
        if website and website.startswith('http'):
            emails.extend(scrape_contact_page(website))

        # 2. Hunter.io (API 키 있을 때)
        if hunter_api_key and not emails:
            domain = extract_domain_from_name(str(row.get('normalized_name', '')))
            emails.extend(search_hunter_email(domain, hunter_api_key))

        # 저장
        if emails:
            df.at[idx, 'contact_email'] = emails[0]
            df.at[idx, 'has_contact'] = True

    return df

if __name__ == "__main__":
    # 사용 예시
    df = pd.read_csv("buyer_candidate.csv", encoding='utf-8-sig')
    df_enriched = enrich_emails(df, hunter_api_key="YOUR_HUNTER_API_KEY")
    df_enriched.to_csv("buyer_candidate_with_emails.csv", index=False, encoding='utf-8-sig')
