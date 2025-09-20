"""
T맵 API 클래스
- POISearch_tmap: POI 통합검색
- CarRoute_tmap: 자동차 경로안내
- WalkRoute_tmap: 보행자 경로안내
- Geocoding_tmap: 주소 좌표 변환
- CategorySearch_tmap: 카테고리별 장소 검색
"""

import requests
from typing import Dict, List, Any, Optional
from loguru import logger
import sys
import os

# 설정 파일 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings

class TmapAPI:
    """T맵 Open API 클래스"""

    def __init__(self):
        self.base_url = settings.TMAP_API_URL
        self.app_key = settings.TMAP_APP_KEY

        if not self.app_key:
            raise ValueError("TMAP_APP_KEY가 설정되지 않았습니다.")

        self.session = requests.Session()
        self.session.headers.update({
            'appKey': self.app_key,
            'Content-Type': 'application/json',
            'User-Agent': 'TmapAPI/1.0'
        })
        logger.info(f"T맵 API 초기화: {self.base_url}")

    def _make_request(self, endpoint: str, params: Dict = None, method: str = "GET") -> Dict[str, Any]:
        """API 요청 공통 메서드"""
        try:
            url = f"{self.base_url}{endpoint}"
            logger.debug(f"요청 URL: {url}, 파라미터: {params}")

            if method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=settings.REQUEST_TIMEOUT)
            else:
                response = self.session.post(url, json=params, timeout=settings.REQUEST_TIMEOUT)

            response.raise_for_status()

            logger.info(f"API 요청 성공: {endpoint}")
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"T맵 API 요청 실패: {e}")
            raise

    def poi_search(self, search_keyword: str, count: int = 10,
                   center_lon: Optional[float] = None, center_lat: Optional[float] = None,
                   radius: Optional[int] = None, page: int = 1) -> Dict[str, Any]:
        """
        POISearch_tmap: POI 통합검색

        Args:
            search_keyword: 검색 키워드
            count: 검색 결과 개수 (1~200)
            center_lon: 검색 중심 경도
            center_lat: 검색 중심 위도
            radius: 검색 반경(미터)
            page: 페이지 번호

        Returns:
            POI 검색 결과
        """
        endpoint = "/tmap/pois"
        params = {
            "version": 1,
            "searchKeyword": search_keyword,
            "count": min(count, 200),
            "page": page,
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO"
        }

        if center_lon is not None and center_lat is not None:
            params["centerLon"] = center_lon
            params["centerLat"] = center_lat

        if radius is not None:
            params["radius"] = radius

        logger.info(f"POI 검색: {search_keyword}")

        try:
            response = self._make_request(endpoint, params)

            pois = []
            poi_list = response.get("searchPoiInfo", {}).get("pois", {}).get("poi", [])

            # poi_list가 딕셔너리인 경우 (결과가 1개) 리스트로 변환
            if isinstance(poi_list, dict):
                poi_list = [poi_list]

            for poi in poi_list:
                poi_data = {
                    "name": poi.get("name", ""),
                    "telNo": poi.get("telNo", ""),
                    "frontLat": poi.get("frontLat", ""),
                    "frontLon": poi.get("frontLon", ""),
                    "noorLat": poi.get("noorLat", ""),
                    "noorLon": poi.get("noorLon", ""),
                    "upperAddrName": poi.get("upperAddrName", ""),
                    "middleAddrName": poi.get("middleAddrName", ""),
                    "lowerAddrName": poi.get("lowerAddrName", ""),
                    "detailAddrName": poi.get("detailAddrName", ""),
                    "upperBizName": poi.get("upperBizName", ""),
                    "middleBizName": poi.get("middleBizName", ""),
                    "lowerBizName": poi.get("lowerBizName", ""),
                    "roadName": poi.get("roadName", ""),
                    "buildingIndex1": poi.get("buildingIndex1", ""),
                    "radius": poi.get("radius", "0")
                }
                pois.append(poi_data)

            total_count = int(response.get("searchPoiInfo", {}).get("totalCount", 0))

            result = {
                "searchKeyword": search_keyword,
                "totalCount": total_count,
                "count": len(pois),
                "page": page,
                "pois": pois
            }

            logger.success(f"POI 검색 완료: {len(pois)}개 결과")
            return result

        except Exception as e:
            logger.error(f"POI 검색 실패: {e}")
            raise

    def car_route(self, start_x: float, start_y: float, end_x: float, end_y: float,
                  search_option: int = 0) -> Dict[str, Any]:
        """
        CarRoute_tmap: 자동차 경로안내

        Args:
            start_x: 출발지 경도
            start_y: 출발지 위도
            end_x: 도착지 경도
            end_y: 도착지 위도
            search_option: 경로 검색 옵션 (0~10)

        Returns:
            자동차 경로 정보
        """
        endpoint = "/tmap/routes"
        data = {
            "startX": start_x,
            "startY": start_y,
            "endX": end_x,
            "endY": end_y,
            "searchOption": search_option,
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO"
        }

        logger.info(f"자동차 경로 검색: ({start_y}, {start_x}) → ({end_y}, {end_x})")

        try:
            response = self._make_request(endpoint, data, method="POST")

            features = response.get("features", [])

            # 경로 정보 추출
            route_info = {}
            routes = []

            for feature in features:
                properties = feature.get("properties", {})
                geometry = feature.get("geometry", {})

                if properties.get("totalDistance"):
                    route_info = {
                        "totalDistance": properties.get("totalDistance"),
                        "totalTime": properties.get("totalTime"),
                        "totalFare": properties.get("totalFare", 0),
                        "taxiFare": properties.get("taxiFare", 0)
                    }

                if geometry.get("type") == "LineString":
                    coordinates = geometry.get("coordinates", [])
                    for i, coord in enumerate(coordinates):
                        route_point = {
                            "pointIndex": i,
                            "longitude": coord[0],
                            "latitude": coord[1],
                            "instruction": properties.get("description", ""),
                            "roadName": properties.get("name", ""),
                            "distance": properties.get("distance", 0),
                            "time": properties.get("time", 0)
                        }
                        routes.append(route_point)

            result = {
                "startX": start_x,
                "startY": start_y,
                "endX": end_x,
                "endY": end_y,
                "searchOption": search_option,
                **route_info,
                "routes": routes
            }

            logger.success(f"경로 검색 완료: {route_info.get('totalDistance', 0)}m, {route_info.get('totalTime', 0)}초")
            return result

        except Exception as e:
            logger.error(f"자동차 경로 검색 실패: {e}")
            raise

    def walk_route(self, start_x: float, start_y: float, end_x: float, end_y: float,
                   start_name: str = "출발지", end_name: str = "목적지") -> Dict[str, Any]:
        """
        WalkRoute_tmap: 보행자 경로안내

        Args:
            start_x: 출발지 경도
            start_y: 출발지 위도
            end_x: 도착지 경도
            end_y: 도착지 위도
            start_name: 출발지 명칭
            end_name: 목적지 명칭

        Returns:
            보행자 경로 정보
        """
        endpoint = "/tmap/routes/pedestrian"
        data = {
            "startX": start_x,
            "startY": start_y,
            "endX": end_x,
            "endY": end_y,
            "startName": start_name,
            "endName": end_name,
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "searchOption": 0
        }

        logger.info(f"보행자 경로 검색: ({start_y}, {start_x}) → ({end_y}, {end_x})")

        try:
            response = self._make_request(endpoint, data, method="POST")

            features = response.get("features", [])

            # 경로 정보 추출
            route_info = {}
            routes = []

            for feature in features:
                properties = feature.get("properties", {})
                geometry = feature.get("geometry", {})

                # 총 거리와 시간 정보 (SP 포인트에서 추출)
                if properties.get("pointType") == "SP":
                    route_info = {
                        "totalDistance": properties.get("totalDistance", 0),
                        "totalTime": properties.get("totalTime", 0)
                    }

                # 경로 포인트 정보
                if geometry.get("type") == "Point":
                    coordinates = geometry.get("coordinates", [])
                    if coordinates:
                        route_point = {
                            "pointIndex": properties.get("pointIndex", 0),
                            "longitude": coordinates[0],
                            "latitude": coordinates[1],
                            "instruction": properties.get("description", ""),
                            "roadName": properties.get("name", ""),
                            "distance": properties.get("distance", 0),
                            "time": properties.get("time", 0),
                            "facilityType": properties.get("facilityType", ""),
                            "facilityName": properties.get("facilityName", ""),
                            "turnType": properties.get("turnType", 0)
                        }
                        routes.append(route_point)

            result = {
                "startX": start_x,
                "startY": start_y,
                "endX": end_x,
                "endY": end_y,
                **route_info,
                "routes": routes
            }

            logger.success(f"보행자 경로 완료: {route_info.get('totalDistance', 0)}m, {route_info.get('totalTime', 0)}초")
            return result

        except Exception as e:
            logger.error(f"보행자 경로 검색 실패: {e}")
            raise

    def geocoding(self, full_addr: str, coord_type: str = "WGS84GEO") -> Dict[str, Any]:
        """
        Geocoding_tmap: 주소 좌표 변환

        Args:
            full_addr: 변환할 주소
            coord_type: 좌표계 타입

        Returns:
            주소 변환 결과
        """
        endpoint = "/tmap/geo/geocoding"
        params = {
            "version": 1,
            "fullAddr": full_addr,
            "coordType": coord_type
        }

        logger.info(f"주소 좌표 변환: {full_addr}")

        try:
            response = self._make_request(endpoint, params)

            coord_info = response.get("coordinateInfo", {})
            coordinate = coord_info.get("coordinate", [])

            if not coordinate:
                raise ValueError(f"주소 '{full_addr}'에 대한 좌표를 찾을 수 없습니다.")

            coord_data = coordinate[0] if isinstance(coordinate, list) else coordinate

            result = {
                "fullAddr": full_addr,
                "addressType": coord_data.get("addressType", ""),
                "city_do": coord_data.get("city_do", ""),
                "gu_gun": coord_data.get("gu_gun", ""),
                "eup_myun": coord_data.get("eup_myun", ""),
                "adminDong": coord_data.get("adminDong", ""),
                "adminDongCode": coord_data.get("adminDongCode", ""),
                "legalDong": coord_data.get("legalDong", ""),
                "legalDongCode": coord_data.get("legalDongCode", ""),
                "ri": coord_data.get("ri", ""),
                "bunji": coord_data.get("bunji", ""),
                "roadName": coord_data.get("roadName", ""),
                "bldNo1": coord_data.get("bldNo1", ""),
                "bldNo2": coord_data.get("bldNo2", ""),
                "buildingName": coord_data.get("buildingName", ""),
                "mappingDistance": coord_data.get("mappingDistance", ""),
                "roadCode": coord_data.get("roadCode", ""),
                "lon": float(coord_data.get("lon", 0)),
                "lat": float(coord_data.get("lat", 0))
            }

            logger.success(f"주소 변환 완료: {result['lat']}, {result['lon']}")
            return result

        except Exception as e:
            logger.error(f"주소 좌표 변환 실패: {e}")
            raise

    def coord_convert(self, lat: float, lon: float, from_coord: str = "WGS84GEO",
                      to_coord: str = "WGS84GEO") -> Optional[Dict[str, Any]]:
        """
        좌표 변환 API

        Args:
            lat: 위도
            lon: 경도
            from_coord: 원본 좌표계
            to_coord: 변환할 좌표계

        Returns:
            변환된 좌표 정보
        """
        endpoint = "/tmap/geo/coordconvert"
        params = {
            "version": 1,
            "lat": lat,
            "lon": lon,
            "fromCoord": from_coord,
            "toCoord": to_coord
        }

        logger.info(f"좌표 변환: {from_coord} → {to_coord}")

        try:
            response = self._make_request(endpoint, params)

            coordinate = response.get("coordinate", {})

            result = {
                "lat": coordinate.get("lat"),
                "lon": coordinate.get("lon"),
                "from_coord": from_coord,
                "to_coord": to_coord
            }

            logger.success(f"좌표 변환 완료: {result['lat']}, {result['lon']}")
            return result

        except Exception as e:
            logger.error(f"좌표 변환 실패: {e}")
            return None
        """
        CategorySearch_tmap: 카테고리별 장소 검색
        
        Args:
            categories: T맵 업종 카테고리
            center_lon: 검색 중심 경도
            center_lat: 검색 중심 위도
            radius: 검색 반경(미터)
            count: 검색 결과 개수
            
        Returns:
            카테고리 검색 결과
        """
        # T맵의 카테고리 검색은 POI 검색을 활용하여 구현
        search_keyword = categories

        logger.info(f"카테고리 검색: {categories}")

        try:
            result = self.poi_search(
                search_keyword=search_keyword,
                count=count,
                center_lon=center_lon,
                center_lat=center_lat,
                radius=radius
            )

            # 결과 형태 변환
            category_result = {
                "categories": categories,
                "centerLon": center_lon,
                "centerLat": center_lat,
                "radius": radius,
                "totalCount": result["totalCount"],
                "pois": result["pois"]
            }

            logger.success(f"카테고리 검색 완료: {len(result['pois'])}개 결과")
            return category_result

        except Exception as e:
            logger.error(f"카테고리 검색 실패: {e}")
            raise

# 테스트용 함수
def test_tmap_api():
    """T맵 API 테스트"""
    try:
        api = TmapAPI()

        # 1. POI 검색
        print("=== POI 검색 ===")
        pois = api.poi_search("스타벅스", count=5)
        print(f"스타벅스 검색 결과: {pois['totalCount']}개")
        if pois['pois']:
            print(f"첫 번째 매장: {pois['pois'][0]['name']}")

        # 2. 좌표 변환 (POI에서 좌표 가져와서 변환 테스트)
        if pois['pois']:
            print("\n=== 좌표 변환 테스트 ===")
            first_poi = pois['pois'][0]
            lat = float(first_poi['frontLat'])
            lon = float(first_poi['frontLon'])
            print(f"첫 번째 POI 좌표: {lat}, {lon}")

            # 좌표 변환 API 테스트
            converted = api.coord_convert(lat, lon, "WGS84GEO", "KATECH")
            if converted:
                print(f"KATECH 좌표로 변환: {converted['lat']}, {converted['lon']}")

        # 3. 자동차 경로 (강남역 → 홍대입구역 대략적 좌표)
        print("\n=== 자동차 경로 ===")
        route = api.car_route(127.027583, 37.497928, 126.924191, 37.556844)
        print(f"경로: {route.get('totalDistance', 0)}m, {route.get('totalTime', 0)}초")

        # 4. 보행자 경로 (짧은 거리로 테스트)
        print("\n=== 보행자 경로 ===")
        walk = api.walk_route(127.027583, 37.497928, 127.030000, 37.500000)
        print(f"도보: {walk.get('totalDistance', 0)}m, {walk.get('totalTime', 0)}초")

        return True

    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_tmap_api()