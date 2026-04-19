# 프론트엔드-백엔드 연동 가이드

## 📝 수정 내용 요약

React 프론트엔드를 FastAPI 백엔드와 연동하여 실시간 AI 분석 결과를 표시하도록 수정했습니다.

## 🔄 주요 변경사항

### 1. MOCK 데이터 제거

**수정 전:**
```javascript
const MOCK_COUNTRIES = [
  { name: "베트남", gdp: 430, growth: 6.0, culture: 90, regulation: 40 },
  { name: "미국", gdp: 27000, growth: 2.1, culture: 55, regulation: 70 },
  { name: "일본", gdp: 4200, growth: 1.1, culture: 65, regulation: 60 },
];
```

**수정 후:**
```javascript
// 국가 코드 -> 한글 이름 매핑
const COUNTRY_NAMES = {
  VNM: "베트남",
  USA: "미국",
  CHN: "중국",
  JPN: "일본",
  SGP: "싱가포르",
  // ... 등
};
```

**변경 이유:**
- 하드코딩된 더미 데이터 대신 백엔드에서 실시간 데이터를 받아옴
- ISO-3 국가 코드를 한글 이름으로 변환하기 위한 매핑만 유지

---

### 2. analyze() 함수 - API 호출로 변경

**수정 전:**
```javascript
const analyze = () => {
  setLoading(true);
  setTimeout(() => {
    const scored = MOCK_COUNTRIES.map((c) => ({
      ...c,
      score: c.growth * 2 + c.culture - c.regulation * 0.5,
    })).sort((a, b) => b.score - a.score);

    setResult(scored[0]);
    setLoading(false);
  }, 1000);
};
```

**수정 후:**
```javascript
const analyze = async () => {
  setLoading(true);
  setError(null);

  try {
    // 백엔드 API 호출
    const response = await fetch("http://localhost:8000/predict", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        hs_code: "33",
        exporter_country: "KOR",
        top_n: 3,
      }),
    });

    if (!response.ok) {
      throw new Error(`API 오류: ${response.status}`);
    }

    const data = await response.json();

    // 첫 번째 추천 국가 사용
    const topCountry = data.top_countries[0];

    // 결과 변환
    setResult({
      country: topCountry.country,
      name: COUNTRY_NAMES[topCountry.country] || topCountry.country,
      score: topCountry.score,
      expected_export_usd: topCountry.expected_export_usd,
      explanation: topCountry.explanation,
    });
  } catch (err) {
    console.error("API 호출 오류:", err);
    setError(err.message);
  } finally {
    setLoading(false);
  }
};
```

**주요 변경점:**
1. **동기 → 비동기**: `setTimeout` 제거, `async/await` 사용
2. **API 호출**: `fetch()` 사용하여 백엔드 `/predict` 엔드포인트 호출
3. **에러 처리**: `try/catch` 블록으로 네트워크 오류 처리
4. **데이터 구조 변환**: 백엔드 응답을 프론트엔드 형식으로 매핑

---

### 3. 레이더 차트 데이터 변환

**수정 전:**
```javascript
const radarData = result
  ? [
      { axis: "시장성장률", value: result.growth * 10 },
      { axis: "문화적합성", value: result.culture },
      { axis: "규제장벽(낮을수록 유리)", value: 100 - result.regulation },
    ]
  : [];
```

**수정 후:**
```javascript
const radarData = result
  ? [
      {
        axis: "중력모형 기준선",
        value: Math.abs(result.explanation.gravity_baseline) * 20,
      },
      {
        axis: "성장 잠재력",
        value: Math.abs(result.explanation.growth_potential) * 20,
      },
      {
        axis: "문화 적합성",
        value: Math.abs(result.explanation.culture_fit) * 20,
      },
      {
        axis: "규제 편의성",
        value: Math.abs(result.explanation.regulation_ease) * 20,
      },
      {
        axis: "물류 성과",
        value: Math.abs(result.explanation.logistics) * 20,
      },
      {
        axis: "관세 영향",
        value: Math.abs(result.explanation.tariff_impact) * 20,
      },
    ]
  : [];
```

**변경 내용:**
- 백엔드에서 제공하는 SHAP 기반 `explanation` 필드 사용
- 6개의 설명 요인을 레이더 차트에 표시
- `Math.abs()`: SHAP 값은 음수/양수 모두 가능, 크기를 시각화
- `* 20`: 값을 스케일링하여 차트에서 잘 보이도록 조정

---

### 4. 에러 상태 추가

**수정 전:**
```javascript
const [loading, setLoading] = useState(false);
const [result, setResult] = useState(null);
```

**수정 후:**
```javascript
const [loading, setLoading] = useState(false);
const [result, setResult] = useState(null);
const [error, setError] = useState(null);
```

**에러 UI:**
```javascript
{error && (
  <div style={{ /* 빨간 배경 스타일 */ }}>
    <strong>오류 발생:</strong> {error}
    <br />
    <small>백엔드 API 서버가 실행 중인지 확인하세요.</small>
  </div>
)}
```

---

### 5. UI 개선

**추가된 정보:**
- 종합 점수 (0-100)
- 예상 수출액 ($)
- 6개 요인별 SHAP 기여도
- 주요 요인 분석 (텍스트 설명)

**수정 전 UI:**
```
추천 국가: 베트남
[레이더 차트]
성장률(6.0%)과 문화적합성이 높아 종합 점수가 가장 높게 산출되었습니다.
```

**수정 후 UI:**
```
추천 국가: 베트남 (VNM)
종합 점수: 87.2 / 100
예상 수출액: $17,176,000

AI 분석 근거 (SHAP 기반)
[6축 레이더 차트]

주요 요인 분석
• 중력모형 기준선: +1.384 (경제 규모 및 거리 기반)
• 성장 잠재력: -0.127 (GDP 성장률 반영)
• 문화 적합성: +0.067 (문화적 유사성)
• 관세 영향: -0.011 (관세율 영향)
```

---

## 📊 API 통신 흐름

```
┌─────────────┐      POST /predict       ┌──────────────┐
│             │ ────────────────────────> │              │
│  React      │  {                        │  FastAPI     │
│  Frontend   │    hs_code: "33",         │  Backend     │
│             │    exporter_country: "KOR"│              │
│             │  }                        │              │
│             │ <──────────────────────── │              │
└─────────────┘      JSON Response        └──────────────┘
                     {
                       top_countries: [
                         {
                           country: "VNM",
                           score: 0.87,
                           expected_export_usd: 17176000,
                           explanation: {
                             gravity_baseline: 1.384,
                             growth_potential: -0.127,
                             culture_fit: 0.067,
                             ...
                           }
                         }
                       ]
                     }
```

## 🔧 에러 처리 시나리오

### 1. 네트워크 오류
```javascript
catch (err) {
  console.error("API 호출 오류:", err);
  setError(err.message);
}
```

**표시 메시지:**
> 오류 발생: Failed to fetch
> 백엔드 API 서버가 실행 중인지 확인하세요.

### 2. HTTP 오류 (4xx, 5xx)
```javascript
if (!response.ok) {
  throw new Error(`API 오류: ${response.status}`);
}
```

**표시 메시지:**
> 오류 발생: API 오류: 500
> 백엔드 API 서버가 실행 중인지 확인하세요.

### 3. 응답 파싱 오류
```javascript
const data = await response.json();
// JSON 파싱 실패시 catch 블록으로 이동
```

---

## 🚀 실행 방법

### 1. 백엔드 실행
```bash
cd backend
python api.py
# 또는
python api_v2.py
```

백엔드가 `http://localhost:8000`에서 실행되어야 합니다.

### 2. 프론트엔드 실행
```bash
npm run dev
```

프론트엔드가 `http://localhost:5173`에서 실행됩니다.

### 3. 테스트
1. 브라우저에서 http://localhost:5173 접속
2. "분석하기" 버튼 클릭
3. 백엔드 API 호출 → 결과 표시

---

## 🐛 트러블슈팅

### CORS 오류
**증상:**
```
Access to fetch at 'http://localhost:8000/predict' from origin
'http://localhost:5173' has been blocked by CORS policy
```

**해결:**
백엔드 `api.py`에 CORS 미들웨어가 이미 설정되어 있습니다:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API 서버 미실행
**증상:**
```
오류 발생: Failed to fetch
```

**해결:**
```bash
cd backend
python api.py
```

### 빈 응답
**증상:**
레이더 차트에 데이터가 표시되지 않음

**확인:**
1. 백엔드 로그에서 모델 로딩 확인
2. `/health` 엔드포인트 테스트:
   ```bash
   curl http://localhost:8000/health
   ```

---

## 📈 향후 개선사항

### 1. 입력 폼 추가
현재는 HS 코드가 "33"으로 하드코딩되어 있습니다.

```javascript
// 추가 예정
const [hsCode, setHsCode] = useState("33");

<input
  value={hsCode}
  onChange={(e) => setHsCode(e.target.value)}
  placeholder="HS 코드 입력 (예: 33)"
/>
```

### 2. Top N 국가 목록
현재는 첫 번째 국가만 표시합니다.

```javascript
// 추가 예정
data.top_countries.map((country, index) => (
  <CountryCard key={index} country={country} rank={index + 1} />
))
```

### 3. 로딩 스피너
```javascript
// 추가 예정
{loading && (
  <div className="spinner">
    <Loader2 className="animate-spin" />
  </div>
)}
```

### 4. 캐싱
```javascript
// 추가 예정
const [cache, setCache] = useState({});

if (cache[cacheKey]) {
  setResult(cache[cacheKey]);
} else {
  // API 호출
}
```

---

## 📝 백엔드 API 스펙

### Endpoint: POST /predict

**요청:**
```json
{
  "hs_code": "33",
  "exporter_country": "KOR",
  "top_n": 3
}
```

**응답:**
```json
{
  "top_countries": [
    {
      "country": "VNM",
      "score": 0.872,
      "expected_export_usd": 17176000,
      "explanation": {
        "gravity_baseline": 1.384,
        "growth_potential": -0.127,
        "culture_fit": 0.067,
        "regulation_ease": 0.024,
        "logistics": 0.016,
        "tariff_impact": -0.011
      }
    }
  ],
  "data_source": "dummy"  // 또는 "real"
}
```

---

**작성일:** 2026-01-11
**버전:** 1.0
**다음 업데이트:** 입력 폼 및 다중 결과 표시 추가
