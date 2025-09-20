"""
한국투자증권 API 클래스
- StockPrice_kis: 국내 주식 현재가 조회
- StockSearch_kis: 종목 검색
- USStockPrice_kis: 미국 주식 현재가 조회
- StockChart_kis: 주식 차트 데이터 조회
"""

import requests
from typing import Dict, List, Any, Optional
from loguru import logger
import sys
import os
import json

# 설정 파일 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

class KISAPI:
    """한국투자증권 Open API 클래스"""

    def __init__(self):
        self.base_url = settings.KIS_API_URL
        self.app_key = settings.KIS_APP_KEY
        self.app_secret = settings.KIS_APP_SECRET
        self.access_token = None

        if not self.app_key or not self.app_secret:
            raise ValueError("KIS_APP_KEY 또는 KIS_APP_SECRET이 설정되지 않았습니다.")

        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'KISAPI/1.0'
        })

        logger.info(f"한국투자증권 API 초기화: {self.base_url}")

    def _get_access_token(self) -> str:
        """OAuth 액세스 토큰 발급"""
        if self.access_token:
            return self.access_token

        endpoint = "/oauth2/tokenP"
        url = f"{self.base_url}{endpoint}"

        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        logger.info("액세스 토큰 발급 중...")

        try:
            response = requests.post(url, json=data, timeout=settings.REQUEST_TIMEOUT)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data.get("access_token")

            if not self.access_token:
                raise ValueError("액세스 토큰 발급 실패")

            logger.success("액세스 토큰 발급 완료")
            return self.access_token

        except Exception as e:
            logger.error(f"토큰 발급 실패: {e}")
            raise

    def _make_request(self, endpoint: str, tr_id: str, params: Dict = None,
                      method: str = "GET") -> Dict[str, Any]:
        """API 요청 공통 메서드"""
        try:
            token = self._get_access_token()
            url = f"{self.base_url}{endpoint}"

            headers = {
                "Authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": tr_id,
                "custtype": "P"  # 개인
            }

            logger.debug(f"요청 URL: {url}, TR_ID: {tr_id}")

            if method.upper() == "GET":
                response = self.session.get(url, params=params, headers=headers,
                                            timeout=settings.REQUEST_TIMEOUT)
            else:
                response = self.session.post(url, json=params, headers=headers,
                                             timeout=settings.REQUEST_TIMEOUT)

            response.raise_for_status()

            logger.info(f"API 요청 성공: {tr_id}")
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"한투 API 요청 실패: {e}")
            raise

    def stock_price(self, symbol: str, market: str = "KOSPI") -> Dict[str, Any]:
        """
        StockPrice_kis: 국내 주식 현재가 조회

        Args:
            symbol: 종목코드 (6자리)
            market: 시장구분 (표시용)

        Returns:
            주식 현재가 정보
        """
        endpoint = "/uapi/domestic-stock/v1/quotations/inquire-price"
        tr_id = "FHKST01010100"  # 실전 투자

        params = {
            "fid_cond_mrkt_div_code": "J",  # 주식 시장
            "fid_input_iscd": symbol
        }

        logger.info(f"주식 현재가 조회: {symbol}")

        try:
            response = self._make_request(endpoint, tr_id, params)

            if response.get("rt_cd") != "0":
                raise ValueError(f"API 오류: {response.get('msg1', '알 수 없는 오류')}")

            data = response.get("output", {})

            result = {
                "symbol": symbol,
                "stock_name": data.get("hts_kor_isnm", ""),
                "current_price": int(data.get("stck_prpr", 0)),
                "change_price": int(data.get("prdy_vrss", 0)),
                "change_rate": float(data.get("prdy_ctrt", 0)),
                "change_sign": int(data.get("prdy_vrss_sign", 0)),
                "volume": int(data.get("acml_vol", 0)),
                "transaction_amount": int(data.get("acml_tr_pbmn", 0)),
                "high_price": int(data.get("stck_hgpr", 0)),
                "low_price": int(data.get("stck_lwpr", 0)),
                "open_price": int(data.get("stck_oprc", 0)),
                "prev_close_price": int(data.get("stck_prpr", 0)),
                "market": market
            }

            logger.success(f"{result['stock_name']} 현재가: {result['current_price']:,}원")
            return result

        except Exception as e:
            logger.error(f"주식 현재가 조회 실패: {e}")
            raise

    def stock_search(self, keyword: str, market: str = "ALL") -> Dict[str, Any]:
        """
        StockSearch_kis: 종목 검색

        Args:
            keyword: 검색 키워드
            market: 시장구분 (ALL, KOSPI, KOSDAQ)

        Returns:
            검색 결과
        """
        # 한투 API에는 직접적인 검색 API가 없으므로
        # 종목 마스터 정보를 기반으로 검색 로직 구현 필요
        # 여기서는 기본 구조만 제공

        logger.info(f"종목 검색: {keyword}")

        # 임시로 더미 데이터 반환 (실제로는 종목 마스터 DB 연동 필요)
        result = {
            "results": [],
            "total_count": 0,
            "keyword": keyword,
            "market_filter": market
        }

        logger.warning("종목 검색 기능은 별도 종목 마스터 DB 연동이 필요합니다.")
        return result

    def us_stock_price(self, symbol: str, exchange: str = "NASDAQ") -> Dict[str, Any]:
        """
        USStockPrice_kis: 미국 주식 현재가 조회

        Args:
            symbol: 미국 주식 심볼
            exchange: 거래소 (NASDAQ, NYSE, AMEX)

        Returns:
            미국 주식 현재가 정보
        """
        endpoint = "/uapi/overseas-price/v1/quotations/price"
        tr_id = "HHDFS00000300"  # 해외주식 현재가

        # 거래소 코드 매핑
        exchange_codes = {
            "NASDAQ": "NAS",
            "NYSE": "NYS",
            "AMEX": "AMS"
        }

        excd = exchange_codes.get(exchange, "NAS")

        params = {
            "AUTH": "",
            "EXCD": excd,
            "SYMB": symbol
        }

        logger.info(f"미국 주식 현재가 조회: {symbol} ({exchange})")

        try:
            response = self._make_request(endpoint, tr_id, params)

            if response.get("rt_cd") != "0":
                raise ValueError(f"API 오류: {response.get('msg1', '알 수 없는 오류')}")

            data = response.get("output", {})

            result = {
                "symbol": symbol,
                "company_name": data.get("name", ""),
                "current_price": float(data.get("last", 0)),
                "change_price": float(data.get("diff", 0)),
                "change_rate": float(data.get("rate", 0)),
                "change_sign": data.get("sign", ""),
                "volume": int(data.get("tvol", 0)),
                "high_price": float(data.get("high", 0)),
                "low_price": float(data.get("low", 0)),
                "open_price": float(data.get("open", 0)),
                "prev_close_price": float(data.get("base", 0)),
                "exchange": exchange,
                "exchange_code": excd,
                "currency": "USD"
            }

            logger.success(f"{symbol} 현재가: ${result['current_price']:.2f}")
            return result

        except Exception as e:
            logger.error(f"미국 주식 현재가 조회 실패: {e}")
            raise

    def stock_chart(self, symbol: str, period: str = "D", count: int = 30,
                    start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        StockChart_kis: 주식 차트 데이터 조회

        Args:
            symbol: 종목코드
            period: 조회 기간 (D=일봉, W=주봉, M=월봉)
            count: 조회할 데이터 개수
            start_date: 시작일자 (YYYYMMDD)
            end_date: 종료일자 (YYYYMMDD)

        Returns:
            차트 데이터
        """
        endpoint = "/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        tr_id = "FHKST01010400"  # 주식현재가 일자별

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol,
            "FID_PERIOD_DIV_CODE": period,
            "FID_ORG_ADJ_PRC": "0"  # 수정주가 미적용
        }

        if start_date:
            params["FID_INPUT_DATE_1"] = start_date
        if end_date:
            params["FID_INPUT_DATE_2"] = end_date

        logger.info(f"차트 데이터 조회: {symbol} {period}봉")

        try:
            response = self._make_request(endpoint, tr_id, params)

            if response.get("rt_cd") != "0":
                raise ValueError(f"API 오류: {response.get('msg1', '알 수 없는 오류')}")

            chart_data = []
            for item in response.get("output2", [])[:count]:
                data_point = {
                    "date": item.get("stck_bsop_date", ""),
                    "open": int(item.get("stck_oprc", 0)),
                    "high": int(item.get("stck_hgpr", 0)),
                    "low": int(item.get("stck_lwpr", 0)),
                    "close": int(item.get("stck_clpr", 0)),
                    "volume": int(item.get("acml_vol", 0))
                }
                chart_data.append(data_point)

            result = {
                "symbol": symbol,
                "stock_name": response.get("output1", {}).get("hts_kor_isnm", ""),
                "period": period,
                "count": len(chart_data),
                "chart_data": chart_data
            }

            logger.success(f"{symbol} 차트 데이터 {len(chart_data)}개 조회 완료")
            return result

        except Exception as e:
            logger.error(f"차트 데이터 조회 실패: {e}")
            raise

# 테스트용 함수
def test_kis_api():
    """한국투자증권 API 테스트"""
    try:
        api = KISAPI()

        # 1. 토큰 발급 테스트
        print("=== 토큰 발급 테스트 ===")
        token = api._get_access_token()
        print(f"토큰 발급 성공: {token[:20]}...")

        # 2. 삼성전자 현재가 조회
        print("\n=== 삼성전자 현재가 조회 ===")
        price = api.stock_price("005930")
        print(f"{price['stock_name']} 현재가: {price['current_price']:,}원")

        # 3. 애플 주가 조회 (미국 주식)
        print("\n=== 애플 주가 조회 ===")
        us_price = api.us_stock_price("AAPL")
        print(f"AAPL 현재가: ${us_price['current_price']:.2f}")

        # 4. 삼성전자 차트 데이터
        print("\n=== 삼성전자 차트 데이터 ===")
        chart = api.stock_chart("005930", count=5)
        print(f"차트 데이터 {chart['count']}개 조회 완료")

        return True

    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_kis_api()