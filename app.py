import json
import os

import folium
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from matplotlib import font_manager, rc
from streamlit_folium import st_folium

from src.pipeline import start_browser, run_recommendation_after_location_allowed
from src.rag_guide import retrieve_emergency_guides, create_guide_text
from src.pdf_writer import save_emergency_guide_pdf
from src.distance import geocode_address
from src.email_sender import send_email_with_files


def set_korean_font():
    # 그래프에서 한글이 깨지지 않도록 폰트 설정
    try:
        font_path = "C:/Windows/Fonts/malgun.ttf"
        font_name = font_manager.FontProperties(fname=font_path).get_name()
        rc("font", family=font_name)
    except Exception:
        pass

    plt.rcParams["axes.unicode_minus"] = False


def load_symptoms():
    # symptoms.json 파일에서 증상 정보 불러오기
    with open("symptoms.json", "r", encoding="utf-8") as f:
        return json.load(f)


def classify_symptom(user_symptom, symptoms):
    # 사용자가 입력한 자연어 증상을 간단한 키워드 기반으로 분류
    text = user_symptom.strip()

    keyword_map = {
        "1": ["숨", "호흡", "숨참", "호흡곤란", "산소", "기침"],
        "2": ["가슴", "흉통", "심장", "심근경색", "심정지", "식은땀"],
        "3": ["피", "출혈", "교통사고", "넘어", "골절", "다침", "상처", "외상", "베", "베임", "유리", "칼", "찢"],
        "4": ["마비", "경련", "의식", "어지러", "말이", "뇌졸중", "두통"],
        "5": ["아이", "소아", "아기", "어린이", "고열", "열"],
        "6": ["화상", "데임", "불", "뜨거운", "끓는"],
        "7": ["중독", "약", "음독", "가스", "농약", "화학"],
        "8": ["감염", "고열", "기침", "코로나", "격리", "전염"]
    }

    for key, keywords in keyword_map.items():
        for keyword in keywords:
            if keyword in text:
                return symptoms[key], key

    return None, None


def hospitals_to_dataframe(hospitals):
    # 최종 추천 병원 리스트를 화면 표시용 DataFrame으로 변환
    rows = []

    for h in hospitals:
        web_info = h.get("정리된웹병상정보", {})

        rows.append({
            "추천순위": h.get("추천순위"),
            "병원명": h.get("웹병원명"),
            "주소": h.get("주소"),
            "추천점수": h.get("추천점수"),
            "직선거리(km)": h.get("직선거리_km"),
            "실제이동거리(km)": h.get("이동거리_km"),
            "예상이동시간(분)": h.get("예상이동시간_분"),
            "응급실일반": web_info.get("응급실일반"),
            "혼잡도": web_info.get("응급실일반_혼잡도"),
            "응급실소아": web_info.get("응급실소아"),
            "중환자실": h.get("중환자실_API"),
            "수술실": h.get("수술실_API"),
            "CT가능": h.get("CT가능"),
            "MRI가능": h.get("MRI가능"),
            "인공호흡기": h.get("인공호흡기"),
            "추천사유": h.get("추천사유")
        })

    return pd.DataFrame(rows)


def draw_chart(hospitals):
    # 추천 병원 TOP 5 그래프 생성
    set_korean_font()

    top5 = hospitals[:5]

    names = [h.get("웹병원명", "알 수 없음") for h in top5]
    scores = [min(int(h.get("추천점수", 0)), 100) for h in top5]

    # 1위가 위쪽에 보이도록 순서 뒤집기
    names = names[::-1]
    scores = scores[::-1]
    top5_reversed = top5[::-1]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.barh(names, scores)

    ax.set_title("응급실 추천 TOP 5", fontsize=17, pad=15)
    ax.set_xlabel("추천점수 (100점 만점)")
    ax.set_ylabel("병원명")
    ax.set_xlim(0, 100)

    # 막대마다 점수, 예상시간, 혼잡도, 병상 수 표시
    for bar, h, score in zip(bars, top5_reversed, scores):
        web_info = h.get("정리된웹병상정보", {})

        time = h.get("예상이동시간_분", "-")
        congestion = web_info.get("응급실일반_혼잡도", "-")
        beds = web_info.get("응급실일반", "-")

        label = f"{score}점 | {time}분 | {congestion} | 병상 {beds}개"
        y = bar.get_y() + bar.get_height() / 2

        # 점수가 높으면 막대 안쪽에 표시
        if score >= 45:
            ax.text(
                score - 2,
                y,
                label,
                va="center",
                ha="right",
                fontsize=10,
                color="white"
            )
        else:
            # 점수가 낮으면 막대 바깥쪽에 표시
            ax.text(
                score + 1,
                y,
                label,
                va="center",
                ha="left",
                fontsize=10,
                color="black"
            )

    ax.grid(axis="x", linestyle="--", alpha=0.3)
    fig.tight_layout()

    return fig


def draw_top5_map(hospitals, user_address):
    # 사용자 주소를 좌표로 변환
    user_coord = geocode_address(user_address)

    if user_coord is None:
        st.warning("사용자 주소 좌표를 찾을 수 없어 지도를 생성할 수 없습니다.")
        return

    top5 = hospitals[:5]

    # 사용자 위치를 중심으로 지도 생성
    m = folium.Map(
        location=[user_coord["lat"], user_coord["lon"]],
        zoom_start=12
    )

    # 사용자 위치 마커 표시
    folium.Marker(
        location=[user_coord["lat"], user_coord["lon"]],
        tooltip="환자 현재 위치",
        popup="환자 현재 위치",
        icon=folium.Icon(color="red", icon="home")
    ).add_to(m)

    # 추천 병원 TOP 5 마커 표시
    for hospital in top5:
        lat = hospital.get("위도")
        lon = hospital.get("경도")

        if lat is None or lon is None:
            continue

        web_info = hospital.get("정리된웹병상정보", {})

        rank = hospital.get("추천순위", "-")
        name = hospital.get("웹병원명", "병원명 없음")
        score = hospital.get("추천점수", "-")
        travel_time = hospital.get("예상이동시간_분", "-")
        distance = hospital.get("이동거리_km", "-")
        congestion = web_info.get("응급실일반_혼잡도", "-")
        beds = web_info.get("응급실일반", "-")

        popup_html = f"""
        <b>{rank}위. {name}</b><br>
        추천점수: {score}점<br>
        예상시간: {travel_time}분<br>
        이동거리: {distance}km<br>
        혼잡도: {congestion}<br>
        응급실 병상: {beds}개
        """

        color = "blue"

        if rank == 1:
            color = "green"
        elif rank == 2:
            color = "purple"
        elif rank == 3:
            color = "orange"

        folium.Marker(
            location=[lat, lon],
            tooltip=f"{rank}위 {name}",
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=color, icon="plus-sign")
        ).add_to(m)

        # 사용자 위치와 병원 위치를 선으로 연결
        folium.PolyLine(
            locations=[
                [user_coord["lat"], user_coord["lon"]],
                [lat, lon]
            ],
            weight=2,
            opacity=0.5
        ).add_to(m)

    st_folium(m, width=1100, height=520)


def get_result_file_paths(result):
    # 이메일에 첨부할 결과 파일 경로 모으기
    file_paths = []

    excel_path = result.get("excel_path")
    chart_path = result.get("chart_path")
    pdf_path = result.get("pdf_path") or st.session_state.get("guide_pdf_path")

    if excel_path and os.path.exists(excel_path):
        file_paths.append(excel_path)

    if chart_path and os.path.exists(chart_path):
        file_paths.append(chart_path)

    if pdf_path and os.path.exists(pdf_path):
        file_paths.append(pdf_path)

    return file_paths


def init_session_state():
    # Streamlit 세션 상태 기본값 설정
    default_values = {
        "page": "guide",
        "driver": None,
        "symptom": None,
        "symptom_key": None,
        "symptom_text": "",
        "guide_pdf_path": None,
        "result": None,
        "address_input": "",
        "patient_address": ""
    }

    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_selected_symptom(symptom, key):
    # 증상이 바뀌면 이전 PDF와 추천 결과를 초기화
    if st.session_state.symptom_key != key:
        st.session_state.guide_pdf_path = None
        st.session_state.result = None
        st.session_state.patient_address = ""

    # 현재 선택된 증상 저장
    st.session_state.symptom = symptom
    st.session_state.symptom_key = key


def go_to_page(page_name):
    # 페이지 이동 후 화면 새로고침
    st.session_state.page = page_name
    st.rerun()


def render_step_indicator():
    # 현재 단계 표시
    current = st.session_state.page

    col1, col2, col3 = st.columns(3)

    with col1:
        if current == "guide":
            st.success("1단계: 응급처치 가이드")
        else:
            st.info("1단계: 응급처치 가이드")

    with col2:
        if current == "recommend":
            st.success("2단계: 응급실 추천")
        else:
            st.info("2단계: 응급실 추천")

    with col3:
        if current == "result":
            st.success("3단계: 결과 확인")
        else:
            st.info("3단계: 결과 확인")


def render_guide_page(symptoms):
    # 1단계 화면
    st.markdown("## 1단계. 증상 입력 및 응급처치 가이드 생성")

    st.write(
        "환자의 현재 증상을 입력하거나 아래 목록에서 직접 선택하면, "
        "RAG 기반 응급처치 가이드 PDF를 먼저 생성합니다."
    )

    left, right = st.columns([1.2, 1])

    with left:
        user_symptom_text = st.text_area(
            "현재 증상을 입력하세요",
            value=st.session_state.symptom_text,
            placeholder="예: 가슴이 답답하고 식은땀이 나요 / 유리에 베여 피가 나요 / 화상을 입었어요",
            height=130
        )

        # 입력한 증상 텍스트 저장
        st.session_state.symptom_text = user_symptom_text

        if st.button("입력한 증상으로 자동 분류", use_container_width=True):
            symptom, key = classify_symptom(user_symptom_text, symptoms)

            if symptom is None:
                st.warning("자동 분류가 어렵습니다. 오른쪽에서 증상을 직접 선택해주세요.")
            else:
                # 증상 적용 및 기존 PDF 초기화 처리
                apply_selected_symptom(symptom, key)
                st.success(f"분류된 증상: {symptom['name']}")

    with right:
        symptom_options = {key: value["name"] for key, value in symptoms.items()}

        selected_key = st.selectbox(
            "증상 직접 선택",
            options=list(symptom_options.keys()),
            format_func=lambda x: f"{x}. {symptom_options[x]}"
        )

        if st.button("선택한 증상 적용", use_container_width=True):
            # 직접 선택한 증상 적용 및 기존 PDF 초기화 처리
            apply_selected_symptom(symptoms[selected_key], selected_key)
            st.success(f"선택된 증상: {symptoms[selected_key]['name']}")

    st.divider()

    if st.session_state.symptom is not None:
        symptom = st.session_state.symptom

        st.markdown("### 선택된 증상 정보")
        st.write(f"**증상명:** {symptom['name']}")
        st.write(f"**설명:** {symptom.get('description', '-')}")
        st.write(f"**필요 병상:** {', '.join(symptom.get('required_beds', []))}")
        st.write(f"**우선 의료 자원:** {', '.join(symptom.get('preferred_resources', []))}")

        col_a, col_b = st.columns([1, 1])

        with col_a:
            if st.button("응급처치 가이드 생성하기", use_container_width=True):
                with st.spinner("전문 응급처치 자료를 검색하고 PDF를 생성하는 중입니다..."):
                    # 현재 선택된 증상을 기준으로 PDF 생성
                    current_symptom = st.session_state.symptom

                    retrieved_guides = retrieve_emergency_guides(current_symptom)
                    guide_text = create_guide_text(current_symptom, retrieved_guides)
                    pdf_path = save_emergency_guide_pdf(guide_text)

                    # 새로 생성된 PDF 경로 저장
                    st.session_state.guide_pdf_path = pdf_path

                st.success("응급처치 가이드 생성이 완료되었습니다.")

        with col_b:
            # PDF가 생성되어야 다음 단계로 이동 가능
            disabled = st.session_state.guide_pdf_path is None

            if st.button("다음 단계로 이동", disabled=disabled, use_container_width=True):
                go_to_page("recommend")

        # 생성된 PDF 다운로드 버튼 표시
        if st.session_state.guide_pdf_path and os.path.exists(st.session_state.guide_pdf_path):
            with open(st.session_state.guide_pdf_path, "rb") as f:
                st.download_button(
                    "응급처치 가이드 PDF 다운로드",
                    f,
                    file_name=os.path.basename(st.session_state.guide_pdf_path),
                    mime="application/pdf",
                    use_container_width=True
                )

    else:
        st.warning("먼저 증상을 입력하거나 직접 선택해주세요.")


def render_recommend_page():
    # 2단계 화면
    st.markdown("## 2단계. 주소 입력 및 응급실 추천")

    st.write(
        "환자의 현재 주소를 입력한 뒤, 내 손안의 응급실 사이트를 열어 위치 정보 접근을 허용해주세요. "
        "위치 정보 허용 후 응급실 목록이 보이면 추천 실행 버튼을 누르면 됩니다."
    )

    if st.session_state.symptom is not None:
        st.info(f"현재 선택된 증상: {st.session_state.symptom['name']}")

    user_address = st.text_input(
        "환자의 현재 주소를 입력하세요",
        placeholder="예: 서울특별시 노원구 ...",
        key="address_input"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("내 손안의 응급실 열기", use_container_width=True):
            with st.spinner("브라우저를 여는 중입니다..."):
                st.session_state.driver = start_browser()

            st.success("브라우저가 열렸습니다. 위치 정보 접근을 허용해주세요.")

    with col2:
        run_disabled = (
            st.session_state.driver is None
            or st.session_state.symptom is None
            or not user_address
        )

        if st.button("위치 허용 완료 후 추천 실행", disabled=run_disabled, use_container_width=True):
            st.session_state.patient_address = user_address

            with st.spinner("응급실 정보 수집, 거리 계산, 추천 점수 산정 중입니다..."):
                result = run_recommendation_after_location_allowed(
                    st.session_state.driver,
                    user_address,
                    st.session_state.symptom
                )

                # 1단계에서 생성한 PDF 경로를 결과에 포함
                if st.session_state.guide_pdf_path:
                    result["pdf_path"] = st.session_state.guide_pdf_path

                st.session_state.result = result

            st.success("추천 병원 생성이 완료되었습니다.")
            go_to_page("result")

    st.divider()

    if st.button("이전 단계로 이동", use_container_width=True):
        go_to_page("guide")


def render_email_section(result):
    # 결과 파일 이메일 전송 영역
    st.markdown("### 이메일로 결과 전송")

    with st.expander("네이버 메일로 결과 파일 보내기"):
        st.info(
            "네이버 메일에서 POP3/SMTP 사용을 켠 뒤, "
            "계정 비밀번호가 아니라 애플리케이션 비밀번호를 입력해야 합니다."
        )

        sender_email = st.text_input(
            "보내는 네이버 메일 주소",
            placeholder="example@naver.com"
        )

        sender_password = st.text_input(
            "네이버 애플리케이션 비밀번호",
            type="password"
        )

        receiver_email = st.text_input(
            "받는 사람 이메일 주소",
            placeholder="example@gmail.com"
        )

        email_subject = st.text_input(
            "메일 제목",
            value=" 응급실 추천 결과 보고서"
        )

        email_body = st.text_area(
            "메일 본문",
            value=(
                "안녕하세요.\n\n"
                "응급실 추천 결과를 전달드립니다.\n"
                "첨부파일에서 추천 병원 보고서, 추천 그래프, 응급처치 가이드를 확인할 수 있습니다.\n\n"
                "※ 본 결과는 참고용이며, 실제 응급 상황에서는 119 및 의료진의 안내를 따라야 합니다."
            ),
            height=160
        )

        file_paths = get_result_file_paths(result)

        # 첨부 예정 파일 표시
        if file_paths:
            st.write("첨부 예정 파일")
            for file_path in file_paths:
                st.write(f"- {os.path.basename(file_path)}")
        else:
            st.warning("첨부할 결과 파일이 없습니다.")

        if st.button("이메일 전송", use_container_width=True):
            if not sender_email or not sender_password or not receiver_email:
                st.warning("보내는 메일, 애플리케이션 비밀번호, 받는 사람 이메일을 모두 입력해주세요.")
                return

            if "@naver.com" not in sender_email:
                st.warning("보내는 메일은 네이버 메일 주소를 입력해주세요.")
                return

            try:
                send_email_with_files(
                    sender_email=sender_email,
                    sender_password=sender_password,
                    receiver_email=receiver_email,
                    subject=email_subject,
                    body=email_body,
                    file_paths=file_paths
                )

                st.success("이메일 전송이 완료되었습니다.")

            except Exception as e:
                st.error("이메일 전송 중 오류가 발생했습니다.")
                st.write(e)


def render_result_page():
    # 3단계 결과 화면
    st.markdown("## 3단계. 추천 결과 확인")

    result = st.session_state.result

    if result is None:
        st.warning("아직 추천 결과가 없습니다.")
        if st.button("응급실 추천 단계로 이동"):
            go_to_page("recommend")
        return

    hospitals = result["hospitals"]
    df = hospitals_to_dataframe(hospitals)

    st.markdown("### 최종 추천 병원 TOP 5")

    card_cols = st.columns(5)

    # TOP 5 병원 카드 표시
    for idx, h in enumerate(hospitals[:5]):
        web_info = h.get("정리된웹병상정보", {})

        rank = h.get("추천순위", "-")
        name = h.get("웹병원명", "병원명 없음")
        score = min(int(h.get("추천점수", 0)), 100)
        travel_time = h.get("예상이동시간_분", "-")
        distance = h.get("이동거리_km", "-")
        congestion = web_info.get("응급실일반_혼잡도", "-")
        beds = web_info.get("응급실일반", "-")

        with card_cols[idx]:
            with st.container(border=True):
                st.markdown(f"## {rank}위")
                st.markdown(f"### {name}")
                st.write(f"**추천점수:** {score}점")
                st.write(f"**예상시간:** {travel_time}분")
                st.write(f"**이동거리:** {distance}km")
                st.write(f"**혼잡도:** {congestion}")
                st.write(f"**병상:** {beds}개")

    st.divider()

    col1, col2 = st.columns([1.3, 1])

    with col1:
        st.markdown("### 추천 점수 시각화")
        fig = draw_chart(hospitals)
        st.pyplot(fig)

    with col2:
        st.markdown("### 1순위 추천 병원")
        top1 = hospitals[0]
        st.write(f"#### {top1.get('웹병원명')}")
        st.write(f"**주소:** {top1.get('주소')}")
        st.write(f"**추천점수:** {min(int(top1.get('추천점수', 0)), 100)}점")
        st.write(f"**이동거리:** {top1.get('이동거리_km')}km")
        st.write(f"**예상시간:** {top1.get('예상이동시간_분')}분")
        st.write(f"**추천사유:** {top1.get('추천사유')}")

    st.divider()

    st.markdown("### 추천 병원 TOP 5 지도")

    user_address = st.session_state.get("patient_address", "")

    if user_address:
        draw_top5_map(hospitals, user_address)
    else:
        st.warning("환자 주소 정보가 없어 지도를 표시할 수 없습니다.")

    st.divider()

    st.markdown("### 전체 추천 결과")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("### 결과 파일 다운로드")

    file_col1, file_col2, file_col3 = st.columns(3)

    with file_col1:
        excel_path = result.get("excel_path")
        if excel_path and os.path.exists(excel_path):
            with open(excel_path, "rb") as f:
                st.download_button(
                    "Excel 보고서 다운로드",
                    f,
                    file_name=os.path.basename(excel_path),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

    with file_col2:
        pdf_path = result.get("pdf_path") or st.session_state.guide_pdf_path
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "응급처치 가이드 PDF 다운로드",
                    f,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                    use_container_width=True
                )

    with file_col3:
        chart_path = result.get("chart_path")
        if chart_path and os.path.exists(chart_path):
            with open(chart_path, "rb") as f:
                st.download_button(
                    "추천 그래프 다운로드",
                    f,
                    file_name=os.path.basename(chart_path),
                    mime="image/png",
                    use_container_width=True
                )

    st.divider()

    render_email_section(result)

    st.divider()

    col_back, col_restart = st.columns(2)

    with col_back:
        if st.button("응급실 추천 단계로 돌아가기", use_container_width=True):
            go_to_page("recommend")

    with col_restart:
        if st.button("처음부터 다시 시작", use_container_width=True):
            st.session_state.page = "guide"
            st.session_state.driver = None
            st.session_state.symptom = None
            st.session_state.symptom_key = None
            st.session_state.symptom_text = ""
            st.session_state.guide_pdf_path = None
            st.session_state.result = None
            st.session_state.address_input = ""
            st.session_state.patient_address = ""
            st.rerun()


# Streamlit 기본 설정
st.set_page_config(
    page_title="위치·증상 기반 응급실 추천 및 응급처치 가이드 자동화 시스템",
    layout="wide"
)

# 세션 상태 초기화
init_session_state()

st.title("위치·증상 기반 응급실 추천 및 응급처치 가이드 자동화 시스템")

render_step_indicator()
st.divider()

# 증상 데이터 로드
symptoms = load_symptoms()

# 현재 페이지에 맞는 화면 출력
if st.session_state.page == "guide":
    render_guide_page(symptoms)

elif st.session_state.page == "recommend":
    render_recommend_page()

elif st.session_state.page == "result":
    render_result_page()