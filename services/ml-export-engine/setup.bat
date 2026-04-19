@echo off
echo ====================================
echo VALUE-UP AI 백엔드 설치 스크립트
echo ====================================
echo.

echo [1/3] Python 버전 확인...
python --version
if %errorlevel% neq 0 (
    echo Python이 설치되어 있지 않습니다.
    echo Python 3.9 이상을 설치해주세요.
    pause
    exit /b 1
)
echo.

echo [2/3] 의존성 설치 중...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 의존성 설치 실패
    pause
    exit /b 1
)
echo.

echo [3/3] 전체 파이프라인 테스트...
python run_full_pipeline.py
if %errorlevel% neq 0 (
    echo 파이프라인 테스트 실패
    pause
    exit /b 1
)
echo.

echo ====================================
echo 설치 완료!
echo ====================================
echo.
echo 다음 명령어로 API 서버를 실행하세요:
echo   python api.py
echo.
pause
