#!/bin/bash

echo "===================================="
echo "VALUE-UP AI 백엔드 설치 스크립트"
echo "===================================="
echo ""

echo "[1/3] Python 버전 확인..."
python3 --version
if [ $? -ne 0 ]; then
    echo "Python이 설치되어 있지 않습니다."
    echo "Python 3.9 이상을 설치해주세요."
    exit 1
fi
echo ""

echo "[2/3] 의존성 설치 중..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "의존성 설치 실패"
    exit 1
fi
echo ""

echo "[3/3] 전체 파이프라인 테스트..."
python3 run_full_pipeline.py
if [ $? -ne 0 ]; then
    echo "파이프라인 테스트 실패"
    exit 1
fi
echo ""

echo "===================================="
echo "설치 완료!"
echo "===================================="
echo ""
echo "다음 명령어로 API 서버를 실행하세요:"
echo "  python3 api.py"
echo ""
