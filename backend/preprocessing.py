import pandas as pd
import numpy as np
import json
import pickle
import re
from sklearn.preprocessing import MultiLabelBinarizer


# 1. CSV 로드
def load_data():
    """CSV 파일 로드"""
    df = pd.read_csv(
        'data/fra_cleaned.csv',
        encoding='latin1',
        engine='python',
        sep=None,
        quoting=3,
        on_bad_lines='skip'
    )
    return df


# 2. 기본 전처리
def basic_preprocessing(df):
    """
    - 불필요한 컬럼 삭제
    - Gender 텍스트 정리
    """
    # 불필요한 컬럼 삭제
    columns_to_drop = ['Country', 'Year', 'Perfumer1', 'Perfumer2', 'mainaccord4', 'mainaccord5']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])
    
    # Gender 텍스트 정리 (소문자 변환 + "for " 제거)
    if 'Gender' in df.columns:
        df['Gender'] = df['Gender'].str.lower().str.replace('for ', '', regex=False)
    
    return df


# 3. NOTE 기반 mainaccord 결측치 보완
NOTE_TO_CATEGORY = {
    # citrus
    "bergamot": "citrus", "lemon": "citrus", "lime": "citrus", "orange": "citrus",
    "grapefruit": "citrus", "mandarin": "citrus", "tangerine": "citrus",
    "yuzu": "citrus", "blood orange": "citrus", "bitter orange": "citrus",

    # floral
    "jasmine": "floral", "rose": "floral", "lily": "floral", "iris": "powdery",
    "violet": "floral", "peony": "floral", "tuberose": "white floral",
    "ylang ylang": "white floral", "lilac": "floral", "orchid": "floral",
    "freesia": "floral", "gardenia": "floral", "magnolia": "floral",
    "hyacinth": "floral", "narcissus": "floral", "lavender": "floral",
    "mimosa": "floral",

    # fruity
    "apple": "fruity", "pear": "fruity", "pineapple": "fruity",
    "peach": "fruity", "melon": "fruity", "raspberry": "fruity",
    "blackcurrant": "fruity", "strawberry": "fruity", "blackberry": "fruity",
    "cherry": "fruity", "plum": "fruity", "apricot": "fruity",
    "mango": "fruity", "banana": "fruity", "grape": "fruity",
    "fig": "fruity", "cassis": "fruity", "cranberry": "fruity",

    # woody
    "cedarwood": "woody", "vetiver": "woody", "sandalwood": "woody",
    "patchouli": "woody", "oak": "woody", "pine": "woody",
    "fir": "woody", "juniper": "woody", "teak": "woody",
    "agarwood": "woody", "rosewood": "woody", "birch": "woody",
    "cypress": "woody",

    # spicy
    "pink pepper": "spicy", "pepper": "spicy", "cardamom": "spicy",
    "cinnamon": "spicy", "nutmeg": "spicy", "saffron": "spicy",
    "clove": "spicy", "ginger": "spicy", "anise": "spicy",
    "cumin": "spicy", "coriander": "spicy", "allspice": "spicy",

    # gourmand
    "vanilla": "gourmand", "tonka bean": "gourmand", "cocoa": "gourmand",
    "chocolate": "gourmand", "caramel": "gourmand", "honey": "gourmand",
    "almond": "gourmand", "hazelnut": "gourmand", "praline": "gourmand",
    "sugar": "gourmand", "toffee": "gourmand",

    # amber / resinous
    "amber": "amber", "labdanum": "amber", "benzoin": "amber",
    "incense": "resinous", "myrrh": "resinous",

    # green / herbal
    "tea": "green", "green tea": "green", "grass": "green",
    "mint": "herbal", "basil": "herbal", "sage": "herbal", "thyme": "herbal",
    "fern": "green", "seaweed": "green", "galbanum": "green",

    # aquatic
    "water": "aquatic", "sea notes": "aquatic", "ozonic": "aquatic",
    "sea salt": "aquatic", "mineral": "aquatic",

    # synthetic
    "ambroxan": "synthetic", "iso e super": "synthetic",
    "hedione": "synthetic", "cashmeran": "synthetic",
}


def get_categories_from_notes(top_note, middle_note, base_note):
    """Top/Middle/Base 노트에서 카테고리 추론"""
    categories = set()
    
    for note in [top_note, middle_note, base_note]:
        if pd.isna(note):
            continue
        note_str = str(note).lower().strip()
        note_list = [n.strip() for n in note_str.split(',')]
        
        for n in note_list:
            if n in NOTE_TO_CATEGORY:
                categories.add(NOTE_TO_CATEGORY[n])
    
    return list(categories) if categories else None


def extract_inferred_accords(row):
    """각 행의 inferred_accords 생성"""
    categories = get_categories_from_notes(
        row.get('Top'),
        row.get('Middle'),
        row.get('Base')
    )
    return categories


def fill_missing_accord(row, accord_col):
    """mainaccord2, mainaccord3 결측치 보완"""
    if pd.isna(row[accord_col]) and row['inferred_accords'] is not None and len(row['inferred_accords']) > 0:
        inferred = row['inferred_accords']
        # 첫 번째는 mainaccord2, 두 번째는 mainaccord3에 할당
        if accord_col == 'mainaccord2' and len(inferred) >= 1:
            return inferred[0]
        elif accord_col == 'mainaccord3' and len(inferred) >= 2:
            return inferred[1]
    return row[accord_col]


def fill_last_missing_accord(row):
    """mainaccord3 남은 결측치 보완"""
    if pd.isna(row["mainaccord3"]) or row["mainaccord3"] == "":
        if not pd.isna(row["mainaccord2"]) and row["mainaccord2"] != "":
            row["mainaccord3"] = row["mainaccord2"]
        else:
            row["mainaccord3"] = row["mainaccord1"]
    return row


def fill_missing_accords(df):
    """mainaccord 결측치 보완"""
    df['inferred_accords'] = df.apply(extract_inferred_accords, axis=1)
    df['mainaccord2'] = df.apply(lambda row: fill_missing_accord(row, 'mainaccord2'), axis=1)
    df['mainaccord3'] = df.apply(lambda row: fill_missing_accord(row, 'mainaccord3'), axis=1)
    df = df.apply(fill_last_missing_accord, axis=1)
    df = df.drop(columns=['inferred_accords'])
    return df



# 4. Raw 노트 리스트 생성
def clean_raw_notes(note_str):
    """Top/Middle/Base를 리스트로 변환"""
    if pd.isna(note_str):
        return []
    note_str = str(note_str).strip()
    if not note_str:
        return []
    notes = [n.strip().lower() for n in note_str.split(',')]
    return [n for n in notes if n]


def create_raw_note_columns(df):
    """Top_raw, Middle_raw, Base_raw 컬럼 생성"""
    if 'Top' in df.columns:
        df['Top_raw'] = df['Top'].apply(clean_raw_notes)
    if 'Middle' in df.columns:
        df['Middle_raw'] = df['Middle'].apply(clean_raw_notes)
    if 'Base' in df.columns:
        df['Base_raw'] = df['Base'].apply(clean_raw_notes)
    
    return df


# 5. 계절 벡터 생성
def load_all_notes_json():
    """backend/data/all_notes.json 로드"""
    with open('data/all_notes.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def season_to_vector(season_list):
    """season 리스트 → 4차원 벡터 [1,1,0,0] 형태"""
    vector = [0, 0, 0, 0]
    for s in season_list:
        if 0 <= s < 4:
            vector[s] = 1
    return vector


def find_season_for_raw_notes(raw_list, season_vector_map):
    """노트 리스트 → 매칭된 벡터들의 평균 반환, 없으면 None"""
    matched_vectors = []
    for n in raw_list:
        key = n.strip().lower()
        if key in season_vector_map:
            matched_vectors.append(season_vector_map[key])
    if len(matched_vectors) == 0:
        return None
    mean_vec = np.mean(np.array(matched_vectors), axis=0)
    return mean_vec.tolist()


def create_season_columns(df, season_vector_map):
    """Season_top, Season_mid, Season_base 컬럼 생성"""
    df['Season_top'] = df['Top_raw'].apply(lambda x: find_season_for_raw_notes(x, season_vector_map))
    df['Season_mid'] = df['Middle_raw'].apply(lambda x: find_season_for_raw_notes(x, season_vector_map))
    df['Season_base'] = df['Base_raw'].apply(lambda x: find_season_for_raw_notes(x, season_vector_map))
    
    return df


# 6. 전체 노트 리스트 ALL_NOTES 생성
def create_all_notes_list(df):
    """Top_raw, Middle_raw, Base_raw에서 전체 노트 set으로 수집 후 정렬"""
    all_notes_set = set()
    
    if 'Top_raw' in df.columns:
        for notes in df['Top_raw']:
            all_notes_set.update(notes)
    if 'Middle_raw' in df.columns:
        for notes in df['Middle_raw']:
            all_notes_set.update(notes)
    if 'Base_raw' in df.columns:
        for notes in df['Base_raw']:
            all_notes_set.update(notes)
    
    return sorted(list(all_notes_set))


# 7. 노트 정규화 (cleanse_note)
REGION_WORDS = [
    "sicilian","italian","indian","japanese","egyptian","tunisian","moroccan",
    "brazilian","chinese","african","arabian","burmese","korean","french",
    "spanish","turkish","russian","persian","haitian","laotian","vietnamese",
    "calabrian","american","mexican","madagascar","madagascan","malaysian",
    "australian","argentinian","greek","romanian","thai","syrian","algerian"
]

REMOVE_TAILS = [
    "blossom","petals","petal","leaf","leaves","root","flower","flowers",
    "peel","zest","absolute","essence","extract","resin","oil","wood",
    "bark","buds"
]

PLURAL_MAP = {
    "berries": "berry",
    "fruits": "fruit",
    "notes": "note",
    "leaves": "leaf"
}

KEEP_AS_IS = {
    "coffee blossom", "orange blossom", "bluebell", "lily of the valley",
    "ylang ylang", "ylang-ylang", "woodsy notes", "woody notes",
    "marine notes", "aquatic notes"
}


def cleanse_note(note: str) -> str:
    """노트 정규화"""
    if not isinstance(note, str):
        return note
    n = note.strip().lower()
    if n in KEEP_AS_IS:
        return n.title()
    for region in REGION_WORDS:
        pattern = r"\b" + re.escape(region) + r"\b"
        n = re.sub(pattern, "", n).strip()
    for plural, singular in PLURAL_MAP.items():
        pattern = r"\b" + plural + r"\b"
        n = re.sub(pattern, singular, n)
    for tail in REMOVE_TAILS:
        pattern = r"\b" + tail + r"\b"
        n = re.sub(pattern, "", n).strip()
    n = re.sub(r"\s+", " ", n).strip()
    return n.title()


def normalize_notes_columns(df):
    """Top, Middle, Base 컬럼을 정규화된 리스트로 업데이트"""
    if 'Top_raw' in df.columns:
        df['Top_raw'] = df['Top_raw'].apply(lambda notes: [cleanse_note(n) for n in notes])
    if 'Middle_raw' in df.columns:
        df['Middle_raw'] = df['Middle_raw'].apply(lambda notes: [cleanse_note(n) for n in notes])
    if 'Base_raw' in df.columns:
        df['Base_raw'] = df['Base_raw'].apply(lambda notes: [cleanse_note(n) for n in notes])
    
    df["Top"] = df["Top_raw"]
    df["Middle"] = df["Middle_raw"]
    df["Base"] = df["Base_raw"]
    
    return df


# 8. 해시태그 컬럼 생성
def create_hashtag_columns(df):
    """Top Notes, Middle Notes, Base Notes 컬럼 생성 (#Rose #Jasmine 형태)"""
    if 'Top_raw' in df.columns:
        df['Top Notes'] = df['Top_raw'].apply(lambda notes: ' '.join([f'#{n.title()}' for n in notes]))
    if 'Middle_raw' in df.columns:
        df['Middle Notes'] = df['Middle_raw'].apply(lambda notes: ' '.join([f'#{n.title()}' for n in notes]))
    if 'Base_raw' in df.columns:
        df['Base Notes'] = df['Base_raw'].apply(lambda notes: ' '.join([f'#{n.title()}' for n in notes]))
    
    return df


# 9. 원핫 인코딩
def create_note_vectors(df, all_notes):
    """MultiLabelBinarizer로 ALL_NOTES 기준 원핫 인코딩"""
    # Top_raw, Middle_raw, Base_raw 합친 all_notes 컬럼
    df['all_notes'] = df.apply(
        lambda row: list(set(
            row.get('Top_raw', []) + 
            row.get('Middle_raw', []) + 
            row.get('Base_raw', [])
        )),
        axis=1
    )
    
    mlb = MultiLabelBinarizer(classes=all_notes)
    note_vectors = mlb.fit_transform(df['all_notes'])
    note_vectors_df = pd.DataFrame(note_vectors, columns=all_notes, index=df.index)
    
    df = df.drop(columns=['all_notes'])
    
    return df, note_vectors_df


# 10. 계절 최종 벡터 계산
def safe_vec(v):
    """None이면 [0,0,0,0] 반환"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return [0, 0, 0, 0]
    return v


def combine_seasons(row):
    """Top 0.5 + Middle 0.3 + Base 0.2 가중치로 Season_final 계산"""
    top_vec = safe_vec(row['Season_top'])
    mid_vec = safe_vec(row['Season_mid'])
    base_vec = safe_vec(row['Season_base'])
    
    combined = np.array(top_vec) * 0.5 + np.array(mid_vec) * 0.3 + np.array(base_vec) * 0.2
    return combined.tolist()


def softmax(v):
    """softmax 함수"""
    e_v = np.exp(np.array(v) - np.max(v))
    return (e_v / e_v.sum()).tolist()


def calculate_season_vectors(df):
    """계절 최종 벡터 계산"""
    df['Season_final'] = df.apply(combine_seasons, axis=1)
    df['Season_scaled'] = df['Season_final'].apply(softmax)
    
    # Season_label 생성
    season_labels = ['Spring', 'Summer', 'Autumn', 'Winter']
    df['Season_label'] = df['Season_scaled'].apply(lambda v: season_labels[np.argmax(v)])
    
    # 불필요한 컬럼 제거
    df = df.drop(columns=['Season_top', 'Season_mid', 'Season_base', 'Season_final'])
    
    return df


# 11. image_url 생성
def convert_fragrantica_url_to_image(url):
    """
    url에서 정규식으로 마지막 숫자 ID 추출 (-숫자.html 패턴)
    https://fimgs.net/mdimg/perfume/375x500.{perfume_id}.jpg 형태로 반환
    fragrantica가 url에 없으면 None 반환
    """
    if pd.isna(url):
        return None
    
    url = str(url)
    if 'fragrantica' not in url.lower():
        return None
    
    # -숫자.html 패턴 찾기
    match = re.search(r'-(\d+)\.html', url)
    if match:
        perfume_id = match.group(1)
        return f"https://fimgs.net/mdimg/perfume/375x500.{perfume_id}.jpg"
    
    return None


def create_image_url_column(df):
    """df에 image_url 컬럼 생성"""
    if 'url' in df.columns:
        df['image_url'] = df['url'].apply(convert_fragrantica_url_to_image)
    else:
        df['image_url'] = None
    
    return df


# 12. 피처 벡터 생성
def build_feature_vector(row, all_notes):
    """note 원핫 벡터 + season 벡터 concat"""
    note_vector = np.array(row[all_notes].values, dtype=float)
    season_vector = np.array(row['Season_scaled'], dtype=float)
    feature_vector = np.concatenate([note_vector, season_vector])
    return feature_vector


def create_feature_vectors(df_notes, all_notes):
    """df_notes에 feature_vector 컬럼 생성"""
    df_notes['feature_vector'] = df_notes.apply(
        lambda row: build_feature_vector(row, all_notes),
        axis=1
    )
    return df_notes


# 13. 저장
def save_data(df_notes, all_notes):
    """df_notes와 NOTE_COLUMNS 저장"""
    df_notes.to_pickle('data/df_notes.pkl')
    with open('data/note_columns.pkl', 'wb') as f:
        pickle.dump(all_notes, f)
    
    print("✓ 전처리 완료!")
    print(f"  - df_notes.pkl 저장 ({len(df_notes)} rows, {len(df_notes.columns)} columns)")
    print(f"  - note_columns.pkl 저장 ({len(all_notes)} notes)")


# Main 실행
def main():
    print("📊 Fragrance Preprocessing 시작...")
    
    # 1. CSV 로드
    print("\n1️⃣  CSV 로드 중...")
    df = load_data()
    print(f"   ✓ {len(df)} rows, {len(df.columns)} columns 로드됨")
    
    # 2. 기본 전처리
    print("\n2️⃣  기본 전처리 중...")
    df = basic_preprocessing(df)
    print(f"   ✓ {len(df.columns)} columns 남음")
    
    # 3. NOTE 기반 mainaccord 결측치 보완
    print("\n3️⃣  mainaccord 결측치 보완 중...")
    df = fill_missing_accords(df)
    print("   ✓ mainaccord 채움")
    
    # 4. Raw 노트 리스트 생성
    print("\n4️⃣  Raw 노트 리스트 생성 중...")
    df = create_raw_note_columns(df)
    print("   ✓ Top_raw, Middle_raw, Base_raw 생성")
    
    # 5. 계절 벡터 생성
    print("\n5️⃣  계절 벡터 생성 중...")
    all_notes_data = load_all_notes_json()
    season_vector_map = {item["note"].lower(): season_to_vector(item["season"]) for item in all_notes_data}
    df = create_season_columns(df, season_vector_map)
    print("   ✓ Season_top, Season_mid, Season_base 생성")
    
    # 6. 전체 노트 리스트 ALL_NOTES 생성
    print("\n6️⃣  ALL_NOTES 생성 중...")
    all_notes = create_all_notes_list(df)
    print(f"   ✓ {len(all_notes)} 개의 고유 노트")
    
    # 7. 노트 정규화
    print("\n7️⃣  노트 정규화 중...")
    df = normalize_notes_columns(df)
    print("   ✓ 노트 정규화 완료")
    
    # 재계산 ALL_NOTES (정규화 후)
    all_notes = create_all_notes_list(df)
    print(f"   ✓ {len(all_notes)} 개의 정규화된 노트")
    
    # 8. 해시태그 컬럼 생성
    print("\n8️⃣  해시태그 컬럼 생성 중...")
    df = create_hashtag_columns(df)
    print("   ✓ Top Notes, Middle Notes, Base Notes 생성")
    
    # 9. 원핫 인코딩
    print("\n9️⃣  원핫 인코딩 중...")
    df, note_vectors_df = create_note_vectors(df, all_notes)
    print(f"   ✓ {note_vectors_df.shape[1]}차원 벡터 생성")
    
    # 10. 계절 최종 벡터 계산
    print("\n🔟 계절 최종 벡터 계산 중...")
    df = calculate_season_vectors(df)
    print("   ✓ Season_scaled, Season_label 생성")
    
    # 11. image_url 생성
    print("\n1️⃣1️⃣  image_url 생성 중...")
    df = create_image_url_column(df)
    print("   ✓ image_url 생성")
    
    # 12. 피처 벡터 생성
    print("\n1️⃣2️⃣  피처 벡터 생성 중...")
    df_notes = pd.concat([df, note_vectors_df], axis=1)
    df_notes = create_feature_vectors(df_notes, all_notes)
    print(f"   ✓ {len(all_notes) + 4}차원 feature_vector 생성")
    
    # 13. 저장
    print("\n1️⃣3️⃣  데이터 저장 중...")
    save_data(df_notes, all_notes)


if __name__ == '__main__':
    main()
