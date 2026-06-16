from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import os
from datetime import datetime
import numpy as np

from recommender import build_user_vector_v2, get_recommendation_result, get_season_recommendation


# 1. FastAPI 앱 생성
app = FastAPI(title="Fragrance Recommendation API", version="1.0.0")

# CORS 미들웨어 (모든 origin 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. 데이터 파일 경로
USERS_FILE = "data/users.json"
HISTORY_FILE = "data/history.json"


# 3. JSON 유틸 함수
def load_json(filepath):
    """파일 없으면 빈 dict 반환"""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(filepath, data):
    """JSON 저장"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def convert_to_serializable(obj):
    """numpy 타입을 JSON 직렬화 가능한 타입으로 변환"""
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, list):
        return [convert_to_serializable(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    return obj


# 4. Pydantic 스키마
class LoginRequest(BaseModel):
    student_id: str
    name: str


class RecommendRequest(BaseModel):
    top_note: Optional[str] = None
    mid_note: Optional[str] = None
    base_note: Optional[str] = None
    season: Optional[str] = None
    gender: Optional[str] = None


class SeasonRequest(BaseModel):
    season: str
    gender: Optional[str] = None


class HistoryRequest(BaseModel):
    student_id: str
    rec_type: str
    result: Dict[str, Any]


# 5. 엔드포인트

@app.post("/login")
def login(request: LoginRequest):
    """
    로그인 엔드포인트
    - 기존 사용자: 이름 검증
    - 신규 사용자: 등록
    """
    # 빈값 검증
    if not request.student_id or not request.student_id.strip():
        raise HTTPException(status_code=400, detail="student_id는 필수입니다")
    if not request.name or not request.name.strip():
        raise HTTPException(status_code=400, detail="name은 필수입니다")
    
    student_id = request.student_id.strip()
    name = request.name.strip()
    
    # users.json 로드
    users = load_json(USERS_FILE)
    
    # 기존 사용자 확인
    if student_id in users:
        # 이름 일치 확인
        if users[student_id]["name"] != name:
            raise HTTPException(status_code=400, detail="학번과 이름이 일치하지 않습니다")
        return {
            "success": True,
            "is_new": False,
            "student_id": student_id,
            "name": name
        }
    
    # 신규 등록
    users[student_id] = {
        "name": name,
        "created_at": datetime.now().isoformat()
    }
    save_json(USERS_FILE, users)
    
    return {
        "success": True,
        "is_new": True,
        "student_id": student_id,
        "name": name
    }


@app.post("/recommend")
def recommend(request: RecommendRequest):
    """
    맞춤 추천 엔드포인트
    top_note, mid_note, base_note 중 적어도 하나는 필수
    """
    # 노트 검증 (빈 문자열도 처리)
    if not (request.top_note or "").strip() and \
       not (request.mid_note or "").strip() and \
       not (request.base_note or "").strip():
        raise HTTPException(status_code=400, detail="top_note, mid_note, base_note 중 적어도 하나는 필수입니다")
    
    try:
        # user_vector 생성
        user_vector = build_user_vector_v2(
            top_note=request.top_note.title() if request.top_note else None,
            mid_note=request.mid_note.title() if request.mid_note else None,
            base_note=request.base_note.title() if request.base_note else None,
            season=request.season,
        )
        
        # 추천 결과 조회
        result = get_recommendation_result(user_vector, gender=request.gender)
        
        # numpy 타입 직렬화
        result = convert_to_serializable(result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 중 오류 발생: {str(e)}")


@app.post("/recommend/season")
def recommend_season(request: SeasonRequest):
    """
    계절 기반 추천 엔드포인트
    """
    # season 값 검증
    valid_seasons = ["Spring", "Summer", "Fall", "Winter"]
    if request.season not in valid_seasons:
        raise HTTPException(
            status_code=400,
            detail=f"season은 {valid_seasons} 중 하나여야 합니다"
        )
    
    try:
        # 계절 추천 조회
        result = get_season_recommendation(request.season, gender=request.gender)
        
        # numpy 타입 직렬화
        result = convert_to_serializable(result)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 중 오류 발생: {str(e)}")


@app.post("/history")
def save_history(request: HistoryRequest):
    """
    추천 기록 저장 엔드포인트
    """
    # history.json 로드
    history = load_json(HISTORY_FILE)
    
    # student_id 키가 없으면 리스트 생성
    if request.student_id not in history:
        history[request.student_id] = []
    
    # 기록 추가
    history[request.student_id].append({
        "rec_type": request.rec_type,
        "result": request.result,
        "timestamp": datetime.now().isoformat()
    })
    
    # 저장
    save_json(HISTORY_FILE, history)
    
    return {"success": True}


@app.get("/history/{student_id}")
def get_history(student_id: str):
    """
    사용자의 추천 기록 조회 엔드포인트
    """
    # history.json 로드
    history = load_json(HISTORY_FILE)
    
    # student_id에 해당하는 기록 조회
    user_history = history.get(student_id, [])
    
    return {
        "student_id": student_id,
        "history": user_history
    }


@app.delete("/history/{student_id}/{idx}")
def delete_history(student_id: str, idx: int):
    """
    사용자의 특정 추천 기록 삭제 엔드포인트
    """
    # history.json 로드
    history = load_json(HISTORY_FILE)
    
    # student_id 확인
    if student_id not in history:
        raise HTTPException(status_code=404, detail="사용자 기록을 찾을 수 없습니다")
    
    # 인덱스 범위 확인
    if idx < 0 or idx >= len(history[student_id]):
        raise HTTPException(status_code=404, detail="해당 인덱스의 기록을 찾을 수 없습니다")
    
    # 삭제
    del history[student_id][idx]
    
    # 저장
    save_json(HISTORY_FILE, history)
    
    return {"success": True}


@app.get("/")
def root():
    """루트 엔드포인트"""
    return {
        "message": "Fragrance Recommendation API v1.0.0",
        "endpoints": {
            "POST /login": "사용자 로그인",
            "POST /recommend": "맞춤 추천",
            "POST /recommend/season": "계절 기반 추천",
            "POST /history": "추천 기록 저장",
            "GET /history/{student_id}": "추천 기록 조회",
            "DELETE /history/{student_id}/{idx}": "추천 기록 삭제"
        }
    }


# 6. 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
