import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# --- 1. 페이지 설정 및 제목 ---
st.set_page_config(page_title="전기화재 분석 대시보드", layout="wide")
st.title("🔥 전기화재 통계 분석 대시보드")
st.markdown("공공데이터를 활용하여 전기화재 현황과 원인을 분석합니다.")

# --- 2. 데이터베이스 초기화 및 샘플 데이터 생성 ---
# (실제 DB 파일이 없어도 공부하실 수 있게 자동으로 만드는 부분입니다.)
def init_db():
    conn = sqlite3.connect('fire_data.db')
    cursor = conn.cursor()
    
    # 기존 샘플 테이블이 있을 경우 스키마와 데이터를 다시 생성합니다.
    cursor.execute("DROP TABLE IF EXISTS [월별 전기화재 발생수]")
    cursor.execute("DROP TABLE IF EXISTS [전기화재 발생수]")
    cursor.execute("DROP TABLE IF EXISTS [전기화재 원인]")
    
    # 테이블 생성
    cursor.execute("CREATE TABLE [월별 전기화재 발생수] ([연도 및 월] TEXT PRIMARY KEY, [전기화재 건수] TEXT)")
    cursor.execute("CREATE TABLE [전기화재 발생수] (연도 TEXT, 행정구역 TEXT, [전기화재 건수] TEXT, PRIMARY KEY(연도, 행정구역))")
    cursor.execute("CREATE TABLE [전기화재 원인] (연도 TEXT, [발화 원인] TEXT, [전기화재 건수] TEXT, 점유율 TEXT, PRIMARY KEY(연도, [발화 원인]))")
    
    # 월별 샘플 (2022~2024)
    monthly_samples = {
        '2022': [835, 695, 705, 610, 595, 758, 895, 953, 666, 625, 595, 870],
        '2023': [905, 617, 640, 545, 693, 642, 1090, 1011, 609, 546, 715, 858],
        '2024': [750, 633, 682, 574, 630, 623, 991, 1074, 757, 536, 639, 745],
    }

    # 기존 DB가 있어도 월별 데이터를 최신 코드 값으로 덮어쓰기
    cursor.execute("DELETE FROM [월별 전기화재 발생수]")
    for y, counts in monthly_samples.items():
        for m, count in enumerate(counts, start=1):
            cursor.execute("INSERT INTO [월별 전기화재 발생수] VALUES (?, ?)", (f"{y}.{m:02d}.", str(count)))

    # 데이터가 비어있을 경우 행정구역/원인 샘플 데이터 삽입
    cursor.execute("SELECT count(*) FROM [전기화재 발생수]")
    if cursor.fetchone()[0] == 0:
        regions = ['서울특별시', '경기도', '부산광역시', '인천광역시', '대구광역시', '경상남도', '충청남도']
        import random
        for y in ['2022', '2023', '2024']:
            for r in regions:
                cursor.execute("INSERT INTO [전기화재 발생수] VALUES (?, ?, ?)", (y, r, str(random.randint(50, 500))))

    # 항상 원인 테이블을 초기화하여 최신 점유율 데이터를 유지합니다.
    cursor.execute("DELETE FROM [전기화재 원인]")
    # 각 연도별 발화 원인 데이터 (원인, 점유율)
    data_2022 = [('접촉 불량', '10.4'), ('과부하 및 과전류', '7'), ('절연열화에 의한 단락', '18.5'), 
                 ('트래킹에 의한 단락', '13.4'), ('기타', '17.6'), ('미확인 단락', '33.2')]
    data_2023 = [('접촉 불량', '10.2'), ('과부하 및 과전류', '7.9'), ('절연열화에 의한 단락', '18.2'), 
                 ('트래킹에 의한 단락', '14.7'), ('기타', '15'), ('미확인 단락', '34')]
    data_2024 = [('접촉 불량', '12.5'), ('과부하 및 과전류', '8.3'), ('절연열화에 의한 단락', '19.5'), 
                 ('트래킹에 의한 단락', '15'), ('기타', '9.6'), ('미확인 단락', '35.1')]
    
    year_data = [('2022', data_2022), ('2023', data_2023), ('2024', data_2024)]
    import random
    for y, causes_shares in year_data:
        for cause, share in causes_shares:
            cursor.execute("INSERT INTO [전기화재 원인] VALUES (?, ?, ?, ?)", 
                         (y, cause, str(random.randint(50, 200)), share))
    conn.commit()
    return conn

conn = init_db()

# --- 3. 사이드바 (연도 선택) ---
selected_year = st.sidebar.selectbox("📅 분석 연도 선택", ['2022', '2023', '2024'])

# --- 4. 차트 구현부 ---

# 차트 1: 월별 전기화재 발생수 (라인차트)
st.subheader(f"1️⃣ {selected_year}년 월별 전기화재 발생 추이")
sql1 = f"SELECT [연도 및 월], [전기화재 건수] FROM [월별 전기화재 발생수] WHERE [연도 및 월] LIKE '{selected_year}.%'"
df1 = pd.read_sql(sql1, conn)
df1['전기화재 건수'] = pd.to_numeric(df1['전기화재 건수'])

col1_1, col1_2 = st.columns([2, 1])
with col1_1:
    fig1 = px.line(df1, x='연도 및 월', y='전기화재 건수', markers=True, title="월별 발생 건수 변화")
    st.plotly_chart(fig1, use_container_width=True)
with col1_2:
    st.info("**SQL Query**\n```sql\n" + sql1 + "\n```")
    st.success(f"**Insight**\n- {selected_year}년 데이터 분석 결과, 계절적 요인에 따라 변동폭이 관찰됩니다.\n- 특히 전력 사용량이 많은 특정 월에 사고가 집중되는 경향이 있습니다.")

st.divider()

# 차트 2: 행정구역 TOP 5 (막대 그래프)
st.subheader(f"2️⃣ {selected_year}년 지역별 전기화재 TOP 5")
sql2 = f"SELECT 행정구역, [전기화재 건수] FROM [전기화재 발생수] WHERE 연도 = '{selected_year}' ORDER BY CAST([전기화재 건수] AS INTEGER) DESC LIMIT 5"
df2 = pd.read_sql(sql2, conn)
df2['전기화재 건수'] = pd.to_numeric(df2['전기화재 건수'])

col2_1, col2_2 = st.columns([2, 1])
with col2_1:
    fig2 = px.bar(df2, x='행정구역', y='전기화재 건수', color='행정구역', title="피해 건수 상위 5개 지역")
    st.plotly_chart(fig2, use_container_width=True)
with col2_2:
    st.info("**SQL Query**\n```sql\n" + sql2 + "\n```")
    st.success(f"**Insight**\n- {df2.iloc[0]['행정구역']} 지역의 발생 건수가 가장 높게 나타났습니다.\n- 인구 밀집도가 높은 대도시 위주로 집중적인 화재 예방 교육이 필요해 보입니다.")

st.divider()

# 차트 3: 전기화재 원인 (원그래프)
st.subheader(f"3️⃣ {selected_year}년 전기화재 발화 원인 비중")
sql3 = f"SELECT [발화 원인], 점유율 FROM [전기화재 원인] WHERE 연도 = '{selected_year}'"
df3 = pd.read_sql(sql3, conn)
df3['점유율'] = pd.to_numeric(df3['점유율'])

col3_1, col3_2 = st.columns([2, 1])
with col3_1:
    fig3 = px.pie(df3, values='점유율', names='발화 원인', hole=0.4, title="원인별 점유율(%)")
    st.plotly_chart(fig3, use_container_width=True)
with col3_2:
    st.info("**SQL Query**\n```sql\n" + sql3 + "\n```")
    st.success(f"**Insight**\n- 가장 큰 원인은 '{df3.iloc[0]['발화 원인']}'(으)로 나타났습니다.\n- 노후 설비 점검 및 올바른 전기 사용 습관이 사고 방지의 핵심입니다.")

conn.close()