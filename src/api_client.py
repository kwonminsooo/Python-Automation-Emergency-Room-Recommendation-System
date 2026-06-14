import os
import requests
import xml.etree.ElementTree as ET
import pandas as pd

from dotenv import load_dotenv


# .env 파일 불러오기
load_dotenv()

# 공공데이터포털에서 발급받은 서비스 키 가져오기
SERVICE_KEY = os.getenv("PUBLIC_API_SERVICE_KEY")

# 응급실 실시간 가용 병상 정보 API 주소
BASE_URL = "http://apis.data.go.kr/B552657/ErmctInfoInqireService/getEmrrmRltmUsefulSckbdInfoInqire"


def get_er_bed_dataframe(stage1="서울특별시"):
    # API 요청 파라미터 설정
    params = {
        "serviceKey": SERVICE_KEY,
        "pageNo": "1",
        "numOfRows": "100",
        "STAGE1": stage1
    }

    # 공공데이터 API 요청
    response = requests.get(BASE_URL, params=params)

    # XML 응답 데이터 파싱
    root = ET.fromstring(response.text)

    rows = []

    # XML item 태그마다 병원 정보 추출
    for item in root.findall(".//item"):
        rows.append({
            "병원명": item.findtext("dutyName"),
            "기관ID": item.findtext("hpid"),
            "응급실일반": item.findtext("hvec"),
            "응급실소아": item.findtext("hvgc"),
            "중환자실": item.findtext("hvicc"),
            "수술실": item.findtext("hvoc"),
            "CT가능": item.findtext("hvctayn"),
            "MRI가능": item.findtext("hvmriayn"),
            "인공호흡기": item.findtext("hvventiayn"),
            "업데이트시간": item.findtext("hvidate")
        })

    # 병원 정보를 DataFrame으로 변환
    df = pd.DataFrame(rows)
    return df


if __name__ == "__main__":
    # 단독 실행 시 API 결과 확인용
    df = get_er_bed_dataframe()

    print(df.head())
    print("총 병원 수:", len(df))
    print(df.columns.tolist())