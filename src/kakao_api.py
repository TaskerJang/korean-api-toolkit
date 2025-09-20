"""
카카오 로컬 API 클래스
- AddressToCoord_kakao: 주소-좌표 변환
- CoordToAddress_kakao: 좌표-주소 변환
- PlaceSearch_kakao: 키워드 장소 검색
- CategorySearch_kakao: 카테고리 장소 검색
"""

import requests
from typing import Dict, List, Any, Optional
from loguru import logger
import sys
import os

# 설정 파일 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

class KakaoAPI:
    """카카오 로컬 API 클래스"""

    def __init__(self):
        self.base_url = settings.KAKAO_API_URL
        self.api_key = settings.KAKAO_REST_API_KEY

        if not self.api_key:
            raise ValueError("KAKAO_REST_API_KEY가 설정되지 않았습니다.")

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'KakaoAK {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'KakaoAPI/1.0'
        })
        logger.info(f"카카오 로컬 API 초기화: {self.base_url}")

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
            logger.error(f"카카오 API 요청 실패: {e}")
            raise

    def address_to_coord(self, address: str) -> Dict[str, Any]:
        """
        AddressToCoord_kakao: 주소-좌표 변환

        Args:
            address: 변환할 주소

        Returns:
            좌표 변환 결과
        """
        endpoint = "/v2/local/search/address.json"
        params = {"query": address}

        logger.info(f"주소-좌표 변환: {address}")

        try:
            response = self._make_request(endpoint, params)

            if not response.get("documents"):
                raise ValueError(f"주소 '{address}'에 대한 검색 결과가 없습니다.")

            data = response["documents"][0]

            result = {
                "address": address,
                "road_address": data.get("road_address", {}).get("address_name", ""),
                "jibun_address": data.get("address", {}).get("address_name", ""),
                "latitude": float(data.get("y", 0)),
                "longitude": float(data.get("x", 0)),
                "address_type": data.get("address_type", "")
            }

            logger.success(f"주소 변환 완료: {result['latitude']}, {result['longitude']}")
            return result

        except Exception as e:
            logger.error(f"주소-좌표 변환 실패: {e}")
            raise

    def coord_to_address(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        CoordToAddress_kakao: 좌표-주소 변환

        Args:
            latitude: 위도
            longitude: 경도

        Returns:
            주소 변환 결과
        """
        endpoint = "/v2/local/geo/coord2address.json"
        params = {
            "x": longitude,
            "y": latitude
        }

        logger.info(f"좌표-주소 변환: {latitude}, {longitude}")

        try:
            response = self._make_request(endpoint, params)

            if not response.get("documents"):
                raise ValueError(f"좌표 ({latitude}, {longitude})에 대한 주소를 찾을 수 없습니다.")

            data = response["documents"][0]

            result = {
                "latitude": latitude,
                "longitude": longitude,
                "road_address": data.get("road_address", {}).get("address_name", ""),
                "jibun_address": data.get("address", {}).get("address_name", ""),
                "building_name": data.get("road_address", {}).get("building_name", ""),
                "region_1depth": data.get("address", {}).get("region_1depth_name", ""),
                "region_2depth": data.get("address", {}).get("region_2depth_name", ""),
                "region_3depth": data.get("address", {}).get("region_3depth_name", ""),
                "zone_no": data.get("road_address", {}).get("zone_no", "")
            }

            logger.success(f"주소 변환 완료: {result['road_address']}")
            return result

        except Exception as e:
            logger.error(f"좌표-주소 변환 실패: {e}")
            raise

    def place_search(self, keyword: str, x: Optional[float] = None, y: Optional[float] = None,
                     radius: Optional[int] = None, sort: str = "accuracy",
                     page: int = 1, size: int = 15) -> Dict[str, Any]:
        """
        PlaceSearch_kakao: 키워드 장소 검색

        Args:
            keyword: 검색 키워드
            x: 중심 좌표 경도 (선택)
            y: 중심 좌표 위도 (선택)
            radius: 검색 반경(미터, 최대 20000)
            sort: 정렬 방식 (accuracy, distance)
            page: 페이지 번호 (1~45)
            size: 한 페이지 결과 수 (1~15)

        Returns:
            장소 검색 결과
        """
        endpoint = "/v2/local/search/keyword.json"
        params = {
            "query": keyword,
            "sort": sort,
            "page": page,
            "size": size
        }

        if x is not None and y is not None:
            params["x"] = x
            params["y"] = y

        if radius is not None:
            params["radius"] = min(radius, 20000)

        logger.info(f"장소 검색: {keyword}")

        try:
            response = self._make_request(endpoint, params)

            places = []
            for place in response.get("documents", []):
                place_data = {
                    "name": place.get("place_name", ""),
                    "address": place.get("address_name", ""),
                    "road_address": place.get("road_address_name", ""),
                    "phone": place.get("phone", ""),
                    "latitude": float(place.get("y", 0)),
                    "longitude": float(place.get("x", 0)),
                    "category": place.get("category_name", ""),
                    "place_url": place.get("place_url", ""),
                    "distance": place.get("distance", "")
                }
                places.append(place_data)

            result = {
                "keyword": keyword,
                "total_count": response.get("meta", {}).get("total_count", 0),
                "places": places
            }

            logger.success(f"장소 검색 완료: {len(places)}개 결과")
            return result

        except Exception as e:
            logger.error(f"장소 검색 실패: {e}")
            raise

    def category_search(self, category: str, x: float, y: float,
                        radius: int = 1000, page: int = 1, size: int = 15) -> Dict[str, Any]:
        """
        CategorySearch_kakao: 카테고리 장소 검색

        Args:
            category: 카테고리 코드 (MT1, CS2, PS3 등)
            x: 중심 좌표 경도
            y: 중심 좌표 위도
            radius: 검색 반경(미터, 0~20000)
            page: 페이지 번호
            size: 한 페이지 결과 수 (1~15)

        Returns:
            카테고리 검색 결과
        """
        endpoint = "/v2/local/search/category.json"
        params = {
            "category_group_code": category,
            "x": x,
            "y": y,
            "radius": min(radius, 20000),
            "page": page,
            "size": size
        }

        # 카테고리 매핑
        category_names = {
            "MT1": "대형마트", "CS2": "편의점", "PS3": "어린이집",
            "SC4": "학교", "AC5": "학원", "PK6": "주차장",
            "OL7": "주유소", "SW8": "지하철역", "BK9": "은행",
            "CT1": "문화시설", "AG2": "중개업소", "PO3": "공공기관",
            "AT4": "관광명소", "AD5": "숙박", "FD6": "음식점",
            "CE7": "카페", "HP8": "병원", "PM9": "약국"
        }

        logger.info(f"카테고리 검색: {category} ({category_names.get(category, category)})")

        try:
            response = self._make_request(endpoint, params)

            places = []
            for place in response.get("documents", []):
                place_data = {
                    "name": place.get("place_name", ""),
                    "address": place.get("address_name", ""),
                    "road_address": place.get("road_address_name", ""),
                    "phone": place.get("phone", ""),
                    "latitude": float(place.get("y", 0)),
                    "longitude": float(place.get("x", 0)),
                    "category": place.get("category_name", ""),
                    "place_url": place.get("place_url", ""),
                    "distance": place.get("distance", "")
                }
                places.append(place_data)

            result = {
                "category_code": category,
                "category_name": category_names.get(category, category),
                "total_count": response.get("meta", {}).get("total_count", 0),
                "places": places
            }

            logger.success(f"카테고리 검색 완료: {len(places)}개 결과")
            return result

        except Exception as e:
            logger.error(f"카테고리 검색 실패: {e}")
            raise

# 테스트용 함수
def test_kakao_api():
    """카카오 로컬 API 테스트"""
    try:
        api = KakaoAPI()

        # 1. 주소-좌표 변환
        print("=== 주소-좌표 변환 ===")
        coord = api.address_to_coord("서울 강남구 역삼동 825")
        print(f"역삼동 좌표: {coord['latitude']}, {coord['longitude']}")

        # 2. 좌표-주소 변환
        print("\n=== 좌표-주소 변환 ===")
        address = api.coord_to_address(coord['latitude'], coord['longitude'])
        print(f"도로명주소: {address['road_address']}")

        # 3. 장소 검색
        print("\n=== 장소 검색 ===")
        places = api.place_search("스타벅스", size=5)
        print(f"스타벅스 검색 결과: {places['total_count']}개")
        print(f"첫 번째 매장: {places['places'][0]['name']}")

        # 4. 카테고리 검색 (강남역 근처 카페)
        print("\n=== 카테고리 검색 ===")
        cafes = api.category_search("CE7", coord['longitude'], coord['latitude'], radius=500, size=3)
        print(f"강남역 근처 카페: {len(cafes['places'])}개")

        return True

    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_kakao_api()