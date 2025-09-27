"""
한국투자증권 API 클래스 (수정 완료 버전)
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
import time
from datetime import datetime, timedelta

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

        # Rate limiting을 위한 속성들
        self.request_count = 0
        self.last_request_time = time.time()
        self.max_requests_per_second = 15  # 안전하게 15로 설정

        if not self.app_key or not self.app_secret:
            raise ValueError("KIS_APP_KEY 또는 KIS_APP_SECRET이 설정되지 않았습니다.")

        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'KISAPI/1.0'
        })

        logger.info(f"한국투자증권 API 초기화: {self.base_url}")

    def _rate_limit(self):
        """API 요청 제한을 위한 메서드"""
        current_time = time.time()

        # 1초가 지났으면 카운터 리셋
        if current_time - self.last_request_time >= 1.0:
            self.request_count = 0
            self.last_request_time = current_time

        # 요청 제한에 도달했으면 대기
        if self.request_count >= self.max_requests_per_second:
            sleep_time = 1.0 - (current_time - self.last_request_time)
            if sleep_time > 0:
                logger.info(f"Rate limit 대기: {sleep_time:.2f}초")
                time.sleep(sleep_time)
                self.request_count = 0
                self.last_request_time = time.time()

        self.request_count += 1

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
            # Rate limiting 적용
            self._rate_limit()

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

            # 429 Too Many Requests 오류인 경우 재시도
            if hasattr(e, 'response') and e.response.status_code == 429:
                logger.warning("요청 제한 초과, 2초 대기 후 재시도")
                time.sleep(2)
                return self._make_request(endpoint, tr_id, params, method)

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
                "prev_close_price": int(data.get("stck_sdpr", 0)),  # 수정: 전일종가
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

        국내주식기간별시세(일/주/월/년)[v1_국내주식-016] API 사용

        Args:
            symbol: 종목코드
            period: 조회 기간 (D=일봉, W=주봉, M=월봉, Y=연봉)
            count: 조회할 데이터 개수
            start_date: 시작일자 (YYYYMMDD)
            end_date: 종료일자 (YYYYMMDD)

        Returns:
            차트 데이터
        """
        # 국내주식기간별시세(일/주/월/년) API
        endpoint = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        tr_id = "FHKST03010100"

        # 기본 날짜 설정
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            # 기간에 따라 시작일 조정
            days_back = {
                "D": count + 10,        # 일봉: count + 여유분
                "W": count * 7 + 10,    # 주봉: count * 7 + 여유분
                "M": count * 30 + 10,   # 월봉: count * 30 + 여유분
                "Y": count * 365 + 10   # 연봉: count * 365 + 여유분
            }
            start_dt = datetime.now() - timedelta(days=days_back.get(period, 50))
            start_date = start_dt.strftime("%Y%m%d")

        # 공식 문서에 따른 파라미터 (대문자)
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",     # 조건 시장 분류 코드 (J:KRX)
            "FID_INPUT_ISCD": symbol,          # 입력 종목코드
            "FID_INPUT_DATE_1": start_date,    # 입력 날짜 1 (조회 시작일자)
            "FID_INPUT_DATE_2": end_date,      # 입력 날짜 2 (조회 종료일자, 최대 100개)
            "FID_PERIOD_DIV_CODE": period,     # 기간분류코드 (D:일봉 W:주봉, M:월봉, Y:년봉)
            "FID_ORG_ADJ_PRC": "0"            # 수정주가 원주가 가격 여부 (0:수정주가 1:원주가)
        }

        logger.info(f"차트 데이터 조회: {symbol} {period}봉 ({start_date}~{end_date})")

        try:
            response = self._make_request(endpoint, tr_id, params)

            if response.get("rt_cd") != "0":
                error_msg = response.get('msg1', '알 수 없는 오류')
                logger.error(f"API 응답 오류: rt_cd={response.get('rt_cd')}, msg={error_msg}")
                return {
                    "symbol": symbol,
                    "stock_name": "",
                    "period": period,
                    "count": 0,
                    "chart_data": [],
                    "error": f"API 오류: {error_msg}"
                }

            # 공식 문서에 따른 응답 구조 파싱
            output1 = response.get("output1", {})
            output2 = response.get("output2", [])

            if not output2:
                logger.warning(f"{symbol}의 차트 데이터가 없습니다.")
                return {
                    "symbol": symbol,
                    "stock_name": output1.get("hts_kor_isnm", ""),
                    "period": period,
                    "count": 0,
                    "chart_data": []
                }

            chart_data = []
            for item in output2[:count]:
                try:
                    # 공식 문서의 output2 필드명 사용
                    data_point = {
                        "date": item.get("stck_bsop_date", ""),      # 주식 영업 일자
                        "open": int(float(item.get("stck_oprc", 0)) if item.get("stck_oprc") else 0),    # 주식 시가
                        "high": int(float(item.get("stck_hgpr", 0)) if item.get("stck_hgpr") else 0),    # 주식 최고가
                        "low": int(float(item.get("stck_lwpr", 0)) if item.get("stck_lwpr") else 0),     # 주식 최저가
                        "close": int(float(item.get("stck_clpr", 0)) if item.get("stck_clpr") else 0),   # 주식 종가
                        "volume": int(float(item.get("acml_vol", 0)) if item.get("acml_vol") else 0),    # 누적 거래량
                        "amount": int(float(item.get("acml_tr_pbmn", 0)) if item.get("acml_tr_pbmn") else 0)  # 누적 거래 대금
                    }

                    # 유효한 데이터만 추가 (날짜가 있고 종가가 0이 아닌 경우)
                    if data_point["date"] and data_point["close"] > 0:
                        chart_data.append(data_point)

                except (ValueError, TypeError) as e:
                    logger.debug(f"데이터 변환 오류: {e}, 데이터: {item}")
                    continue

            result = {
                "symbol": symbol,
                "stock_name": output1.get("hts_kor_isnm", ""),
                "period": period,
                "count": len(chart_data),
                "chart_data": chart_data
            }

            logger.success(f"{symbol} 차트 데이터 {len(chart_data)}개 조회 완료")
            return result

        except Exception as e:
            logger.error(f"차트 데이터 조회 실패: {e}")
            return {
                "symbol": symbol,
                "stock_name": "",
                "period": period,
                "count": 0,
                "chart_data": [],
                "error": str(e)
            }

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

        # 4. 삼성전자 차트 데이터 (수정된 버전)
        print("\n=== 삼성전자 차트 데이터 ===")

        # 먼저 더 넓은 기간으로 시도
        chart = api.stock_chart("005930", count=10,
                                start_date="20240901",
                                end_date="20240920")  # 과거 날짜로 시도

        print(f"차트 데이터 {chart['count']}개 조회 완료")

        if chart['chart_data']:
            print("최근 데이터:")
            for data in chart['chart_data'][:5]:
                print(f"  {data['date']}: 종가 {data['close']:,}원, 거래량 {data['volume']:,}주")
        elif 'error' in chart:
            print(f"차트 오류: {chart['error']}")
            print("다른 방식으로 재시도...")

            # 5. 다른 종목으로 시도 (LG전자)
            print("\n=== LG전자 차트 데이터 재시도 ===")
            chart2 = api.stock_chart("066570", period="D", count=5)

            if chart2['count'] > 0:
                print(f"LG전자 차트 성공: {chart2['count']}개 데이터")
                for data in chart2['chart_data'][:3]:
                    print(f"  {data['date']}: 종가 {data['close']:,}원")
            else:
                print("LG전자 차트도 실패")
                print("차트 API는 현재 사용할 수 없는 상태로 보입니다.")
                print("가능한 원인:")
                print("- 해당 API는 별도 신청이나 권한이 필요할 수 있음")
                print("- 장 시간 중에만 작동할 수 있음")
                print("- 모의투자 계정에서는 제한될 수 있음")

        return True

    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_kis_api()