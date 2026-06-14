import os

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# 프로젝트 루트 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# RAG 검색용 txt 파일이 들어있는 data 폴더 경로
DATA_DIR = os.path.join(BASE_DIR, "data")

# 모델과 임베딩 결과를 재사용하기 위한 캐시 변수
_embedding_model = None
_cached_chunks = None
_cached_chunk_embeddings = None


# 증상별 기본 응급처치 템플릿
SYMPTOM_GUIDE_TEMPLATES = {
    "호흡곤란": {
        "danger_signs": [
            "숨을 쉬기 매우 힘들어하거나 말하기 어려운 경우",
            "입술이나 얼굴이 파랗게 변하는 경우",
            "의식이 흐려지거나 축 처지는 경우",
            "호흡곤란이 갑자기 심해지는 경우"
        ],
        "actions": [
            "환자를 눕히기보다 상체를 세운 편안한 자세를 유지한다.",
            "목이나 가슴을 조이는 옷을 느슨하게 한다.",
            "환자의 의식과 호흡 상태를 계속 확인한다.",
            "증상이 심하거나 청색증, 의식저하가 있으면 즉시 119에 신고한다."
        ],
        "cautions": [
            "억지로 물이나 음식을 먹이지 않는다.",
            "환자를 무리하게 걷게 하거나 이동시키지 않는다."
        ]
    },
    "심혈관 문제": {
        "danger_signs": [
            "수 분 이상 지속되는 가슴 통증 또는 압박감",
            "가슴 통증이 어깨, 팔, 목, 턱으로 퍼지는 경우",
            "식은땀, 어지러움, 호흡곤란, 오심이 함께 나타나는 경우",
            "의식이 없거나 정상 호흡이 없는 경우"
        ],
        "actions": [
            "환자를 안정시키고 움직임을 최소화한다.",
            "환자가 가장 편안한 자세를 취하도록 돕는다.",
            "호흡 상태를 계속 확인한다.",
            "의식이 없고 정상 호흡이 없으면 즉시 119 신고 후 심폐소생술을 시행한다."
        ],
        "cautions": [
            "증상이 좋아질 것이라고 기다리며 시간을 지체하지 않는다.",
            "환자를 혼자 두지 않는다."
        ]
    },
    "외상": {
        "danger_signs": [
            "출혈이 많거나 압박해도 멈추지 않는 경우",
            "의식저하, 호흡곤란, 심한 통증이 있는 경우",
            "골절, 큰 상처, 교통사고, 추락이 의심되는 경우",
            "머리, 목, 척추 손상이 의심되는 경우"
        ],
        "actions": [
            "환자를 안전한 장소에 두고 불필요하게 움직이지 않는다.",
            "출혈 부위는 깨끗한 천이나 거즈로 직접 압박한다.",
            "골절이 의심되면 다친 부위를 고정하고 움직임을 줄인다.",
            "의식저하, 대량출혈, 호흡곤란이 있으면 즉시 119에 신고한다."
        ],
        "cautions": [
            "박힌 물체를 억지로 제거하지 않는다.",
            "목이나 허리 손상이 의심되면 함부로 일으키지 않는다."
        ]
    },
    "신경계 증상": {
        "danger_signs": [
            "갑자기 한쪽 팔이나 다리에 힘이 빠지는 경우",
            "말이 어눌해지거나 말을 이해하기 어려운 경우",
            "갑작스러운 심한 두통, 구토, 의식저하가 있는 경우",
            "경련이 지속되거나 반복되는 경우"
        ],
        "actions": [
            "환자를 안전한 곳에 눕히고 주변 위험 물건을 치운다.",
            "증상 발생 시간을 확인한다.",
            "의식과 호흡 상태를 계속 관찰한다.",
            "뇌졸중 의심 증상이 있으면 즉시 119에 신고한다."
        ],
        "cautions": [
            "증상이 잠시 좋아졌다고 안심하지 않는다.",
            "경련 중 입에 물건을 넣지 않는다.",
            "억지로 물이나 약을 먹이지 않는다."
        ]
    },
    "소아 응급": {
        "danger_signs": [
            "고열과 함께 경련이 발생한 경우",
            "호흡이 힘들거나 입술이 파래지는 경우",
            "의식이 처지거나 반응이 약한 경우",
            "탈수, 반복 구토, 심한 보챔이 있는 경우"
        ],
        "actions": [
            "아이의 호흡, 의식, 피부색을 확인한다.",
            "경련 중에는 주변 물건을 치워 다치지 않게 한다.",
            "증상 발생 시간과 체온을 기록한다.",
            "호흡곤란, 의식저하, 경련이 지속되면 즉시 119에 신고한다."
        ],
        "cautions": [
            "경련 중 아이의 입에 손가락이나 물건을 넣지 않는다.",
            "억지로 물이나 약을 먹이지 않는다."
        ]
    },
    "화상": {
        "danger_signs": [
            "얼굴, 목, 손, 생식기 부위 화상",
            "넓은 부위의 화상",
            "전기화상 또는 화학물질 화상",
            "호흡곤란이나 기도 화상이 의심되는 경우"
        ],
        "actions": [
            "화상 부위를 흐르는 깨끗한 물로 식힌다.",
            "화상 부위를 깨끗한 천으로 가볍게 덮는다.",
            "넓은 화상이나 얼굴, 목 부위 화상은 즉시 119에 신고한다.",
            "화학물질 화상은 오염된 의복을 제거하고 충분히 씻어낸다."
        ],
        "cautions": [
            "얼음을 직접 대지 않는다.",
            "물집을 터뜨리지 않는다.",
            "된장, 연고, 기름 등을 임의로 바르지 않는다."
        ]
    },
    "중독": {
        "danger_signs": [
            "의식저하 또는 호흡 이상이 있는 경우",
            "약물, 농약, 화학물질, 가스 흡입이 의심되는 경우",
            "구토, 경련, 심한 어지러움이 있는 경우",
            "일산화탄소 중독이 의심되는 경우"
        ],
        "actions": [
            "즉시 119에 신고한다.",
            "가능하면 복용하거나 노출된 물질의 이름, 양, 시간을 확인한다.",
            "가스 중독이 의심되면 안전한 곳으로 이동하고 환기한다.",
            "의식과 호흡 상태를 계속 확인한다."
        ],
        "cautions": [
            "억지로 토하게 하지 않는다.",
            "의식이 없는 환자에게 물이나 음식을 먹이지 않는다.",
            "원인 물질 용기나 약 봉투가 있으면 의료진에게 전달한다."
        ]
    },
    "감염 의심": {
        "danger_signs": [
            "고열과 호흡곤란이 함께 있는 경우",
            "의식 혼미, 청색증, 지속적인 가슴 통증이 있는 경우",
            "감염병 의심 증상과 함께 상태가 빠르게 악화되는 경우",
            "격리가 필요한 감염성 질환이 의심되는 경우"
        ],
        "actions": [
            "마스크를 착용하고 다른 사람과의 접촉을 줄인다.",
            "의료기관 방문 전 증상과 방문 가능 여부를 문의한다.",
            "호흡곤란, 의식저하, 청색증이 있으면 즉시 119에 신고한다.",
            "기침 예절과 손위생을 지킨다."
        ],
        "cautions": [
            "대중교통 이용과 불필요한 외출을 피한다.",
            "증상을 숨기고 의료기관을 방문하지 않는다."
        ]
    }
}


def get_embedding_model():
    global _embedding_model

    # 모델은 처음 한 번만 불러오고 이후에는 재사용
    if _embedding_model is None:
        print("임베딩 모델 로딩 중...")
        _embedding_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
        print("임베딩 모델 로딩 완료")

    return _embedding_model


def read_txt_file(path):
    # txt 파일 내용 읽기
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_documents():
    documents = []

    # data 폴더가 없으면 빈 결과 반환
    if not os.path.exists(DATA_DIR):
        print("data 폴더가 없습니다:", DATA_DIR)
        return documents

    # data 폴더 안의 txt 파일만 읽어오기
    for root, _, files in os.walk(DATA_DIR):
        for filename in files:
            if not filename.lower().endswith(".txt"):
                continue

            path = os.path.join(root, filename)
            text = read_txt_file(path)

            documents.append({
                "filename": filename,
                "text": text
            })

    print(f"txt 문서 로드 완료: {len(documents)}개")
    return documents


def split_text(text, chunk_size=500, overlap=80):
    chunks = []

    # 줄바꿈 형식 통일
    text = text.replace("\r", "\n")

    paragraphs = []

    # 빈 줄은 제외하고 문단만 저장
    for line in text.split("\n"):
        line = line.strip()

        if line:
            paragraphs.append(line)

    current = ""

    # 문서를 일정 크기의 chunk로 분리
    for paragraph in paragraphs:
        if len(current) + len(paragraph) <= chunk_size:
            current += paragraph + "\n"
        else:
            if current.strip():
                chunks.append(current.strip())

            # 이전 내용 일부를 남겨 문맥이 끊기지 않게 처리
            current = current[-overlap:] + "\n" + paragraph + "\n"

    if current.strip():
        chunks.append(current.strip())

    return chunks


def build_chunks(documents):
    chunks = []

    # 문서별로 chunk 생성
    for doc in documents:
        split_chunks = split_text(doc["text"])

        for chunk in split_chunks:
            chunks.append({
                "filename": doc["filename"],
                "text": chunk
            })

    print(f"chunk 생성 완료: {len(chunks)}개")
    return chunks


def get_cached_chunks_and_embeddings():
    global _cached_chunks
    global _cached_chunk_embeddings

    # 이미 계산된 chunk와 임베딩이 있으면 재사용
    if _cached_chunks is not None and _cached_chunk_embeddings is not None:
        return _cached_chunks, _cached_chunk_embeddings

    model = get_embedding_model()

    print("문서 임베딩 생성 중...")

    documents = load_documents()
    chunks = build_chunks(documents)

    # 검색할 문서가 없는 경우
    if not chunks:
        return [], None

    # chunk 텍스트를 임베딩으로 변환
    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts)

    # 다음 검색에서 다시 계산하지 않도록 캐시에 저장
    _cached_chunks = chunks
    _cached_chunk_embeddings = embeddings

    print("문서 임베딩 생성 완료")

    return _cached_chunks, _cached_chunk_embeddings


def retrieve_emergency_guides(symptom, top_k=6):
    chunks, embeddings = get_cached_chunks_and_embeddings()

    # chunk나 임베딩이 없으면 검색 결과 없음
    if not chunks or embeddings is None:
        return []

    model = get_embedding_model()

    # 증상 정보를 검색 문장으로 구성
    query = " ".join([
        symptom.get("name", ""),
        symptom.get("description", ""),
        " ".join(symptom.get("required_beds", [])),
        " ".join(symptom.get("preferred_resources", []))
    ])

    # 검색 문장 임베딩 생성
    query_embedding = model.encode([query])

    # 검색 문장과 문서 chunk 사이의 유사도 계산
    scores = cosine_similarity(query_embedding, embeddings)[0]

    # 유사도가 높은 chunk 순서대로 선택
    top_indices = scores.argsort()[::-1][:top_k]
    results = []

    for idx in top_indices:
        results.append({
            "filename": chunks[idx]["filename"],
            "text": chunks[idx]["text"],
            "similarity": round(float(scores[idx]), 4)
        })

    return results


def get_symptom_template(symptom_name):
    # 등록되지 않은 증상일 때 사용할 기본 템플릿
    default_template = {
        "danger_signs": [
            "의식저하, 호흡곤란, 심한 통증, 대량출혈 등 위급 증상이 있는 경우"
        ],
        "actions": [
            "환자의 의식과 호흡 상태를 확인한다.",
            "증상이 심하거나 악화되면 즉시 119에 신고한다.",
            "환자를 안전한 자세로 유지한다."
        ],
        "cautions": [
            "의식이 없는 환자에게 음식이나 물을 먹이지 않는다.",
            "환자를 불필요하게 움직이지 않는다."
        ]
    }

    # 증상명이 있으면 해당 템플릿 사용, 없으면 기본 템플릿 사용
    return SYMPTOM_GUIDE_TEMPLATES.get(symptom_name, default_template)


def add_bullet_section(lines, title, items):
    # 가이드에 들어갈 제목 추가
    lines.append(title)

    # 항목을 bullet 형태로 추가
    if items:
        for item in items:
            lines.append(f"- {item}")
    else:
        lines.append("- 해당 항목 없음")

    lines.append("")


def clean_rag_text(text):
    # 줄바꿈과 중복 공백 제거
    text = str(text).replace("\n", " ")
    text = " ".join(text.split())

    # 검색 결과가 어색한 표현으로 시작할 경우 제거
    bad_starts = [
        "는다.",
        "다.",
        "후 ",
        "이후 ",
        "그리고 ",
        "또한 ",
        "거나 ",
        "하는 경우,"
    ]

    for bad in bad_starts:
        if text.startswith(bad):
            text = text[len(bad):].strip()

    return text


def cut_by_sentence(text, max_len=180):
    # RAG 검색 결과를 보기 좋게 정리
    text = clean_rag_text(text)

    if len(text) <= max_len:
        return text

    # 너무 긴 내용은 일정 길이까지만 사용
    sliced = text[:max_len]

    # 가능하면 문장 끝에서 자르기
    last_dot = sliced.rfind(".")
    last_question = sliced.rfind("?")
    last_exclamation = sliced.rfind("!")

    cut_pos = max(last_dot, last_question, last_exclamation)

    if cut_pos >= 60:
        return sliced[:cut_pos + 1]

    return sliced + "..."


def make_short_text(text, max_len=180):
    # 최종 출력용 짧은 참고 문장 생성
    return cut_by_sentence(text, max_len=max_len)


def add_rag_section(lines, retrieved_guides, max_count=3):
    lines.append("[4] RAG 검색 자료 기반 참고 내용")

    # 검색 결과가 없는 경우
    if not retrieved_guides:
        lines.append("- 검색된 참고 내용이 없습니다.")
        lines.append("")
        return

    used_files = []
    added_count = 0

    for guide in retrieved_guides:
        filename = guide.get("filename", "알 수 없음")

        # 같은 파일이 여러 번 검색되면 한 번만 표시
        if filename in used_files:
            continue

        used_files.append(filename)

        # 검색된 내용을 짧고 자연스럽게 정리
        text = make_short_text(guide.get("text", ""), max_len=180)

        lines.append(f"- {filename}에서 관련 내용이 검색되었습니다.")
        lines.append(f"  참고 내용: {text}")

        added_count += 1

        # 최대 표시 개수를 넘으면 종료
        if added_count >= max_count:
            break

    lines.append("")


def add_source_section(lines, retrieved_guides):
    lines.append("[6] 참고 문서")

    used_sources = []

    # 참고 문서명이 중복되지 않도록 저장
    for guide in retrieved_guides:
        filename = guide.get("filename", "알 수 없음")

        if filename not in used_sources:
            used_sources.append(filename)

    if used_sources:
        for source in used_sources:
            lines.append(f"- {source}")
    else:
        lines.append("- 관련 문서 없음")


def create_guide_text(symptom, retrieved_guides):
    # 선택된 증상 정보 가져오기
    symptom_name = symptom.get("name", "응급 증상")
    description = symptom.get("description", "")

    # 증상에 맞는 기본 템플릿 가져오기
    template = get_symptom_template(symptom_name)

    # PDF에 들어갈 전체 텍스트 구성
    lines = [
        f"{symptom_name} 응급 대처 가이드",
        "",
        f"증상 설명: {description}",
        "",
        "※ 본 가이드는 전문 응급처치 내용을 정리한 txt 문서를 RAG로 검색하여 만든 참고용 자료입니다.",
        "※ 실제 진단과 치료는 의료진의 판단을 따라야 합니다.",
        "※ 위급한 상황에서는 즉시 119에 신고해야 합니다.",
        ""
    ]

    # 신고가 필요한 상황 추가
    add_bullet_section(
        lines,
        "[1] 즉시 119 신고가 필요한 경우",
        template["danger_signs"]
    )

    # 현장 대처 방법 추가
    add_bullet_section(
        lines,
        "[2] 현장에서 할 수 있는 대처",
        template["actions"]
    )

    # 주의사항 추가
    add_bullet_section(
        lines,
        "[3] 주의해야 할 행동",
        template["cautions"]
    )

    # RAG 검색 결과 추가
    add_rag_section(lines, retrieved_guides)

    # 병원 이동 시 전달할 정보 추가
    lines.append("[5] 병원 이동 시 의료진에게 전달할 정보")
    lines.append("- 증상이 시작된 시각")
    lines.append("- 현재 가장 심한 증상")
    lines.append("- 의식 및 호흡 상태")
    lines.append("- 기존 질환")
    lines.append("- 복용 중인 약물")
    lines.append("- 사고 또는 증상 발생 상황")
    lines.append("")

    # 참고 문서 목록 추가
    add_source_section(lines, retrieved_guides)

    # 리스트를 하나의 문자열로 합쳐 반환
    return "\n".join(lines)