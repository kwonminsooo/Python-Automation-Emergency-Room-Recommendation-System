import re


def parse_available_count(value):
    # 값이 없으면 0으로 처리
    if value is None:
        return 0

    value = str(value).strip()

    # 빈 값 또는 '-'는 사용 가능한 병상이 없는 것으로 처리
    if value == "-" or value == "":
        return 0

    # '7/22', '-1*/24' 같은 형식에서 앞쪽 숫자 추출
    if "/" in value:
        left = value.split("/")[0]
        numbers = re.findall(r"-?\d+", left)

        if numbers:
            return int(numbers[0])

    # 일반 문자열에서 숫자 추출
    numbers = re.findall(r"-?\d+", value)

    if numbers:
        return int(numbers[0])

    # 숫자는 없지만 '가능'이라고 적힌 경우 1점 처리
    if "가능" in value:
        return 1

    return 0


def get_web_bed_info(web_values):
    # E-GEN에서 가져온 원본 병상 정보를 점수 계산용 dict로 변환
    return {
        "응급실일반_혼잡도": web_values[0] if len(web_values) > 0 else "",
        "응급실일반": parse_available_count(web_values[1]) if len(web_values) > 1 else 0,

        "응급실소아_혼잡도": web_values[2] if len(web_values) > 2 else "",
        "응급실소아": parse_available_count(web_values[3]) if len(web_values) > 3 else 0,

        "분만실": parse_available_count(web_values[4]) if len(web_values) > 4 else 0,

        "음압격리_혼잡도": web_values[5] if len(web_values) > 5 else "",
        "음압격리": parse_available_count(web_values[6]) if len(web_values) > 6 else 0,

        "일반격리_혼잡도": web_values[7] if len(web_values) > 7 else "",
        "일반격리": parse_available_count(web_values[8]) if len(web_values) > 8 else 0,

        "코호트격리": parse_available_count(web_values[9]) if len(web_values) > 9 else 0,
    }


def congestion_score(congestion):
    # 응급실 혼잡도에 따라 점수 부여
    if congestion == "원활":
        return 20
    if congestion == "보통":
        return 10
    if congestion == "혼잡":
        return 0

    # 정보가 없을 때는 최소 점수 부여
    return 5


def yes_no_score(value, weight):
    # CT, MRI, 인공호흡기 등 Y/N 항목 점수 계산
    if value is None:
        return 0

    value = str(value).strip().upper()

    if value == "Y":
        return weight

    return 0


def travel_time_score(hospital):
    # 예상 이동시간이 짧을수록 가산점 부여
    travel_time = hospital.get("예상이동시간_분")

    if travel_time is None:
        return 0

    try:
        travel_time = float(travel_time)
    except Exception:
        return 0

    if travel_time <= 10:
        return 10
    if travel_time <= 20:
        return 7
    if travel_time <= 30:
        return 3

    return -5


def normalize_score(score):
    # 추천점수를 0~100점 범위로 제한
    if score < 0:
        return 0

    if score > 100:
        return 100

    return round(score, 1)


def calculate_score(hospital, symptom):
    score = 0
    reasons = []

    # 증상별 가중치와 필요 자원 정보 가져오기
    weights = symptom.get("weights", {})
    required_beds = symptom.get("required_beds", [])
    preferred_resources = symptom.get("preferred_resources", [])

    # 웹에서 수집한 병상 정보 정리
    web_values = hospital.get("웹원본값", [])
    web_info = get_web_bed_info(web_values)

    # 응급실 일반 병상 점수 계산
    if "응급실일반" in required_beds or "응급실일반" in weights:
        bed_count = web_info["응급실일반"]

        if bed_count > 0:
            add = min(bed_count * 2, weights.get("응급실일반", 30))
            score += add
            reasons.append(f"응급실 일반 가용 병상 {bed_count}개")
        else:
            score -= 20
            reasons.append("응급실 일반 가용 병상 부족")

    # 소아 응급 병상 점수 계산
    if "응급실소아" in required_beds or "응급실소아" in weights:
        bed_count = web_info["응급실소아"]

        if bed_count > 0:
            add = min(bed_count * 5, weights.get("응급실소아", 40))
            score += add
            reasons.append(f"소아 응급 병상 {bed_count}개")
        else:
            score -= 30
            reasons.append("소아 응급 병상 부족")

    # 중환자실 점수 계산
    if "중환자실" in preferred_resources or "중환자실" in weights:
        icu_count = parse_available_count(hospital.get("중환자실_API"))

        if icu_count > 0:
            add = min(icu_count * 3, weights.get("중환자실", 25))
            score += add
            reasons.append(f"중환자실 가용 {icu_count}개")
        else:
            reasons.append("중환자실 정보 부족 또는 가용 병상 없음")

    # 수술실 점수 계산
    if "수술실" in preferred_resources or "수술실" in weights:
        surgery_count = parse_available_count(hospital.get("수술실_API"))

        if surgery_count > 0:
            add = min(surgery_count * 5, weights.get("수술실", 20))
            score += add
            reasons.append(f"수술실 가용 {surgery_count}개")
        else:
            reasons.append("수술실 정보 부족 또는 가용 병상 없음")

    # CT 가능 여부 점수 계산
    if "CT가능" in preferred_resources or "CT가능" in weights:
        add = yes_no_score(hospital.get("CT가능"), weights.get("CT가능", 15))
        score += add

        if add > 0:
            reasons.append("CT 가능")
        else:
            reasons.append("CT 정보 부족 또는 사용 불가")

    # MRI 가능 여부 점수 계산
    if "MRI가능" in preferred_resources or "MRI가능" in weights:
        add = yes_no_score(hospital.get("MRI가능"), weights.get("MRI가능", 15))
        score += add

        if add > 0:
            reasons.append("MRI 가능")
        else:
            reasons.append("MRI 정보 부족 또는 사용 불가")

    # 인공호흡기 가능 여부 점수 계산
    if "인공호흡기" in preferred_resources or "인공호흡기" in weights:
        add = yes_no_score(hospital.get("인공호흡기"), weights.get("인공호흡기", 25))
        score += add

        if add > 0:
            reasons.append("인공호흡기 가능")
        else:
            reasons.append("인공호흡기 정보 부족 또는 사용 불가")

    # 음압격리 병상 점수 계산
    if "음압격리" in preferred_resources or "음압격리" in weights:
        count = web_info["음압격리"]

        if count > 0:
            add = min(count * 5, weights.get("음압격리", 20))
            score += add
            reasons.append(f"음압격리 병상 {count}개")
        else:
            reasons.append("음압격리 병상 정보 부족 또는 가용 병상 없음")

    # 일반격리 병상 점수 계산
    if "일반격리" in preferred_resources or "일반격리" in weights:
        count = web_info["일반격리"]

        if count > 0:
            add = min(count * 3, weights.get("일반격리", 15))
            score += add
            reasons.append(f"일반격리 병상 {count}개")
        else:
            reasons.append("일반격리 병상 정보 부족 또는 가용 병상 없음")

    # 코호트격리 병상 점수 계산
    if "코호트격리" in preferred_resources or "코호트격리" in weights:
        count = web_info["코호트격리"]

        if count > 0:
            add = min(count * 3, weights.get("코호트격리", 15))
            score += add
            reasons.append(f"코호트격리 병상 {count}개")
        else:
            reasons.append("코호트격리 병상 정보 부족 또는 가용 병상 없음")

    # 응급실 혼잡도 점수 반영
    congestion = web_info["응급실일반_혼잡도"]
    score += congestion_score(congestion)
    reasons.append(f"응급실 혼잡도: {congestion}")

    # 병원 기관구분에 따른 가산점
    institution = hospital.get("기관구분")

    if institution == "권역":
        score += 10
        reasons.append("권역응급의료센터")
    elif institution == "센터":
        score += 5
        reasons.append("지역응급의료센터")

    # 예상 이동시간 점수 반영
    time_score = travel_time_score(hospital)
    score += time_score

    travel_time = hospital.get("예상이동시간_분")
    if travel_time is not None:
        reasons.append(f"예상 이동시간 {travel_time}분")

    # API 병원명 매칭 신뢰도 확인
    match_score = hospital.get("매칭점수", 0)

    try:
        match_score = float(match_score)
    except Exception:
        match_score = 0

    if match_score < 0.45:
        score -= 10
        reasons.append("API 병원명 매칭 신뢰도 낮음")

    # 최종 점수와 추천 사유 저장
    final_score = normalize_score(score)

    hospital["추천점수"] = final_score
    hospital["추천사유"] = ", ".join(reasons)
    hospital["정리된웹병상정보"] = web_info

    return hospital


def score_hospitals(merged_hospitals, symptom):
    scored = []

    # 병원별 추천 점수 계산
    for hospital in merged_hospitals:
        scored.append(calculate_score(hospital, symptom))

    # 추천점수 우선, 점수가 같으면 예상 이동시간이 짧은 병원 우선
    scored.sort(
        key=lambda x: (
            x.get("추천점수", 0),
            -float(x.get("예상이동시간_분") or 9999)
        ),
        reverse=True
    )

    # 정렬된 순서대로 추천순위 부여
    for idx, hospital in enumerate(scored, start=1):
        hospital["추천순위"] = idx

    return scored