
"""
NICE D&B API - 100개 샘플 테스트 코드
무료 테스트베드 사용 (일 100건)
"""

import requests
import pandas as pd
import json
from pathlib import Path

# NICE D&B Open API 테스트베드 정보
# 참고: https://openapi.nicednb.com/index.jsp
BASE_URL = "https://openapi.nicednb.com"
API_KEY = "YOUR_TEST_API_KEY"  # 테스트베드 신청 후 발급

def search_company_by_name(name: str, country_code: str) -> dict:
    """
    기업명 + 국가코드로 D&B 검색

    Args:
        name: 기업명 (예: "Lazada")
        country_code: ISO3 국가코드 (예: "SGP")

    Returns:
        {
            "found": True/False,
            "duns": "65-211-8522",
            "company_name": "Lazada Group",
            "match_score": 95,  # 매칭 확신도
            "api_response": {...}  # 원본 응답
        }
    """
    url = f"{BASE_URL}/api/search"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    params = {
        "companyName": name,
        "countryCode": country_code,
        "matchType": "F"  # Fuzzy(유사) 검색
    }

    resp = requests.get(url, headers=headers, params=params, timeout=30)

    if resp.status_code == 200:
        data = resp.json()

        # 검색 결과 파싱
        if data.get("matchCandidates"):
            best_match = data["matchCandidates"][0]
            return {
                "found": True,
                "duns": best_match.get("duns"),
                "company_name": best_match.get("primaryName"),
                "match_score": best_match.get("matchConfidenceCode"),
                "api_response": data
            }

    return {"found": False, "api_response": resp.text if resp.status_code != 200 else data}


def get_company_detail(duns: str) -> dict:
    """
    D-U-N-S 번호로 상세 기업정보 조회

    Returns:
        {
            "annual_sales": "$2.5B",  # 매출액
            "employees": 8000,        # 종업원수
            "credit_rating": "5A1",   # D&B 신용등급
            "year_started": 2012,     # 설립년도
            "industry": "E-commerce", # 산업분류
            "hq_location": "Singapore", # 본사 위치
            "family_tree": [...],     # 계열사 목록
            "watchlist": False        # 제재 여부
        }
    """
    url = f"{BASE_URL}/api/company/{duns}"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    resp = requests.get(url, headers=headers, timeout=30)

    if resp.status_code == 200:
        data = resp.json()
        return {
            "annual_sales": data.get("financials", {}).get("annualSales", {}).get("value"),
            "employees": data.get("numberOfEmployees"),
            "credit_rating": data.get("dnbAssessment", {}).get("creditRating", {}).get("rating"),
            "year_started": data.get("organization", {}).get("startDate"),
            "industry": data.get("industryCodes", [{}])[0].get("industryDescription"),
            "hq_location": data.get("primaryAddress", {}).get("addressLocality"),
            "family_tree": data.get("familyTreeMembers", []),
            "watchlist": data.get("watchlistIndicator") == "Y"
        }

    return {}


def grade_buyer(sales: str, employees: int, rating: str) -> str:
    """
    A/B/C 등급 자동 분류

    A: 대기업 (매출 $500M+, 직원 1,000+, 등급 4이상)
    B: 중견기업 (매출 $50M+, 직원 100+, 등급 3이상)
    C: 중소기업 (매출 $50M 미만, 직원 100 미만)
    """
    # 매출 파싱 ($2.5B → 2500000000)
    sales_num = parse_sales(sales)

    # 등급 숫자 추출 (5A1 → 5)
    rating_num = int(rating[0]) if rating else 0

    if sales_num >= 500_000_000 and employees >= 1000 and rating_num >= 4:
        return "A"
    elif sales_num >= 50_000_000 and employees >= 100 and rating_num >= 3:
        return "B"
    else:
        return "C"


def parse_sales(sales_str: str) -> int:
    """매출 문자열을 숫자로 변환"""
    if not sales_str:
        return 0
    sales_str = sales_str.replace("$", "").replace(",", "")
    if "B" in sales_str:
        return int(float(sales_str.replace("B", "")) * 1_000_000_000)
    elif "M" in sales_str:
        return int(float(sales_str.replace("M", "")) * 1_000_000)
    elif "K" in sales_str:
        return int(float(sales_str.replace("K", "")) * 1_000)
    return int(sales_str)


# 메인 실행
def main():
    # 우리 데이터 로드
    df = pd.read_csv("buyer_candidate_CLEANED_20250430.csv", encoding='utf-8-sig')

    # 100개 샘플 추출 (국가 다양하게)
    sample = df.groupby('country_iso3').head(5).head(100).copy()

    results = []
    for idx, row in sample.iterrows():
        name = row['normalized_name'] or row['title']
        country = row['country_iso3']

        print(f"[{idx}] 검색: {name} ({country})")

        # 1단계: 기업 검색
        search_result = search_company_by_name(name, country)

        if search_result["found"]:
            duns = search_result["duns"]
            print(f"  → 찾음! DUNS: {duns}, 신뢰도: {search_result['match_score']}%")

            # 2단계: 상세 정보
            detail = get_company_detail(duns)
            grade = grade_buyer(
                detail.get("annual_sales", ""),
                detail.get("employees", 0),
                detail.get("credit_rating", "")
            )

            results.append({
                "original_name": name,
                "duns": duns,
                "matched_name": search_result["company_name"],
                "match_score": search_result["match_score"],
                "grade": grade,
                **detail,
                "status": "VERIFIED"
            })
            print(f"  → 등급: {grade}, 매출: {detail.get('annual_sales')}, 직원: {detail.get('employees')}")
        else:
            results.append({
                "original_name": name,
                "status": "NOT_FOUND"
            })
            print(f"  → 찾을 수 없음")

    # 결과 저장
    df_result = pd.DataFrame(results)
    df_result.to_csv("nice_dnb_sample_results.csv", index=False, encoding='utf-8-sig')

    # 요약
    verified = len(df_result[df_result["status"] == "VERIFIED"])
    not_found = len(df_result[df_result["status"] == "NOT_FOUND"])

    print(f"
=== 결과 요약 ===")
    print(f"검증 완료: {verified}건")
    print(f"미발견: {not_found}건")
    print(f"A등급: {len(df_result[df_result['grade'] == 'A'])}건")
    print(f"B등급: {len(df_result[df_result['grade'] == 'B'])}건")
    print(f"C등급: {len(df_result[df_result['grade'] == 'C'])}건")

if __name__ == "__main__":
    main()
