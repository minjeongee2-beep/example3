import json
import streamlit as st
from openai import OpenAI

# 페이지 기본 설정
st.set_page_config(
    page_title="서·논술형 답안 자동 채점 시스템",
    page_icon="📝",
    layout="wide"
)

st.title("📝 서·논술형 문항 자동 채점 시스템")
st.caption("2회고사 대비 모의 문항 (1~3세트) 전용 자동 채점기")

# API 키 및 세트 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    # Secrets 설정이 되어 있으면 우선 사용, 없으면 사이드바 입력받음
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
        st.success("Secrets에서 API Key를 로드했습니다.")
    else:
        api_key = st.text_input("OpenAI API Key 입력", type="password")
        
    selected_set = st.selectbox(
        "채점할 문항 세트 선택", 
        ["1세트 (사회적 촉진/억제)", "2세트 (정전기의 특징)", "3세트 (AI 그림과 예술)"]
    )

# 세트별 채점 프롬프트 데이터베이스
RUBRICS = {
    "1세트 (사회적 촉진/억제)": {
        "q1": """
        [문항] 표 요약 (1)과제의 특성, (2)효율적인 환경/방법, (3)관련 심리 현상
        [채점 기준]
        - (1) 필수: '쉬운', '익숙한', '친숙한', '노력이 들지 않는' 중 의미 포함. 오개념(어려운 과제)은 오답.
        - (2) 필수: '혼자' 필수 포함 + ('집중', '익숙', '연습' 중 의미 포함). 타인과 함께하는 내용 쓰면 오답.
        - (3) 필수: 정확히 '사회적 억제' (학술 용어로 용어 변경/오탈자 불가).
        """,
        "q2": """
        [문항] 과제 난이도에 따른 학습 전략 설명문 (2문장)
        [채점 기준]
        - (1)문장: 쉬운 과제 + 타인/함께/도서관/커피숍 내용 포함. 예시/비교 등의 설명 기법 의미 반영.
        - (2)문장: 어려운 과제 + 혼자 집중하는 내용 포함. 대조/구분 등의 설명 기법 의미 반영.
        - 오개념: 쉬운 과제와 어려운 과제의 환경을 반대로 작성 시 오답.
        - 기법 명칭 괄호 표기 유무와 상관없이 기법의 특성과 의미가 문장에 반영되었으면 인정.
        """,
        "q3": """
        [문항] 영상 기획안 (어려운 과제 시각/청각 연출 및 효과)
        [채점 기준]
        - 시각(A): 혼자 방에서 집중하는 구체적 연출 + 어려운 과제는 혼자 해야 효율적이라는 지문 근거 효과 서술.
        - 청각(B): 정적, 초침 소리, 잔잔한 음향 연출 + 주변 방해 없이 집중하는 환경을 조성한다는 효과 서술.
        - 결론 방향: 혼자 집중해야 학습 효율이 올라간다는 결론이 명확해야 함.
        """
    },
    "2세트 (정전기의 특징)": {
        "q1": """
        [문항] 표 요약 (1)물의 상태 비유, (2)전하의 상태, (3)위험성
        [채점 기준]
        - (1) 필수: '높은 곳' + '고여 있는 물' (단순 '고여 있는 물'은 부분점수/감점).
        - (2) 필수: '이동하지 않음', '정지', '머물러 있음' 중 의미 포함.
        - (3) 필수: '위험하지 않음', '피해가 없음' (전압은 높지만 위험하지 않다는 결론 명확해야 함).
        """,
        "q2": """
        [문항] 정전기의 특징 설명문 (2문장)
        [채점 기준]
        - (1)문장: 정전기의 정의(전하 정지/이동 없음/개념)를 밝히는 내용.
        - (2)문장: 실생활 전기(흐르는 물)와의 비교/대조/비유 및 위험하지 않다는 특징.
        - 논리 흐름: (1)과 (2)가 자연스럽게 이어져야 함.
        - 오개념: 정전기가 이동한다거나 위험하다고 서술 시 0점.
        """,
        "q3": """
        [문항] 정전기 영상 기획안 (시각/청각 연출 및 효과)
        [채점 기준]
        - 시각(A): 높은 곳에 고여 있는 물 연출 + 전하가 이동하지 않아 위험하지 않다는 지문 근거 포함.
        - 청각(B): 고요함/소리 없음 연출 + "움직이지 아니하여 조용하다(靜)"는 한자 의미/지문 근거 포함.
        - 결론 방향: 전압은 높으나 전하 미이동으로 위험하지 않다라는 결론 필수.
        """
    },
    "3세트 (AI 그림과 예술)": {
        "q1": """
        [문항] 표 요약 (1)올림픽 비유, (2)예술 여부/근거, (3)예술적 가치
        [채점 기준]
        - (1) 필수: '로봇' + '실수 없이/완벽한' + '피겨 스케이팅' 의미 포함.
        - (2) 필수: 감정, 독자적 철학, 이야기, 경험 중 1개 이상 부재함 + 예술로 보기 어렵다는 결론.
        - (3) 필수: 기존 미술계 변화, 예술 범주 확장, 상징적 가치 중 1개 이상 포함.
        """,
        "q2": """
        [문항] AI 그림을 바라보는 시각 설명문 (2문장)
        [채점 기준]
        - (1)문장: 인간 작품(감정/경험)과 AI 그림(감정 없음)의 차이점 서술 (대조 특성 반영).
        - (2)문장: 에드몽 드 벨라미 등 AI 작품 사례와 변화/가치 서술 (예시 특성 반영).
        - 오개념: AI가 감정을 느낀다고 서술하거나 결론이 왜곡되면 오답.
        """,
        "q3": """
        [문항] AI/인간 예술 영상 기획안 (시각/청각 연출 및 효과)
        [채점 기준]
        - 시각(A): 화가/선수의 노력/고뇌 클로즈업 + 인간 작품에는 감정/철학/경험이 담긴다는 지문 근거.
        - 청각(B): 숨소리, 따뜻한/웅장한 음악 + 마음의 울림과 감동을 준다는 지문 근거.
        - 결론 방향: 인간의 예술은 감동과 울림을 준다는 결론이 명확해야 함.
        """
    }
}

# 채점 함수
def evaluate_answer(client_instance, rubric_text, user_answer):
    prompt = f"""
    당신은 국어과 서논술형 채점 전문 출제위원입니다.
    아래 [채점 루브릭]과 [채점 원칙]에 따라 [학생 답안]을 엄격하게 평가하세요.

    [채점 원칙]
    1. 용어 없이 의미 인정: 조건에서 요구한 설명 방법 용어(예: 정의, 예시, 대조 등)가 직접 명시되지 않았더라도, 문장 내용에 해당 방법의 특성과 의미가 담겨있으면 인정합니다.
    2. 방법의 특성 반영: 특정 설명 방법을 썼다고 주장하거나 선택한 경우, 그 기법에 부합하는 내용적 특성이 답안에 드러나야 합니다.
    3. 오개념 방지 (엄격 채점): 대상의 특성을 교차하여 잘못 적용하거나 개념을 오해한 경우 감점 또는 0점 처리하세요.
    4. 결론 방향 검증: 문제에서 정한 최종 결론이나 지문의 핵심 결론 방향이 왜곡 없이 명확히 드러나야 합니다.

    [채점 루브릭]
    {rubric_text}

    [학생 답안]
    {user_answer}

    반드시 아래 구조를 가진 유효한 JSON 형식으로만 답변하세요:
    {{
        "score": "통과 / 부분점수 / 재작성 필요",
        "score_num": "점수 (예: 5/5)",
        "feedback": "채점 이유 및 세부 피드백",
        "model_answer": "모범 답안 예시"
    }}
    """

    try:
        response = client_instance.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "score": "오류 발생",
            "score_num": "0/0",
            "feedback": f"채점 처리 중 오류가 발생했습니다: {str(e)}",
            "model_answer": "API Key 또는 네트워크 설정을 확인하세요."
        }

# UI 구성
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown(f"### ✍️ 답안 입력 ({selected_set})")
    q1_ans = st.text_area("서·논술형 1번 답안 (표 요약)", height=120, placeholder="(1) ...\n(2) ...\n(3) ...")
    q2_ans = st.text_area("서·논술형 2번 답안 (설명문 작성)", height=150, placeholder="(1) ...\n(2) ...")
    q3_ans = st.text_area("서·논술형 3번 답안 (영상 기획안 및 효과)", height=180, placeholder="(1) 시각 요소 및 효과: ...\n(2) 청각 요소 및 효과: ...")

    submit_btn = st.button("🚀 자동 채점 실행하기", use_container_width=True)

with col2:
    st.markdown("### 📊 채점 결과 및 피드백")
    
    if submit_btn:
        if not api_key:
            st.error("OpenAI API Key가 설정되지 않았습니다. 사이드바에서 Key를 입력하거나 Secrets를 설정하세요.")
        elif not (q1_ans.strip() or q2_ans.strip() or q3_ans.strip()):
            st.warning("최소 한 개 이상의 문항에 답안을 입력해주세요.")
        else:
            client = OpenAI(api_key=api_key)
            current_rubric = RUBRICS[selected_set]

            if q1_ans.strip():
                with st.spinner("1번 문항 채점 중..."):
                    res1 = evaluate_answer(client, current_rubric["q1"], q1_ans)
                    st.markdown(f"#### [서·논술형 1] 결과: {res1['score']} ({res1['score_num']})")
                    st.info(f"**피드백:**\n{res1['feedback']}")
                    st.markdown(f"**💡 모범 답안 참고:**\n{res1['model_answer']}")
                    st.divider()

            if q2_ans.strip():
                with st.spinner("2번 문항 채점 중..."):
                    res2 = evaluate_answer(client, current_rubric["q2"], q2_ans)
                    st.markdown(f"#### [서·논술형 2] 결과: {res2['score']} ({res2['score_num']})")
                    st.info(f"**피드백:**\n{res2['feedback']}")
                    st.markdown(f"**💡 모범 답안 참고:**\n{res2['model_answer']}")
                    st.divider()

            if q3_ans.strip():
                with st.spinner("3번 문항 채점 중..."):
                    res3 = evaluate_answer(client, current_rubric["q3"], q3_ans)
                    st.markdown(f"#### [서·논술형 3] 결과: {res3['score']} ({res3['score_num']})")
                    st.info(f"**피드백:**\n{res3['feedback']}")
                    st.markdown(f"**💡 모범 답안 참고:**\n{res3['model_answer']}")