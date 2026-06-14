from difflib import SequenceMatcher


def normalize_name(name):
    if not name:
        return ""

    name = str(name).replace(" ", "")  # 공백 제거

    remove_words = [
        "의료법인",
        "학교법인",
        "재단법인",
        "사회복지법인",
        "성심의료재단",
        "학교법인고려중앙학원",
        "대학교의과대학부속",
        "대학교병원",
        "대학병원",
        "부속병원",
        "서울특별시",
        "의료원",
        "병원",
        "재단",
        "법인"
    ]

    for word in remove_words:
        name = name.replace(word, "")  # 병원명 비교에 불필요한 단어 제거

    return name


def get_similarity(name1, name2):
    name1 = normalize_name(name1)
    name2 = normalize_name(name2)

    return SequenceMatcher(None, name1, name2).ratio()  # 문자열 유사도 계산


def find_best_match(web_name, api_df):
    best_row = None
    best_score = 0

    for _, row in api_df.iterrows():
        api_name = row.get("병원명", "")
        score = get_similarity(web_name, api_name)

        if score > best_score:
            best_score = score
            best_row = row

    return best_row, best_score


def make_empty_data(web_hospital, match_score):
    return {
        # 웹사이트에서 가져온 기본 정보
        "웹병원명": web_hospital.get("병원명", ""),
        "주소": web_hospital.get("주소", ""),
        "기관구분": web_hospital.get("기관구분", ""),
        "웹원본값": web_hospital.get("원본값", []),

        # API 매칭 정보
        "매칭점수": round(match_score, 2),
        "API병원명": None,

        # API에서 가져올 상세 정보
        "기관ID": None,
        "응급실일반_API": None,
        "응급실소아_API": None,
        "중환자실_API": None,
        "수술실_API": None,
        "CT가능": None,
        "MRI가능": None,
        "인공호흡기": None,
        "업데이트시간": None
    }


def fill_api_data(data, api_row):
    data["API병원명"] = api_row.get("병원명")
    data["기관ID"] = api_row.get("기관ID")
    data["응급실일반_API"] = api_row.get("응급실일반")
    data["응급실소아_API"] = api_row.get("응급실소아")
    data["중환자실_API"] = api_row.get("중환자실")
    data["수술실_API"] = api_row.get("수술실")
    data["CT가능"] = api_row.get("CT가능")
    data["MRI가능"] = api_row.get("MRI가능")
    data["인공호흡기"] = api_row.get("인공호흡기")
    data["업데이트시간"] = api_row.get("업데이트시간")

    return data


def merge_web_and_api_data(web_hospitals, api_df):
    merged = []

    for web_hospital in web_hospitals:
        web_name = web_hospital.get("병원명", "")

        best_row, best_score = find_best_match(web_name, api_df)

        data = make_empty_data(web_hospital, best_score)

        # 점수가 너무 낮으면 다른 병원일 가능성이 있어서 API 정보는 붙이지 않음
        if best_row is not None and best_score >= 0.35:
            data = fill_api_data(data, best_row)

        merged.append(data)

    return merged