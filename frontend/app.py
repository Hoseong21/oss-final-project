import streamlit as st
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Streamlit 페이지 설정 (전역)
st.set_page_config(page_title="Sce.note", layout="wide")

# 전역 CSS
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=IBM+Plex+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
<style>
.stApp {
    background-color: #F8F4ED;
}
.block-container {
    max-width: 900px;
    margin: auto;
    padding-top: 2rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
}
.stButton > button {
    background-color: #8B5345;
    color: white;
    border: none;
}
.stButton > button:hover {
    background-color: #7A4538;
    color: white;
    border: none;
}
body, p, li, label, div {
    font-family: 'IBM Plex Sans KR', sans-serif !important;
}
/* 입력창 배경색 */
.stTextInput > div > div > input {
    background-color: #F0E8DC;
    border: 1px solid #D4BFA5;
}
/* selectbox 배경색 */
.stSelectbox > div > div {
    background-color: #F0E8DC;
    border: 1px solid #D4BFA5;
}
header[data-testid="stHeader"] {
    background-color: #F8F4ED;
}
[data-testid="stSidebar"] {
    background-color: #F0E8DC;
}
/* 사이드바 색상 */
[data-testid="stSidebar"] .stButton > button {
    background-color: #ffffff !important;
    color: #333333 !important;
    border: none !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #F8F4ED !important;
    color: #7A4538 !important;
    border: none !important;
}           
[data-testid="stSidebar"] .stButton > button p {
    color: #333333 !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #333333 !important;
}
/* selectbox 텍스트 입력 비활성화 */
.stSelectbox input {
    pointer-events: none !important;
    user-select: none !important;
    -webkit-user-select: none !important;
    caret-color: transparent !important;
    cursor: pointer !important;
}
.stSelectbox [data-baseweb="select"] input {
    pointer-events: none !important;
    caret-color: transparent !important;
}            
</style>
""", unsafe_allow_html=True)

# 1. 상수 정의
NOTE_GROUP_DESC = {
    "Citrus": "레몬·라임 같은 상큼하고 싱그러운 향",
    "Fruity": "달콤하거나 발랄한 과일 과즙 느낌의 향",
    "Green": "숲 속에 들어간 듯한 시원한 자연의 향",
    "Floral": "향수하면 떠오르는 꽃 중심의 대중적인 향",
    "Spicy": "이국적이고 자극적인 향신료 느낌의 향",
    "Fresh": "비누·바람·바다 같은 깨끗하고 시원한 향",
    "Woody": "나무의 이미지처럼 부드럽고 중후한 향",
    "Musk": "따뜻하고 관능적인 느낌의 향",
    "Amber": "따뜻하고 달콤한 파우더리한 느낌의 향",
    "Sweet": "달달한 디저트 느낌의 향",
    "Leather": "가죽 특유의 스모키하고 강렬한 향",
}

NOTE_GROUPS = {
    "Citrus": ["bergamot", "lemon", "orange", "mandarin orange", "grapefruit", "yuzu", "lime", "neroli", "petitgrain"],
    "Floral": ["jasmine", "rose", "peony", "violet", "geranium", "orange blossom", "lily-of-the-valley", "magnolia", "iris", "tuberose", "gardenia", "ylang-ylang", "lavender", "heliotrope"],
    "Fruity": ["apple", "pear", "peach", "black currant", "raspberry", "strawberry", "pineapple"],
    "Green": ["green tea", "mint", "basil", "sage", "rosemary", "mate", "fig"],
    "Woody": ["cedar", "sandalwood", "vetiver", "patchouli", "guaiac", "oakmoss", "cashmere", "cypress", "agarwood (oud)"],
    "Spicy": ["pink pepper", "black pepper", "pepper", "cardamom", "cinnamon", "clove", "nutmeg", "ginger", "saffron"],
    "Sweet": ["vanilla", "tonka bean", "caramel", "honey", "praline", "chocolate", "coconut", "cotton candy"],
    "Musk": ["musk", "white musk", "ambrette"],
    "Amber": ["amber", "benzoin", "labdanum", "frankincense", "myrrh", "olibanum", "ambergris", "incense"],
    "Leather": ["leather"],
    "Fresh": ["sea salt", "aquatic notes", "aldehydes", "ozonic"]
}

TOP_NOTE_GROUPS = ["Citrus", "Fruity", "Green", "Floral", "Spicy", "Fresh"]
MID_NOTE_GROUPS = ["Floral", "Woody", "Spicy", "Green", "Fruity", "Leather"]
BASE_NOTE_GROUPS = ["Woody", "Musk", "Amber", "Sweet", "Leather"]


# 2. 유틸 함수
def clean_name(name):
    """향수 이름에서 '-' 제거 및 정리"""
    if not isinstance(name, str):
        return name
    return name.replace("-", " ").strip().title()


def notes_to_hashtags(note_list):
    """['Cinnamon','Orange'] → #Cinnamon #Orange"""
    if not isinstance(note_list, list):
        return ""
    return " ".join([f"#{n.replace(' ', '')}" for n in note_list])


def call_api(method, endpoint, **kwargs):
    """FastAPI 백엔드 호출"""
    try:
        url = f"{BACKEND_URL}{endpoint}"
        if method.upper() == "GET":
            response = requests.get(url, **kwargs)
        elif method.upper() == "POST":
            response = requests.post(url, json=kwargs.get("json"), **{k: v for k, v in kwargs.items() if k != "json"})
        elif method.upper() == "DELETE":
            response = requests.delete(url, **kwargs)
        
        if response.status_code >= 400:
            try:
                error_detail = response.json().get("detail", "오류가 발생했습니다")
            except:
                error_detail = "오류가 발생했습니다"
            st.error(f"오류: {error_detail}")
            return None
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"API 오류: {str(e)}")
        return None


# 3. Session State 초기화
if "page" not in st.session_state:
    st.session_state["page"] = "home"
if "student_id" not in st.session_state:
    st.session_state["student_id"] = None
if "name" not in st.session_state:
    st.session_state["name"] = None
if "show_history" not in st.session_state:
    st.session_state["show_history"] = False


@st.dialog("🔐 로그인")
def show_login_dialog():
    student_id = st.text_input("학번", placeholder="예: 2027010101", max_chars=10)
    name = st.text_input("이름", placeholder="예: 홍길동", max_chars=10)
    
    if st.button("로그인", use_container_width=True, key="btn_login"):
        if not student_id or not name:
            st.error("학번과 이름을 입력해주세요")
        else:
            result = call_api("POST", "/login", json={"student_id": student_id, "name": name})
            if result:
                st.session_state["student_id"] = result["student_id"]
                st.session_state["name"] = result["name"]
                st.session_state["page"] = "main"
                st.rerun()


# 4. 페이지 렌더링 함수
def render_home():
    """홈 페이지"""
    st.markdown("""

<h1 style="font-family: 'Playfair Display', serif; font-size: 3.5rem;">Sce.note</h1>
<h4 style="font-family: 'IBM Plex Sans KR', sans-serif; font-weight: 700;">🧴 향수 추천 서비스</h4>
<p style="font-family: 'IBM Plex Sans KR', sans-serif;">본인의 취향을 반영한 노트를 선택하거나, 계절에 맞는 향수를 추천받을 수 있습니다.</p>
<p style="font-family: 'IBM Plex Sans KR', sans-serif;"><b>기능:</b></p>
<ul style="font-family: 'IBM Plex Sans KR', sans-serif;">
    <li><b>노트 기반 추천</b>: 자신이 좋아하는 향수 노트를 선택하여 맞춤 추천</li>
    <li><b>계절 기반 추천</b>: 계절에 어울리는 향수 자동 추천</li>
    <li><b>추천 히스토리</b>: 받은 추천 기록 저장 및 관리</li>
</ul>
""", unsafe_allow_html=True)

    if st.button("시작하기 →", use_container_width=True, key="btn_home"):
        show_login_dialog()


def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        st.markdown("""
<div style="margin-top: -2rem;">
<hr style="margin: 0.5rem 0;">
</div>
""", unsafe_allow_html=True)
        st.markdown("""
<h4 style="font-family: 'IBM Plex Sans KR', sans-serif; font-weight: 700;">👤 로그인 정보</h4>
""", unsafe_allow_html=True)
        st.markdown(f"**{st.session_state['name']} 님**")
        st.markdown(f"학번: {st.session_state['student_id']}")
        if st.button("로그아웃", use_container_width=True, key="btn_logout"):
            st.session_state["student_id"] = None
            st.session_state["name"] = None
            st.session_state["page"] = "home"
            st.session_state["show_history"] = False
            st.rerun()
        
        st.markdown("---")
        btn_label = "돌아가기" if st.session_state.get("show_history") else "추천 히스토리"
        if st.button(btn_label, use_container_width=True, key="btn_history"):
            st.session_state["show_history"] = not st.session_state["show_history"]
            st.rerun()


def render_history():
    """히스토리 렌더링"""
    st.markdown("""
<h1 style="font-family: 'Playfair Display', serif;">Sce.note</h1>
<h2 style="font-family: 'IBM Plex Sans KR', sans-serif; font-weight: 700;">추천 히스토리</h2>
""", unsafe_allow_html=True)
    
    result = call_api("GET", f"/history/{st.session_state['student_id']}")
    if not result:
        return
    
    original_history = result.get("history", [])
    total = len(original_history)
    history = list(reversed(original_history))

    if not history:
        st.info("추천 기록이 없습니다")
        return

    for display_idx, rec in enumerate(history):
        idx = total - 1 - display_idx
        rec_type = rec.get("rec_type", "unknown")
        timestamp = rec.get("timestamp", "")
        result_data = rec.get("result", {})
        
        title = "노트 기반 추천" if rec_type == "note" else "계절 기반 추천"
        
        with st.expander(f"{title} - {timestamp[:10]}"):
            top1 = result_data.get("top1", {})
            col_img, col_divider, col_info = st.columns([2, 0.1, 4])

            with col_img:
                if top1.get("image_url"):
                    st.image(top1["image_url"], width=240)

            with col_divider:
                st.markdown("""
                <div style="border-left: 1px solid #C9B99A; height: 100%; min-height: 320px;"></div>
                """, unsafe_allow_html=True)

            with col_info:
                st.markdown(f"<h4 style='font-family: IBM Plex Sans KR, sans-serif; font-weight: 700;'>{clean_name(top1.get('name', 'N/A'))} ({clean_name(top1.get('brand', 'N/A'))})</h4>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'>성별: {top1.get('gender', 'N/A')}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'>계절: {top1.get('season', 'N/A')}</p>", unsafe_allow_html=True)
                if top1.get('url'):
                    st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><a href='{top1['url']}'>Fragrantica로 이동</a></p>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><b>Top Notes:</b> {notes_to_hashtags(top1.get('top_notes', []))}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><b>Middle Notes:</b> {notes_to_hashtags(top1.get('middle_notes', []))}</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><b>Base Notes:</b> {notes_to_hashtags(top1.get('base_notes', []))}</p>", unsafe_allow_html=True)
        
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button("삭제", key=f"del_history_{display_idx}_{rec.get('timestamp', display_idx)}"):
                        del_result = call_api("DELETE", f"/history/{st.session_state['student_id']}/{idx}")
                        if del_result and del_result.get("success"):
                            st.success("삭제되었습니다")
                            st.rerun()


def render_main():
    """메인 페이지"""
    render_sidebar()

    if st.session_state.get("show_history"):
        render_history()
        return

    st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
<h1 style="font-family: 'Playfair Display', serif;">Sce.note</h1>
""", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["노트 기반 추천", "계절 기반 추천"])
    
    # =====================================================================
    # TAB 1: Note 기반 추천
    # =====================================================================
    with tab1:
        st.markdown("""
<h2 style="font-family: 'IBM Plex Sans KR', sans-serif; font-weight: 700;">노트 기반 추천</h2>
""", unsafe_allow_html=True)
        
        gender = st.selectbox("성별 선택", ["전체", "men", "women", "unisex"], key="gender_tab1")

        # Top Note
        top_group_options = ["선택 안함"] + [f"{grp} — {NOTE_GROUP_DESC.get(grp, '')}" for grp in TOP_NOTE_GROUPS]
        top_group_label = st.selectbox("Top Note 그룹", top_group_options, key="top_group_select")
        top_group = top_group_label.split(" — ")[0]
        top_note = None
        if top_group != "선택 안함":
            top_note_options = ["선택 안함"] + NOTE_GROUPS.get(top_group, [])
            top_note_label = st.selectbox("Top Note", top_note_options, key="top_note_select")
            top_note = None if top_note_label == "선택 안함" else top_note_label

        # Middle Note
        mid_group_options = ["선택 안함"] + [f"{grp} — {NOTE_GROUP_DESC.get(grp, '')}" for grp in MID_NOTE_GROUPS]
        mid_group_label = st.selectbox("Middle Note 그룹", mid_group_options, key="mid_group_select")
        mid_group = mid_group_label.split(" — ")[0]
        mid_note = None
        if mid_group != "선택 안함":
            mid_note_options = ["선택 안함"] + NOTE_GROUPS.get(mid_group, [])
            mid_note_label = st.selectbox("Middle Note", mid_note_options, key="mid_note_select")
            mid_note = None if mid_note_label == "선택 안함" else mid_note_label

        # Base Note
        base_group_options = ["선택 안함"] + [f"{grp} — {NOTE_GROUP_DESC.get(grp, '')}" for grp in BASE_NOTE_GROUPS]
        base_group_label = st.selectbox("Base Note 그룹", base_group_options, key="base_group_select")
        base_group = base_group_label.split(" — ")[0]
        base_note = None
        if base_group != "선택 안함":
            base_note_options = ["선택 안함"] + NOTE_GROUPS.get(base_group, [])
            base_note_label = st.selectbox("Base Note", base_note_options, key="base_note_select")
            base_note = None if base_note_label == "선택 안함" else base_note_label

        season = st.selectbox("계절 선택", ["선택 안함", "Spring", "Summer", "Fall", "Winter"], key="season_tab1")
        season = None if season == "선택 안함" else season
        
        if st.button("향수 추천 받기", use_container_width=True, key="btn_tab1"):
            if not top_note and not mid_note and not base_note:
                st.error("❗ Top / Middle / Base Note 중 최소 1개는 선택해야 합니다.")
            else:
                with st.spinner("추천 중입니다..."):
                    gender_input = None if gender == "전체" else gender
                    
                    rec_result = call_api("POST", "/recommend", json={
                        "top_note": top_note,
                        "mid_note": mid_note,
                        "base_note": base_note,
                        "season": season,
                        "gender": gender_input
                    })
                    
                    if rec_result:
                        top1 = rec_result.get("top1", {})
                        others = rec_result.get("recommended", [])
                        
                        st.markdown("<h3 style='font-family: IBM Plex Sans KR, sans-serif; font-weight: 700;'>TOP 1 추천 향수</h3>", unsafe_allow_html=True)
                        st.markdown("")
                        col_img, col_divider, col_info = st.columns([2, 0.15, 4])

                        with col_img:
                            if top1.get("image_url"):
                                st.image(top1["image_url"], width=250)

                        with col_divider:
                            st.markdown("""
                            <div style="border-left: 1px solid #C9B99A; height: 100%; min-height: 330px;"></div>
                            """, unsafe_allow_html=True)

                        with col_info:
                            st.markdown(f"<h3 style='font-family: IBM Plex Sans KR, sans-serif; font-weight: 700;'>{clean_name(top1.get('name', 'N/A'))} ({clean_name(top1.get('brand', 'N/A'))})</h3>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'>성별: {top1.get('gender', 'N/A')}</p>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'>계절: {top1.get('season', 'N/A')}</p>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><a href='{top1['url']}'>Fragrantica로 이동</a></p>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><b>Top Notes:</b> {notes_to_hashtags(top1.get('top_notes', []))}</p>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><b>Middle Notes:</b> {notes_to_hashtags(top1.get('middle_notes', []))}</p>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><b>Base Notes:</b> {notes_to_hashtags(top1.get('base_notes', []))}</p>", unsafe_allow_html=True)
                            st.markdown("</div>", unsafe_allow_html=True)
                                
                        st.markdown("---")
                        st.markdown("<h3 style='font-family: IBM Plex Sans KR, sans-serif; font-weight: 700;'>Top 2~4 추천 향수</h3>", unsafe_allow_html=True)
                        
                        cols = st.columns(3)
                        for col, rec in zip(cols, others):
                            with col:
                                st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><b>{clean_name(rec.get('name', 'N/A'))}</b> ({clean_name(rec.get('brand', 'N/A'))})</p>", unsafe_allow_html=True)
                                if rec.get("image_url"):
                                    st.image(rec["image_url"], width=150)
                        
                        call_api("POST", "/history", json={
                            "student_id": st.session_state["student_id"],
                            "rec_type": "note",
                            "result": rec_result
                        })
    
    # =====================================================================
    # TAB 2: 계절 기반 추천
    # =====================================================================
    with tab2:
        st.markdown("""
<h2 style="font-family: 'IBM Plex Sans KR', sans-serif; font-weight: 700;">계절 기반 추천</h2>
""", unsafe_allow_html=True)
        
        season = st.selectbox("계절 선택", ["선택 안함", "Spring", "Summer", "Fall", "Winter"], key="season_tab2")
        season = None if season == "선택 안함" else season
        gender2 = st.selectbox("성별 선택", ["전체", "men", "women", "unisex"], key="gender_tab2")
        gender2 = None if gender2 == "전체" else gender2
        
        if st.button("향수 추천 받기", use_container_width=True, key="btn_tab2"):
            if not season:
                st.error("❗ 계절을 선택해주세요.")
            else:
                with st.spinner("계절 향수 추천 중..."):
                    rec_result = call_api("POST", "/recommend/season", json={
                        "season": season,
                        "gender": gender2
                    })
                
                    if rec_result:
                        top1 = rec_result.get("top1", {})
                        others = rec_result.get("recommended", [])
                    
                        st.markdown("<h3 style='font-family: IBM Plex Sans KR, sans-serif; font-weight: 700;'>TOP 1 추천 향수</h3>", unsafe_allow_html=True)
                        st.markdown("")
                        col_img, col_divider, col_info = st.columns([2, 0.15, 4.3])

                        with col_img:
                            if top1.get("image_url"):
                                st.image(top1["image_url"], width=250)

                        with col_divider:
                            st.markdown("""
                            <div style="border-left: 1px solid #C9B99A; height: 100%; min-height: 330px;"></div>
                            """, unsafe_allow_html=True)

                        with col_info:
                            st.markdown(f"<h3 style='font-family: IBM Plex Sans KR, sans-serif; font-weight: 700;'>{clean_name(top1.get('name', 'N/A'))} ({clean_name(top1.get('brand', 'N/A'))})</h3>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'>성별: {top1.get('gender', 'N/A')}</p>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'>계절: {top1.get('season', 'N/A')}</p>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><a href='{top1['url']}'>Fragrantica로 이동</a></p>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><b>Top Notes:</b> {notes_to_hashtags(top1.get('top_notes', []))}</p>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><b>Middle Notes:</b> {notes_to_hashtags(top1.get('middle_notes', []))}</p>", unsafe_allow_html=True)
                            st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><b>Base Notes:</b> {notes_to_hashtags(top1.get('base_notes', []))}</p>", unsafe_allow_html=True)
                        
                        st.markdown("---")
                        st.markdown("<h3 style='font-family: IBM Plex Sans KR, sans-serif; font-weight: 700;'>Top 2~3 추천 향수</h3>", unsafe_allow_html=True)
                        
                        cols = st.columns(2)
                        for col, rec in zip(cols, others):
                            with col:
                                st.markdown(f"<p style='font-family: IBM Plex Sans KR, sans-serif;'><b>{clean_name(rec.get('name', 'N/A'))}</b> ({clean_name(rec.get('brand', 'N/A'))})</p>", unsafe_allow_html=True)
                                if rec.get("image_url"):
                                    st.image(rec["image_url"], width=150)
                        
                        call_api("POST", "/history", json={
                            "student_id": st.session_state["student_id"],
                            "rec_type": "season",
                            "result": rec_result
                        })


# 5. Main 함수
def main():
    """메인 진입점"""
    page = st.session_state.get("page", "home")
    
    if page == "home":
        render_home()
    elif page == "main":
        if st.session_state["student_id"]:
            render_main()
        else:
            st.session_state["page"] = "login"
            st.rerun()


if __name__ == "__main__":
    main()