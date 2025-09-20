"""
업비트 API 클래스
- CryptoPrice_upbit: 현재가 조회
- MarketList_upbit: 마켓 목록 조회
- CryptoCandle_upbit: 캔들 데이터 조회
"""

import requests
from typing import Dict, List, Any, Optional
from loguru import logger
import sys
import os

# 설정 파일 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

class UpbitAPI:
    """업비트 Open API 클래스"""

    def __init__(self):
        self.base_url = settings.UPBIT_API_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'UpbitAPI/1.0'
        })
        logger.info(f"업비트 API 초기화: {self.base_url}")

    def _make_request(self, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """API 요청 공통 메서드"""
        try:
            url = f"{self.base_url}{endpoint}"
            logger.debug(f"요청 URL: {url}, 파라미터: {params}")

            response = self.session.get(
                url,
                params=params,
                timeout=settings.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            logger.info(f"API 요청 성공: {endpoint}")
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"업비트 API 요청 실패: {e}")
            raise

    def crypto_price(self, symbol: str, quote: str = "KRW") -> Dict[str, Any]:
        """
        CryptoPrice_upbit: 암호화폐 현재가 조회

        Args:
            symbol: 암호화폐 심볼 (BTC, ETH 등)
            quote: 기준 통화 (KRW, BTC, USDT)

        Returns:
            현재가 정보 딕셔너리
        """
        market = f"{quote}-{symbol}"
        endpoint = "/v1/ticker"
        params = {"markets": market}

        logger.info(f"현재가 조회: {market}")

        try:
            response = self._make_request(endpoint, params)

            if not response:
                raise ValueError(f"마켓 {market}에 대한 데이터가 없습니다")

            data = response[0]  # 첫 번째 마켓 데이터

            # 표준화된 형태로 변환
            result = {
                "symbol": symbol,
                "trade_price": data.get("trade_price"),
                "change_price": data.get("change_price"),
                "change_rate": data.get("change_rate"),
                "change": data.get("change"),
                "high_price": data.get("high_price"),
                "low_price": data.get("low_price"),
                "opening_price": data.get("opening_price"),
                "prev_closing_price": data.get("prev_closing_price"),
                "trade_volume": data.get("trade_volume"),
                "acc_trade_price_24h": data.get("acc_trade_price_24h"),
                "acc_trade_volume_24h": data.get("acc_trade_volume_24h"),
                "highest_52_week_price": data.get("highest_52_week_price"),
                "highest_52_week_date": data.get("highest_52_week_date"),
                "lowest_52_week_price": data.get("lowest_52_week_price"),
                "lowest_52_week_date": data.get("lowest_52_week_date"),
                "market": market,
                "timestamp": data.get("timestamp")
            }

            logger.success(f"{symbol} 현재가: {result['trade_price']:,}원")
            return result

        except Exception as e:
            logger.error(f"현재가 조회 실패: {e}")
            raise

    def market_list(self, quote: str = "KRW", include_event: bool = True) -> Dict[str, Any]:
        """
        MarketList_upbit: 마켓 목록 조회

        Args:
            quote: 기준 통화 필터 (KRW, BTC, USDT, ALL)
            include_event: 시장 경고/주의 정보 포함 여부

        Returns:
            마켓 목록 정보
        """
        endpoint = "/v1/market/all"
        params = {}

        if not include_event:
            params["isDetails"] = "false"

        logger.info(f"마켓 목록 조회: {quote}")

        try:
            response = self._make_request(endpoint, params)

            # quote에 따른 필터링
            if quote != "ALL":
                filtered_markets = [
                    market for market in response
                    if market["market"].startswith(quote)
                ]
            else:
                filtered_markets = response

            result = {
                "markets": [market["market"] for market in filtered_markets],
                "market_count": len(filtered_markets),
                "quote": quote,
                "details": filtered_markets
            }

            logger.success(f"{quote} 마켓 {len(filtered_markets)}개 조회 완료")
            return result

        except Exception as e:
            logger.error(f"마켓 목록 조회 실패: {e}")
            raise

    def crypto_candle(self, symbol: str, quote: str = "KRW",
                      candle_type: str = "days", unit: Optional[int] = None,
                      count: int = 30, to: Optional[str] = None) -> Dict[str, Any]:
        """
        CryptoCandle_upbit: 캔들 데이터 조회

        Args:
            symbol: 암호화폐 심볼
            quote: 기준 통화
            candle_type: 캔들 타입 (minutes, days, weeks, months)
            unit: 분봉일 때 분 단위 (1, 3, 5, 10, 15, 30, 60, 240)
            count: 조회할 캔들 개수 (최대 200)
            to: 마지막 캔들 시점 (ISO8601)

        Returns:
            캔들 데이터
        """
        market = f"{quote}-{symbol}"

        # 엔드포인트 설정
        if candle_type == "minutes":
            if unit is None:
                unit = 1
            endpoint = f"/v1/candles/minutes/{unit}"
        else:
            endpoint = f"/v1/candles/{candle_type}"

        params = {
            "market": market,
            "count": min(count, 200)  # 최대 200개 제한
        }

        if to:
            params["to"] = to

        logger.info(f"캔들 데이터 조회: {market} {candle_type}")

        try:
            response = self._make_request(endpoint, params)

            # 데이터 변환
            candles = []
            for candle in response:
                candle_data = {
                    "candle_date_time_kst": candle.get("candle_date_time_kst"),
                    "opening_price": candle.get("opening_price"),
                    "high_price": candle.get("high_price"),
                    "low_price": candle.get("low_price"),
                    "trade_price": candle.get("trade_price"),
                    "candle_acc_trade_volume": candle.get("candle_acc_trade_volume"),
                    "candle_acc_trade_price": candle.get("candle_acc_trade_price"),
                    "timestamp": candle.get("timestamp")
                }
                candles.append(candle_data)

            result = {
                "symbol": symbol,
                "candle_type": candle_type,
                "unit": unit if candle_type == "minutes" else None,
                "count": len(candles),
                "candles": candles,
                "market": market
            }

            logger.success(f"{symbol} {candle_type} 캔들 {len(candles)}개 조회 완료")
            return result

        except Exception as e:
            logger.error(f"캔들 데이터 조회 실패: {e}")
            raise

# 테스트용 함수
def test_upbit_api():
    """업비트 API 테스트"""
    api = UpbitAPI()

    try:
        # 1. 마켓 목록 조회
        print("=== 마켓 목록 조회 ===")
        markets = api.market_list("KRW")
        print(f"KRW 마켓 수: {markets['market_count']}")
        print(f"첫 5개 마켓: {markets['markets'][:5]}")

        # 2. BTC 현재가 조회
        print("\n=== BTC 현재가 조회 ===")
        price = api.crypto_price("BTC")
        print(f"BTC 현재가: {price['trade_price']:,}원")
        print(f"전일대비: {price['change_price']:,}원 ({price['change_rate']:.2%})")

        # 3. BTC 일봉 조회
        print("\n=== BTC 일봉 데이터 ===")
        candles = api.crypto_candle("BTC", count=5)
        print(f"조회된 캔들 수: {candles['count']}")

        return True

    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_upbit_api()