"""
프로젝트 설정 파일
환경변수 로드 및 API 설정 관리
"""

import os
from dotenv import load_dotenv
from typing import Optional

# .env 파일 로드
load_dotenv()

class Settings:
    """API 설정 클래스"""

    # 기본 설정
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))

    # API Base URLs
    UPBIT_API_URL: str = os.getenv('UPBIT_API_URL', 'https://api.upbit.com')
    KIS_API_URL: str = os.getenv('KIS_API_URL', 'https://openapi.koreainvestment.com:9443')
    KAKAO_API_URL: str = os.getenv('KAKAO_API_URL', 'https://dapi.kakao.com')
    TMAP_API_URL: str = os.getenv('TMAP_API_URL', 'https://apis.openapi.sk.com')

    # 업비트 API (공개 API, 인증 불필요)
    UPBIT_ACCESS_KEY: Optional[str] = os.getenv('UPBIT_ACCESS_KEY')
    UPBIT_SECRET_KEY: Optional[str] = os.getenv('UPBIT_SECRET_KEY')

    # 한국투자증권 API
    KIS_APP_KEY: Optional[str] = os.getenv('KIS_APP_KEY')
    KIS_APP_SECRET: Optional[str] = os.getenv('KIS_APP_SECRET')
    KIS_ACCOUNT_NUMBER: Optional[str] = os.getenv('KIS_ACCOUNT_NUMBER')

    # 카카오 로컬 API
    KAKAO_REST_API_KEY: Optional[str] = os.getenv('KAKAO_REST_API_KEY')

    # T맵 API
    TMAP_APP_KEY: Optional[str] = os.getenv('TMAP_APP_KEY')

    @classmethod
    def validate_api_keys(cls) -> dict:
        """API 키 검증 및 상태 반환"""
        status = {
            'upbit': True,  # 공개 API라 항상 사용 가능
            'kis': bool(cls.KIS_APP_KEY and cls.KIS_APP_SECRET),
            'kakao': bool(cls.KAKAO_REST_API_KEY),
            'tmap': bool(cls.TMAP_APP_KEY)
        }
        return status

    @classmethod
    def get_missing_keys(cls) -> list:
        """누락된 API 키 목록 반환"""
        missing = []
        status = cls.validate_api_keys()

        for api, available in status.items():
            if not available:
                missing.append(api)

        return missing

# 설정 인스턴스 생성
settings = Settings()

# 개발용 함수들
def print_api_status():
    """API 키 상태 출력"""
    status = settings.validate_api_keys()
    print("=== API 키 상태 ===")
    for api, available in status.items():
        status_text = "✅ 사용 가능" if available else "❌ 키 누락"
        print(f"{api.upper()}: {status_text}")

    missing = settings.get_missing_keys()
    if missing:
        print(f"\n누락된 키: {', '.join(missing)}")
        print("'.env' 파일에 키를 추가해주세요.")

if __name__ == "__main__":
    print_api_status()