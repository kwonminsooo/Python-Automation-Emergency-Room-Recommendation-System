import time
import re

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By


# 내 손안의 응급실 사이트 주소
EGEN_URL = "https://mediboard.nemc.or.kr/emergency_room_in_hand"


def open_egen_site():
    # 크롬 브라우저 옵션 설정
    options = webdriver.ChromeOptions()

    # 코드가 끝나도 브라우저가 바로 닫히지 않게 설정
    options.add_experimental_option("detach", True)

    # 크롬 드라이버 실행
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    # E-GEN 사이트 접속
    driver.get(EGEN_URL)

    # 브라우저 창 최대화
    driver.maximize_window()

    # 페이지 로딩 대기
    time.sleep(1)

    return driver


def get_page_text(driver):
    # 위치 허용 후 병원 목록이 뜰 시간을 기다림
    time.sleep(1)

    # 페이지 전체 body 텍스트 가져오기
    body = driver.find_element(By.TAG_NAME, "body")
    return body.text


def parse_hospital_text(text):
    # 줄 단위로 나누고 빈 줄 제거
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 병원 구분값
    hospital_types = {"기관", "센터", "권역"}
    hospitals = []

    i = 0

    # 전체 줄을 순서대로 확인
    while i < len(lines):
        # 병원 구분값을 만나면 병원 정보 시작으로 판단
        if lines[i] in hospital_types:
            hospital_type = lines[i]

            # 병원명, 주소, 길찾기 줄이 부족하면 종료
            if i + 3 >= len(lines):
                break

            name = lines[i + 1]
            address = lines[i + 2]

            # 예상한 위치에 길찾기가 없으면 병원 정보가 아니라고 판단
            if lines[i + 3] != "길찾기":
                i += 1
                continue

            # 다음 병원 시작 전까지 병상 관련 값 수집
            j = i + 4
            values = []

            while j < len(lines) and lines[j] not in hospital_types:
                values.append(lines[j])
                j += 1

            # 병원 정보를 dict 형태로 저장
            hospital = {
                "기관구분": hospital_type,
                "병원명": name,
                "주소": address,
                "원본값": values
            }

            hospitals.append(hospital)

            # 다음 병원 위치로 이동
            i = j
        else:
            i += 1

    return hospitals


def print_parsed_hospitals(driver):
    # 현재 페이지 텍스트 수집
    text = get_page_text(driver)

    # 병원 정보 파싱
    hospitals = parse_hospital_text(text)

    print(f"\n총 {len(hospitals)}개 병원 파싱 완료\n")

    # 확인용으로 앞의 5개 병원만 출력
    for h in hospitals[:5]:
        print(h)

    return hospitals