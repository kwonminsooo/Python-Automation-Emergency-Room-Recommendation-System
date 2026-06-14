from src.scraper import open_egen_site, get_page_text, parse_hospital_text
from src.api_client import get_er_bed_dataframe
from src.matcher import merge_web_and_api_data
from src.scorer import score_hospitals
from src.excel_writer import save_recommendation_excel
from src.visualizer import draw_top5_chart
from src.distance import add_coordinates_and_straight_distance, add_directions_to_top10


def start_browser():
    # E-GEN 사이트 접속용 브라우저 실행
    return open_egen_site()


def run_recommendation_after_location_allowed(driver, user_address, symptom):
    # 현재 브라우저 화면에서 응급실 목록 텍스트 수집
    page_text = get_page_text(driver)
    web_hospitals = parse_hospital_text(page_text)

    # 공공데이터 API에서 병상/장비 정보 조회
    api_df = get_er_bed_dataframe()

    # 웹 수집 데이터와 API 데이터 병합
    hospitals = merge_web_and_api_data(web_hospitals, api_df)

    # 환자 주소 기준으로 병원별 직선거리 계산
    hospitals = add_coordinates_and_straight_distance(
        hospitals,
        user_address
    )

    # 가까운 병원 10곳에 대해 실제 이동거리와 예상시간 계산
    hospitals = add_directions_to_top10(
        hospitals,
        user_address
    )

    # 증상별 가중치를 반영해 추천 점수 계산
    scored_hospitals = score_hospitals(hospitals, symptom)

    # 추천 결과 파일 저장
    excel_path = save_recommendation_excel(scored_hospitals)
    chart_path = draw_top5_chart(scored_hospitals)

    # Streamlit 화면으로 넘길 결과
    result = {
        "hospitals": scored_hospitals,
        "excel_path": excel_path,
        "chart_path": chart_path,
        "pdf_path": None,
        "hospital_count": len(web_hospitals)
    }

    return result