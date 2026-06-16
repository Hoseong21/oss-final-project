# Sce.note — AI 향수 추천 서비스

> Streamlit + FastAPI + Docker + AWS EC2 기반 향수 추천 웹 애플리케이션

| 항목 | 내용 |
| --- | --- |
| 제출자 | 송호성 |
| 학번 | 2021603038 |
| 소속 | 광운대학교 수학과 (정보융합학부 복수전공) |
| 과제명 | 오픈소스소프트웨어실습 기말고사 대체 과제 |

## 프로젝트 소개

Sce.note는 사용자가 선호하는 향수 노트(Top/Middle/Base)나 계절을 선택하면, 코사인 유사도 기반으로 가장 어울리는 향수를 추천해주는 웹 애플리케이션입니다.

Streamlit이 사용자 입력을 받아 FastAPI 백엔드에 HTTP 요청을 보내고, FastAPI는 24,063개 향수 데이터셋(Kaggle Fragrantica)에서 코사인 유사도를 계산해 JSON 형태로 추천 결과를 반환합니다. Streamlit은 추천 결과를 직접 계산하지 않고, FastAPI의 응답을 받아 화면에 표시하는 역할만 수행합니다.

프론트엔드와 백엔드를 각각 Docker 컨테이너로 분리하고, Docker Compose로 통합 관리하며, AWS EC2 환경에서 실행됩니다.

## 주요 기능

| 기능 | 설명 |
| --- | --- |
| 학번 기반 로그인 | 학번 10자리 + 이름으로 사용자를 식별하며, 신규 사용자는 자동 등록됩니다 |
| 노트 기반 추천 | Top/Middle/Base Note 그룹과 세부 노트, 계절, 성별을 선택해 맞춤 향수를 추천받습니다 |
| 계절 기반 추천 | 노트 선택 없이 계절에 가장 어울리는 향수를 자동으로 추천받습니다 |
| 추천 히스토리 | 사용자별 추천 기록을 저장하고, 다시 확인하거나 삭제할 수 있습니다 |
| Streamlit ↔ FastAPI 연동 | 모든 추천 로직은 FastAPI에서 처리되며, Streamlit은 결과만 받아 표시합니다 |

## 전체 구조

```
사용자 입력 → Streamlit → FastAPI 호출(HTTP POST) → 추천 결과 반환(JSON) → Streamlit 화면 표시
```

* **Streamlit**: 사용자 입력 받기 / 결과 출력
* **FastAPI**: 입력값을 받아 코사인 유사도 기반 추천 결과 생성 후 JSON 반환
* **Docker**: Streamlit과 FastAPI를 각각 별도 컨테이너로 분리하여 실행
* **AWS EC2**: 실제 실행 환경 (Ubuntu 24.04, t3.micro)

## 실행 방법

### 요구 사항

* Docker, Docker Compose
* (전처리 시) Python 3.9+

### Docker로 실행 (권장)

```bash
# 1. 저장소 클론
git clone https://github.com/Hoseong21/oss-final-project.git
cd oss-final-project

# 2. Kaggle Fragrantica 데이터셋(fra_cleaned.csv)을 backend/data/ 에 위치
#    (df_notes.pkl, note_columns.pkl은 용량 문제로 .gitignore 처리되어 있어
#     아래 전처리 과정을 통해 직접 생성해야 합니다)

# 3. 전처리 실행 (df_notes.pkl, note_columns.pkl 생성)
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python preprocessing.py
cd ..

# 4. Docker Compose 빌드 및 실행
docker compose up -d --build

# 5. 컨테이너 확인
docker ps
```

실행 후 브라우저에서 `http://localhost:8501` 접속.

### 로컬 개발 환경 (Docker 없이)

```bash
# 터미널 1 - 백엔드
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 터미널 2 - 프론트엔드
cd frontend
streamlit run app.py
```

### AWS EC2 배포 시 추가 설정

```bash
# Swap 메모리 설정 (t3.micro 메모리 부족 방지)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

EC2 보안 그룹 인바운드 규칙에 **8000번(FastAPI), 8501번(Streamlit)** 포트를 0.0.0.0/0으로 열어야 외부에서 접속 가능합니다.

## 추천 알고리즘

1. **데이터 전처리**: Kaggle Fragrantica 데이터셋의 향수별 Top/Middle/Base 노트를 정규화(지역명·접미어 제거, 단수화)하고, 1,402개 고유 노트에 대해 One-hot Encoding을 적용합니다
2. **메인 어코드 결측치 보완**: 노트 기반으로 카테고리를 추론하여 누락된 mainaccord 값을 보완합니다
3. **계절 벡터 생성**: 노트별 계절 적합도(`all_notes.json`)를 Top 0.5 / Middle 0.3 / Base 0.2 가중치로 결합한 뒤 Softmax로 정규화합니다
4. **피처 벡터**: 노트 원-핫 벡터(1,402차원) + 계절 벡터(4차원)를 결합하여 1,406차원 피처 벡터를 생성하고 전처리 단계에서 미리 계산해 캐싱합니다
5. **사용자 벡터 생성**: 선택한 Top/Middle/Base 노트에 차등 가중치(Top 1.2 / Middle 0.8 / Base 0.6)를 부여하여 사용자 취향 벡터를 만듭니다
6. **추천**: 사용자 벡터와 전체 향수 피처 벡터 간 코사인 유사도(Cosine Similarity)를 계산하여 상위 4개(노트 기반) 또는 3개(계절 기반)를 추천합니다

## API 엔드포인트 (FastAPI)

| Method | Endpoint | 설명 |
| --- | --- | --- |
| POST | `/login` | 학번/이름 기반 로그인·신규 등록 |
| POST | `/recommend` | 노트 기반 추천 |
| POST | `/recommend/season` | 계절 기반 추천 |
| POST | `/history` | 추천 기록 저장 |
| GET | `/history/{student_id}` | 추천 기록 조회 |
| DELETE | `/history/{student_id}/{idx}` | 추천 기록 삭제 |
| GET | `/` | API 루트 (엔드포인트 목록 확인) |

API 문서는 `http://localhost:8000/docs` (EC2 배포 시 `http://{EC2 주소}:8000/docs`)에서 Swagger UI로 확인할 수 있으며, 각 엔드포인트를 직접 호출해 JSON 응답을 확인할 수 있습니다.

## 캐싱 적용

전처리 단계(`recommender.py` 모듈 로드 시)에서 `df_notes.pkl`을 1회만 로드하고, 전체 향수의 피처 벡터를 미리 `FEATURE_MATRIX`로 변환해 메모리에 캐싱합니다. 추천 요청이 들어올 때마다 pkl을 다시 읽거나 벡터를 재계산하지 않고, 캐싱된 행렬을 재사용하여 코사인 유사도만 계산하므로 응답 속도가 향상됩니다.

또한 `NOTE_COLUMNS`를 리스트가 아닌 딕셔너리(`NOTE_COLUMNS_IDX`)로 변환해 두어, 노트 인덱스 조회를 O(1)로 처리합니다.

## 파일 구조

```
oss-final-project/
├── docker-compose.yml      # 컨테이너 통합 실행 설정
├── README.md               # 프로젝트 설명 (현재 파일)
├── backend/
│   ├── main.py               # FastAPI 엔드포인트
│   ├── recommender.py        # 추천 로직 (코사인 유사도, 캐싱)
│   ├── preprocessing.py      # 데이터 전처리 스크립트
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .dockerignore
│   └── data/
│       ├── fra_cleaned.csv     # Kaggle Fragrantica 데이터셋
│       ├── all_notes.json      # 노트별 계절 매핑
│       ├── df_notes.pkl        # 전처리 결과 (gitignore 처리, 직접 생성 필요)
│       ├── note_columns.pkl    # 노트 컬럼 목록 (gitignore 처리, 직접 생성 필요)
│       ├── users.json          # 사용자 정보 (gitignore 처리)
│       └── history.json        # 추천 기록 (gitignore 처리)
└── frontend/
    ├── app.py                 # Streamlit 메인 실행 파일
    ├── requirements.txt
    ├── Dockerfile
    └── .dockerignore
```

## 기술 스택

| 분류 | 기술 |
| --- | --- |
| 언어 | Python 3.9 |
| 프론트엔드 | Streamlit 1.50.0 |
| 백엔드 | FastAPI, Uvicorn |
| 데이터 처리 | Pandas, NumPy, scikit-learn (Cosine Similarity, MultiLabelBinarizer) |
| 컨테이너 | Docker, Docker Compose |
| 배포 환경 | AWS EC2 (Ubuntu 24.04, t3.micro) |
| 데이터셋 | Kaggle Fragrantica Fragrance Dataset (`fra_cleaned.csv`) |

## 데이터셋 출처

본 프로젝트는 Kaggle에 공개된 Fragrantica 향수 데이터셋(`fra_cleaned.csv`, 24,063개 향수)을 사용했습니다. 노트별 계절 매핑(`all_notes.json`)은 향수 업계에서 통용되는 노트 계열별 계절 특성을 참고하여 별도로 구성했습니다.