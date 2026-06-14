import os

import matplotlib.pyplot as plt
from matplotlib import font_manager, rc


def set_korean_font():
    try:
        # Windows 기본 한글 폰트 설정
        font_path = "C:/Windows/Fonts/malgun.ttf"
        font_name = font_manager.FontProperties(fname=font_path).get_name()
        rc("font", family=font_name)
    except Exception:
        print("한글 폰트 설정 실패. 그래프의 한글이 깨질 수 있습니다.")

    # 마이너스 기호 깨짐 방지
    plt.rcParams["axes.unicode_minus"] = False


def get_er_bed_count(hospital):
    # 정리된 웹 병상 정보 가져오기
    web_info = hospital.get("정리된웹병상정보", {})

    bed_value = web_info.get("응급실일반")

    # 정리된 값이 없으면 병원 dict에서 직접 가져오기
    if bed_value is None:
        bed_value = hospital.get("응급실일반")

    if bed_value is None:
        return "-"

    bed_value = str(bed_value).strip()

    # '7/22' 형식이면 사용 가능 병상 수만 추출
    if "/" in bed_value:
        return bed_value.split("/")[0]

    return bed_value


def get_congestion(hospital):
    # 정리된 웹 병상 정보 가져오기
    web_info = hospital.get("정리된웹병상정보", {})

    congestion = web_info.get("응급실일반_혼잡도")

    # 정리된 값이 없으면 병원 dict에서 직접 가져오기
    if congestion is None:
        congestion = hospital.get("응급실일반_혼잡도")

    if congestion is None or congestion == "":
        return "-"

    return congestion


def draw_top5_chart(scored_hospitals):
    # output 폴더 생성
    os.makedirs("output", exist_ok=True)

    # 그래프 한글 폰트 설정
    set_korean_font()

    # 추천 병원 상위 5개 선택
    top5 = scored_hospitals[:5]

    if not top5:
        print("그래프를 생성할 추천 병원 데이터가 없습니다.")
        return None

    # 병원명과 추천점수 추출
    hospital_names = [h.get("웹병원명", "알 수 없음") for h in top5]
    scores = [min(int(h.get("추천점수", 0)), 100) for h in top5]

    # 1위가 위쪽에 오도록 순서 뒤집기
    hospital_names = hospital_names[::-1]
    scores = scores[::-1]
    top5_reversed = top5[::-1]

    # 그래프 크기 설정
    plt.figure(figsize=(12, 6))

    # 가로 막대그래프 생성
    bars = plt.barh(hospital_names, scores)

    # 그래프 제목과 축 이름 설정
    plt.title("응급실 추천 TOP 5", fontsize=18, pad=18)
    plt.xlabel("추천점수 (100점 만점)", fontsize=12)
    plt.ylabel("병원명", fontsize=12)
    plt.xlim(0, 100)

    ax = plt.gca()

    # 각 막대에 점수, 이동시간, 혼잡도, 병상 수 표시
    for bar, hospital, score in zip(bars, top5_reversed, scores):
        travel_time = hospital.get("예상이동시간_분")
        congestion = get_congestion(hospital)
        er_beds = get_er_bed_count(hospital)

        if travel_time is None:
            travel_time_text = "시간 정보 없음"
        else:
            travel_time_text = f"{travel_time}분"

        label = f"{score}점 | {travel_time_text} | {congestion} | 병상 {er_beds}개"

        y = bar.get_y() + bar.get_height() / 2

        # 점수가 높은 경우 막대 안쪽에 표시
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
            # 점수가 낮은 경우 막대 바깥쪽에 표시
            ax.text(
                score + 1,
                y,
                label,
                va="center",
                ha="left",
                fontsize=10
            )

    # x축 기준선 표시
    plt.grid(axis="x", linestyle="--", alpha=0.35)

    # 레이아웃 정리
    plt.tight_layout()

    # 그래프 이미지 저장
    file_path = "output/추천_병원_TOP5_그래프.png"
    plt.savefig(file_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"추천 병원 TOP5 그래프 저장 완료: {file_path}")

    return file_path