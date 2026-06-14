import os  # 파일 경로 처리
import json  # 좌표 캐시 저장
import math  # 거리 계산
import requests  # 카카오 API 호출

from dotenv import load_dotenv


# .env 파일 불러오기
load_dotenv()

# 카카오 REST API 키 가져오기
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

# 프로젝트 루트 경로
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 결과 폴더 경로
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# 병원 좌표 캐시 파일 경로
CACHE_FILE = os.path.join(OUTPUT_DIR, "hospital_coordinates_cache.json")


def get_headers():
    # 카카오 API 요청 헤더 생성
    return {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
    }


def load_cache():
    # output 폴더가 없으면 생성
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 캐시 파일이 없으면 빈 딕셔너리 반환
    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        # 캐시 파일 읽기
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        # 캐시 파일 오류 시 빈 캐시 사용
        return {}


def save_cache(cache):
    # output 폴더 생성
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 좌표 캐시 저장
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def clean_address(address):
    # 주소가 없으면 빈 문자열 반환
    if not address:
        return ""

    # 주소 문자열 정리
    address = str(address).strip()

    # 괄호 뒤 상세주소 제거
    address = address.split("(")[0]

    # 쉼표 뒤 내용 제거
    address = address.split(",")[0]

    return address.strip()


def geocode_address(address, use_cache=True):
    # 주소 전처리
    address = clean_address(address)

    # 주소가 비어 있으면 변환 실패 처리
    if not address:
        return None

    # 캐시 사용 여부 확인
    cache = load_cache() if use_cache else {}

    # 이미 변환한 주소면 캐시 좌표 반환
    if use_cache and address in cache:
        return cache[address]

    # 카카오 주소 검색 API
    url = "https://dapi.kakao.com/v2/local/search/address.json"

    try:
        # 주소 좌표 변환 API 요청
        response = requests.get(
            url,
            headers=get_headers(),
            params={"query": address},
            timeout=5
        )

        # 요청 실패 시 None 반환
        if response.status_code != 200:
            print("주소 좌표 변환 실패:", address)
            return None

        # JSON 응답 변환
        data = response.json()

        # 검색 결과 추출
        documents = data.get("documents", [])

        # 검색 결과가 없으면 None 반환
        if not documents:
            print("주소 검색 결과 없음:", address)
            return None

        # 경도, 위도 추출
        lon = float(documents[0]["x"])
        lat = float(documents[0]["y"])

        # 좌표 딕셔너리 생성
        coord = {
            "lat": lat,
            "lon": lon
        }

        # 캐시 사용 시 좌표 저장
        if use_cache:
            cache[address] = coord
            save_cache(cache)

        return coord

    except Exception as e:
        # 주소 변환 중 오류 발생 시 None 반환
        print("주소 변환 중 오류:", address)
        print(e)
        return None


def haversine_distance(lat1, lon1, lat2, lon2):
    # 지구 반지름(km)
    earth_radius = 6371

    # 위도, 경도를 라디안으로 변환
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # 위도, 경도 차이 계산
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # 하버사인 공식 계산
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )

    # 중심각 계산
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # km 단위 거리 반환
    return round(earth_radius * c, 2)


def add_coordinates_and_straight_distance(hospitals, user_address):
    # 사용자 주소 좌표 변환
    user_coord = geocode_address(user_address)

    # 사용자 좌표 변환 실패 시 기존 병원 목록 반환
    if user_coord is None:
        print("사용자 주소 좌표 변환 실패")
        return hospitals

    result = []

    # 병원별 좌표 변환 및 직선거리 계산
    for hospital in hospitals:
        address = hospital.get("주소", "")
        hospital_coord = geocode_address(address)

        # 병원 좌표 변환 실패 시 정렬에서 뒤로 보내기
        if hospital_coord is None:
            hospital["위도"] = None
            hospital["경도"] = None
            hospital["직선거리_km"] = 9999

        else:
            # 병원 좌표 저장
            hospital["위도"] = hospital_coord["lat"]
            hospital["경도"] = hospital_coord["lon"]

            # 사용자 위치와 병원 사이의 직선거리 계산
            hospital["직선거리_km"] = haversine_distance(
                user_coord["lat"],
                user_coord["lon"],
                hospital_coord["lat"],
                hospital_coord["lon"]
            )

        result.append(hospital)

    # 직선거리 기준 가까운 순으로 정렬
    result.sort(key=lambda h: h.get("직선거리_km", 9999))

    return result


def get_directions(origin_lon, origin_lat, dest_lon, dest_lat):
    # 카카오 길찾기 API 주소
    url = "https://apis-navi.kakaomobility.com/v1/directions"

    # 길찾기 요청 파라미터
    params = {
        "origin": f"{origin_lon},{origin_lat}",
        "destination": f"{dest_lon},{dest_lat}",
        "priority": "TIME"
    }

    try:
        # 길찾기 API 요청
        response = requests.get(
            url,
            headers=get_headers(),
            params=params,
            timeout=8
        )

        # 요청 실패 시 None 반환
        if response.status_code != 200:
            print("길찾기 API 호출 실패:", response.status_code)
            return None

        # JSON 응답 변환
        data = response.json()

        # 경로 목록 가져오기
        routes = data.get("routes", [])

        # 경로가 없으면 None 반환
        if not routes:
            return None

        # 첫 번째 경로 요약 정보 사용
        summary = routes[0].get("summary", {})

        # 이동거리와 이동시간 추출
        distance_m = summary.get("distance")
        duration_sec = summary.get("duration")

        # 값이 없으면 None 반환
        if distance_m is None or duration_sec is None:
            return None

        return {
            "이동거리_km": round(distance_m / 1000, 2),
            "예상이동시간_분": round(duration_sec / 60, 1)
        }

    except Exception as e:
        # 길찾기 API 오류 처리
        print("길찾기 API 오류")
        print(e)
        return None


def add_directions_to_top10(hospitals, user_address):
    # 사용자 주소 좌표 변환
    user_coord = geocode_address(user_address)

    # 사용자 좌표 변환 실패 시 TOP10만 반환
    if user_coord is None:
        print("사용자 주소 좌표 변환 실패")
        return hospitals[:10]

    # 직선거리 기준 가까운 10개 병원 선택
    top10 = hospitals[:10]

    # TOP10 병원에 대해 실제 이동거리와 예상시간 계산
    for hospital in top10:
        lat = hospital.get("위도")
        lon = hospital.get("경도")

        # 병원 좌표가 없으면 이동정보 없음 처리
        if lat is None or lon is None:
            hospital["이동거리_km"] = None
            hospital["예상이동시간_분"] = None
            continue

        # 카카오 길찾기 API 호출
        directions = get_directions(
            user_coord["lon"],
            user_coord["lat"],
            lon,
            lat
        )

        # 길찾기 실패 시 직선거리로 대체
        if directions is None:
            hospital["이동거리_km"] = hospital.get("직선거리_km")
            hospital["예상이동시간_분"] = None

        else:
            # 실제 이동거리와 예상시간 저장
            hospital["이동거리_km"] = directions["이동거리_km"]
            hospital["예상이동시간_분"] = directions["예상이동시간_분"]

    return top10