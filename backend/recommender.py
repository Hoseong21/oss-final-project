import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


# 1. 데이터 로드
def load_data():
    """데이터 로드 with 에러 처리"""
    try:
        with open("data/df_notes.pkl", "rb") as f:
            df_notes = pickle.load(f)
        with open("data/note_columns.pkl", "rb") as f:
            NOTE_COLUMNS = pickle.load(f)
        return df_notes, NOTE_COLUMNS
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Data file not found: {e}")
    except Exception as e:
        raise Exception(f"Error loading data: {e}")


df_notes, NOTE_COLUMNS = load_data()

# NOTE_COLUMNS를 딕셔너리로 변환 (O(1) 조회)
NOTE_COLUMNS_IDX = {note: idx for idx, note in enumerate(NOTE_COLUMNS)}

# feature_matrix 캐싱
FEATURE_MATRIX = np.vstack(df_notes["feature_vector"].values)


# 2. 노트 정규화
def normalize_note_name(note):
    """입력 노트를 소문자 + strip으로 정규화"""
    if not isinstance(note, str):
        return None
    return note.strip().lower()


# 3. 계절 인덱스 매핑
SEASON_INDEX = {
    "Spring": 0,
    "Summer": 1,
    "Fall": 2,
    "Winter": 3
}


# 4. season → 4차원 벡터 변환
def season_to_vector(season_name):
    """season_name → 4차원 np.zeros 벡터"""
    vec = np.zeros(4)
    idx = SEASON_INDEX.get(season_name)
    if idx is not None:
        vec[idx] = 1.0
    return vec


# 5. 사용자 벡터 생성
def build_user_vector_v2(
    top_note=None,
    mid_note=None,
    base_note=None,
    season=None,
    w_top=1.0,
    w_mid=0.8,
    w_base=0.6,
    w_notes=0.7,
    w_season=0.3,
):
    """
    사용자 벡터 생성
    파라미터: top_note, mid_note, base_note, season, w_top=1.0, w_mid=0.8, w_base=0.6, w_notes=0.7, w_season=0.3
    벡터 크기: len(NOTE_COLUMNS) + 4
    """
    vec = np.zeros(len(NOTE_COLUMNS) + 4)
    note_vec = np.zeros(len(NOTE_COLUMNS))

    # 정규화
    top_note_norm = normalize_note_name(top_note)
    mid_note_norm = normalize_note_name(mid_note)
    base_note_norm = normalize_note_name(base_note)

    # NOTE_COLUMNS_IDX 딕셔너리로 O(1) 조회
    if top_note_norm and top_note_norm in NOTE_COLUMNS_IDX:
        idx = NOTE_COLUMNS_IDX[top_note_norm]
        note_vec[idx] = w_top

    if mid_note_norm and mid_note_norm in NOTE_COLUMNS_IDX:
        idx = NOTE_COLUMNS_IDX[mid_note_norm]
        note_vec[idx] = max(note_vec[idx], w_mid)

    if base_note_norm and base_note_norm in NOTE_COLUMNS_IDX:
        idx = NOTE_COLUMNS_IDX[base_note_norm]
        note_vec[idx] = max(note_vec[idx], w_base)

    # note part 적용
    vec[:len(NOTE_COLUMNS)] = w_notes * note_vec

    # season part 적용
    if season:
        vec[-4:] = w_season * season_to_vector(season)

    return vec


# 6. NOTE GROUPS
NOTE_GROUPS = {
    "Citrus": [
        "bergamot", "lemon", "orange", "mandarin",
        "grapefruit", "yuzu", "lime", "neroli", "petitgrain"
    ],
    "Floral": [
        "jasmine", "rose", "peony", "violet",
        "orange blossom", "lily of the valley", "magnolia",
        "iris", "tuberose", "gardenia"
    ],
    "Fruity": [
        "apple", "pear", "peach", "blackcurrant",
        "raspberry", "strawberry", "pineapple"
    ],
    "Green": [
        "green tea", "mint", "basil", "sage",
        "rosemary", "mate", "fig"
    ],
    "Woody": [
        "cedar", "sandalwood", "vetiver", "patchouli",
        "guaiac", "oakmoss", "cashmere", "cypress"
    ],
    "Spicy": [
        "pink pepper", "black pepper", "cardamom",
        "cinnamon", "clove", "nutmeg"
    ],
    "Sweet": [
        "vanilla", "tonka bean", "caramel", "honey",
        "praline", "chocolate", "coconut", "cotton candy"
    ],
    "Musk": ["musk", "white musk", "ambrette"],
    "Amber": ["amber", "benzoin", "labdanum", "frankincense", "myrrh", "olibanum"],
    "Fresh": ["sea salt", "aquatic notes", "aldehydes", "ozonic"]
}

TOP_NOTE_GROUPS = ["Citrus", "Fruity", "Green", "Floral", "Spicy", "Fresh"]
MID_NOTE_GROUPS = ["Floral", "Woody", "Spicy", "Green", "Fruity"]
BASE_NOTE_GROUPS = ["Woody", "Musk", "Amber", "Sweet"]


def get_notes_by_group(group_name):
    """특정 그룹의 노트 리스트 반환"""
    return NOTE_GROUPS.get(group_name, [])


# 7. 추천 엔진
def recommend_perfumes(user_vector, gender=None, top_n=4):
    """
    FEATURE_MATRIX 캐싱된 것 사용 (np.vstack 반복 호출 금지)
    df_notes.copy()로 복사본 사용
    """
    # 1) similarity 계산 (캐싱된 FEATURE_MATRIX 사용)
    sims = cosine_similarity(FEATURE_MATRIX, user_vector.reshape(1, -1)).flatten()

    # 2) df_notes 복사본에 similarity 추가
    df_temp = df_notes.copy()
    df_temp["similarity"] = sims

    # 3) gender 필터링
    if gender:
        gender = gender.lower().strip()
        df_temp = df_temp[df_temp["Gender"].str.lower() == gender]

    # 4) 정렬 후 상위 top_n 반환
    result = df_temp.sort_values("similarity", ascending=False).head(top_n)
    return result.reset_index(drop=True)


# 8. 추천 결과 포맷팅
def format_recommendation_output(result_df):
    """
    top1: name, brand, url, gender, top_notes, middle_notes, base_notes, accord, similarity, image_url
    others: name, brand, similarity, image_url (2~4위)
    """

    def clean_name_local(text):
        return text.replace("-", " ").strip().title() if isinstance(text, str) else text

    top1 = result_df.iloc[0]

    top1_detail = {
        "name": clean_name_local(top1["Perfume"]),
        "brand": clean_name_local(top1["Brand"]),
        "url": top1["url"],
        "gender": top1["Gender"],
        "top_notes": top1["Top"],
        "middle_notes": top1["Middle"],
        "base_notes": top1["Base"],
        "accord": top1.get("mainaccord1", None),
        "similarity": float(top1["similarity"]),
        "image_url": top1.get("image_url")
    }

    # 2~4위
    others = []
    for idx in range(1, len(result_df)):
        row = result_df.iloc[idx]
        others.append({
            "name": clean_name_local(row["Perfume"]),
            "brand": clean_name_local(row["Brand"]),
            "similarity": float(row["similarity"]),
            "image_url": row.get("image_url")
        })

    return top1_detail, others


# 9. End-to-End 추천 패키지
def get_recommendation_result(user_vector, gender=None):
    result_df = recommend_perfumes(user_vector, gender=gender, top_n=4)
    top1, others = format_recommendation_output(result_df)
    return {
        "top1": top1,
        "recommended": others
    }


# 10. 계절 기반 추천
def recommend_by_season(season, gender=None, top_n=3):
    """
    season, gender, top_n=3
    Season_scaled 컬럼에서 해당 계절 인덱스 점수 추출
    gender 필터링 후 상위 top_n 반환
    """
    # season → index
    idx = SEASON_INDEX.get(season)
    if idx is None:
        raise ValueError("Season must be Spring/Summer/Fall/Winter")

    df_temp = df_notes.copy()

    # 각 향수의 해당 계절 점수
    df_temp["season_score"] = df_temp["Season_scaled"].apply(lambda v: float(v[idx]))

    # 성별 필터
    if gender:
        gender = gender.lower().strip()
        df_temp = df_temp[df_temp["Gender"].str.lower() == gender]

    # 상위 top_n 개 반환
    result = df_temp.sort_values("season_score", ascending=False).head(top_n)
    return result.reset_index(drop=True)


# 11. 계절 추천 결과 포맷팅
def format_season_recommendation(df):
    """
    top1: name, brand, gender, url, score, top_notes, middle_notes, base_notes, image_url
    others: name, brand, score, image_url
    """

    def clean_name_local(text):
        return text.replace("-", " ").strip().title() if isinstance(text, str) else text

    top1 = df.iloc[0]

    top1_detail = {
        "name": clean_name_local(top1["Perfume"]),
        "brand": clean_name_local(top1["Brand"]),
        "gender": top1["Gender"],
        "url": top1["url"],
        "score": float(top1["season_score"]),
        "top_notes": top1["Top"],
        "middle_notes": top1["Middle"],
        "base_notes": top1["Base"],
        "image_url": top1.get("image_url")
    }

    others = []
    for i in range(1, len(df)):
        row = df.iloc[i]
        others.append({
            "name": clean_name_local(row["Perfume"]),
            "brand": clean_name_local(row["Brand"]),
            "score": float(row["season_score"]),
            "image_url": row.get("image_url")
        })

    return top1_detail, others


# 12. 계절 추천 최종 패키지
def get_season_recommendation(season, gender=None):
    """
    season, gender 받아서 recommend_by_season + format_season_recommendation 호출
    {"top1": ..., "recommended": ...} 반환
    """
    df_result = recommend_by_season(season, gender=gender, top_n=3)
    top1, others = format_season_recommendation(df_result)

    return {
        "top1": top1,
        "recommended": others
    }