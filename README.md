##프로젝트 소개

본 프로젝트는 위치와 증상 정보를 기반으로 주변 응급실을 추천하고, 응급처치 가이드를 함께 제공하는 Python 자동화 시스템입니다.
응급 상황에서는 환자의 상태에 맞는 병원을 빠르게 찾는 것이 중요합니다. 그러나 실제 상황에서는 병원별 병상 여부, 혼잡도, 의료 장비 보유 여부, 이동 거리 등을 직접 확인해야 하므로 시간이 오래 걸릴 수 있습니다. 본 프로젝트는 이러한 문제를 줄이기 위해 웹 자동화, 공공데이터 API, 카카오 API, RAG 기반 응급처치 자료 검색, Excel/PDF/그래프 자동 생성 기능을 하나의 흐름으로 연결하였습니다.
사용자는 환자의 증상과 현재 주소를 입력하고, 내 손안의 응급실 사이트에서 위치 정보 접근을 허용한 뒤 추천 실행 버튼을 누르면 됩니다. 프로그램은 주변 응급실 정보를 수집하고, 병상 및 의료자원 정보와 거리 정보를 결합하여 추천 점수를 계산합니다. 이후 추천 병원 TOP 5, 지도, 그래프, Excel 보고서, 응급처치 PDF를 제공합니다.

##주요 기능
환자 증상 입력 및 응급 증상 카테고리 분류
RAG 기반 응급처치 가이드 PDF 생성
Selenium을 이용한 내 손안의 응급실 웹사이트 자동 접속
공공데이터 API를 이용한 병상 및 의료자원 정보 수집
카카오 주소 검색 API를 이용한 주소 좌표 변환
카카오 길찾기 API를 이용한 실제 이동거리 및 예상 이동시간 계산
증상별 가중치 기반 응급실 추천 점수 계산
추천 병원 TOP 5 카드, 그래프, 지도 시각화
Excel 보고서 자동 생성
PDF 가이드, Excel 보고서, 추천 그래프 다운로드
이메일을 통한 결과 파일 전송

##사용 방법
Streamlit 화면에서 환자의 증상을 입력하거나 직접 선택합니다.
선택된 증상을 기준으로 응급처치 가이드 PDF를 생성합니다.
환자의 현재 주소를 입력합니다.
내 손안의 응급실 사이트를 열고 위치 정보 접근을 허용합니다.
응급실 목록이 화면에 표시되면 추천 실행 버튼을 누릅니다.
추천 병원 TOP 5, 지도, 그래프, 전체 추천 결과를 확인합니다.
Excel 보고서, 응급처치 PDF, 추천 그래프를 다운로드하거나 이메일로 전송합니다.

###사용 기술
구분	기술
언어	Python
웹 UI	Streamlit
웹 자동화	Selenium, webdriver-manager
데이터 처리	pandas
API 요청	requests
XML 파싱	xml.etree.ElementTree
Excel 생성	openpyxl
그래프 시각화	matplotlib
지도 시각화	folium, streamlit-folium
RAG 검색	sentence-transformers, scikit-learn
PDF 생성	PyMuPDF
이메일 전송	smtplib, email.mime
환경 변수 관리	python-dotenv

###프로젝트 구조

프로젝트 폴더/
├─ app.py
├─ symptoms.json
├─ requirements.txt
├─ README.md
├─ .gitignore
├─ data/
│  ├─ burn/
│  ├─ cardiovascular/
│  ├─ common/
│  ├─ infection/
│  ├─ neurological/
│  ├─ pediatric_emergency/
│  ├─ poisoning/
│  ├─ respiratory_distress/
│  └─ trauma/
├─ output/
│  └─ .gitkeep
└─ src/
   ├─ api_client.py
   ├─ distance.py
   ├─ email_sender.py
   ├─ excel_writer.py
   ├─ matcher.py
   ├─ pdf_writer.py
   ├─ pipeline.py
   ├─ rag_guide.py
   ├─ scorer.py
   ├─ scraper.py
   └─ visualizer.py



###추천 점수 계산 기준

추천 점수는 단순 거리만 기준으로 계산하지 않고, 환자 증상에 따라 필요한 병상과 의료자원을 다르게 반영합니다.
예를 들어 호흡곤란 환자의 경우 중환자실과 인공호흡기 정보를 중요하게 고려하고, 외상 환자의 경우 수술실과 CT 가능 여부를 반영합니다. 또한 응급실 일반 병상 수, 혼잡도, 실제 이동시간, 기관구분 등을 함께 고려하여 최종 추천 점수를 계산합니다.
최종 점수는 0점에서 100점 사이로 정규화하여 사용자에게 보여줍니다.

###화면구성

<img width="940" height="415" alt="image" src="https://github.com/user-attachments/assets/a79f5072-6fe1-47a4-a3d1-83a2c0284c9a" />
<img width="940" height="243" alt="image" src="https://github.com/user-attachments/assets/0d89979e-2d61-411f-b426-61faa9264b00" />
<img width="940" height="242" alt="image" src="https://github.com/user-attachments/assets/67fcd868-4cdb-41b7-95fa-84ef9ecf47ad" />
<img width="940" height="212" alt="image" src="https://github.com/user-attachments/assets/b3ae51ff-4670-4dec-a7a9-bb3628a7345b" />

###결과 파일

프로그램 실행 후 output 폴더에 다음과 같은 결과 파일이 생성됩니다.

응급실 추천 결과 Excel 보고서
<img width="940" height="306" alt="image" src="https://github.com/user-attachments/assets/c3c6c475-e3c7-4b02-a162-1dfd69d9376a" />

응급처치 가이드 PDF
<img width="378" height="599" alt="image" src="https://github.com/user-attachments/assets/7de42a90-6546-45f9-9f21-2932e9506cdd" />

추천 병원 TOP 5 그래프 이미지
<img width="940" height="302" alt="image" src="https://github.com/user-attachments/assets/df93593b-2da4-4cae-b5d2-b3105b83321b" />

환자의 현재 위치와 병원 위치를 나타낸 지도
<img width="940" height="467" alt="image" src="https://github.com/user-attachments/assets/efa3fd94-94f6-4f80-b767-414a87bbd198" />


####주의 사항
본 시스템은 응급 상황에서 참고할 수 있는 정보를 빠르게 제공하기 위한 자동화 프로그램입니다. 실제 병원 수용 가능 여부는 병원 상황에 따라 실시간으로 달라질 수 있으며, 응급 상황에서는 반드시 119 또는 의료진의 안내를 따라야 합니다.
