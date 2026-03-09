import streamlit as st
import pandas as pd
import plotly.express as px

# 1. BPL ROYAL UI & SLEEK CSS
st.set_page_config(page_title="BPL LEAGUE CENTRAL", page_icon="🏀", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    div[data-testid="stToolbar"] {visibility: hidden;} [data-testid="stStatusWidget"] {display: none;}
    .block-container { padding: 0rem !important; margin: 0rem !important; }
    .stApp { background: radial-gradient(circle at top, #001f3f 0%, #050505 100%); color: #e0e0e0; }
    div[data-testid="stMetric"] { 
        background: rgba(255, 255, 255, 0.05) !important; 
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 123, 255, 0.3) !important; 
        border-radius: 20px !important; padding: 20px !important;
    }
    .header-banner { 
        padding: 25px; text-align: center; 
        background: linear-gradient(90deg, #004085 0%, #007bff 50%, #004085 100%);
        color: #fff; font-family: 'Arial Black'; font-size: 28px;
    }
    @keyframes ticker { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    .ticker-wrap { width: 100%; overflow: hidden; background: #000; color: #007bff; padding: 12px 0; border-bottom: 1px solid #333; }
    .ticker-content { display: inline-block; white-space: nowrap; animation: ticker 45s linear infinite; }
    .ticker-item { display: inline-block; margin-right: 100px; font-weight: bold; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# 2. DATA ENGINE
SHEET_ID = "1Q5Q7_bk2RyNqJMbrYY5_VzDaPYhlEbQxqXA3BnYFBJU"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(URL)
        df.columns = df.columns.str.strip()
        
        # 1. Drop completely empty rows
        df = df.dropna(how='all')
        
        # 2. Safety check: Ensure the column exists before filtering
        if 'Player/Team' not in df.columns:
            return "ERROR: Column 'Player/Team' not found. Check your Google Sheet headers."

        # 3. CLEANING: Remove repeated headers and "TOTAL" rows
        df = df[df['Player/Team'].str.contains('Player/Team|TOTAL|Total', case=False, na=False) == False]
        
        # 4. Remove rows where the player name is missing
        df = df.dropna(subset=['Player/Team'])

        # 5. Ensure other key columns exist
        for col in ['Team Name', 'Type']:
            if col not in df.columns: df[col] = "Unknown"

        # 6. Convert numeric columns
        req_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'FTM', 'Game_ID', 'Win', 'Season']
        for c in req_cols:
            if c not in df.columns: df[c] = 0
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
        df['is_ff'] = (df['PTS'] == 0) & (df['FGA'] == 0) & (df['REB'] == 0)
        
        def calc_multis(row):
            if row['is_ff']: return pd.Series([0, 0])
            s = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for x in s if x >= 10)
            return pd.Series([1 if tens >= 2 else 0, 1 if tens >= 3 else 0])
            
        df[['DD', 'TD']] = df.apply(calc_multis, axis=1)
        df['PIE_Raw'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        df['Poss_Raw'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']
        df['FG%_Raw'] = (df['FGM'] / df['FGA'].replace(0,1) * 100).round(1)
        
        return df
    except Exception as e: return f"System Error: {str(e)}"

full_df = load_data()

# 3. STATS LOGIC
def get_stats(dataframe, group):
    if dataframe.empty: return pd.DataFrame()
    total_gp = dataframe.groupby(group).size().reset_index(name='GP')
    played_df = dataframe[dataframe['is_ff'] == False]
    played_gp = played_df.groupby(group).size().reset_index(name='Played_GP')
    
    sums = dataframe.groupby(group).sum(numeric_only=True).reset_index()
    m = pd.merge(sums, total_gp, on=group)
    m = pd.merge(m, played_gp, on=group, how='left').fillna(0)
    
    for col in ['DD', 'TD', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'Win', '3PM', 'TO', 'FGM', 'FGA', '3PA', 'FTA', 'FTM']:
        m[f'Total_{col}'] = m[col].astype(int)
    
    divisor = m['Played_GP'].replace(0, 1)
    for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', '3PA', 'FTM', 'FTA', 'Poss_Raw', 'FGA', 'FGM', 'PIE_Raw', 'DD', 'TD']:
        m[f'{col}/G'] = (m[col] / divisor).round(2)
    
    m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(2)
    m['PIE'] = m['PIE_Raw/G']
    return m

# 4. DIALOG CARDS
@st.dialog("🏀 BPL SCOUTING REPORT", width="large")
def show_card(name, stats_df, raw_df, is_player=True):
    row = stats_df.loc[name]
    st.title(f"{'👤' if is_player else '🏘️'} {name}")
    st.subheader("📈 Per Game Averages")
    c = st.columns(5); c[0].metric("PPG", row['PTS/G']); c[1].metric("RPG", row['REB/G']); c[2].metric("APG", row['AST/G']); c[3].metric("SPG", row['STL/G']); c[4].metric("BPG", row['BLK/G'])
    st.subheader("📊 Totals")
    t = st.columns(5); t[0].metric("Total PTS", row['Total_PTS']); t[1].metric("Total REB", row['Total_REB']); t[2].metric("Total AST", row['Total_AST']); t[3].metric("Total STL", row['Total_STL']); t[4].metric("Total BLK", row['Total_BLK'])
    
    st.markdown("---")
    if st.button("Close Card", use_container_width=True): st.rerun()

# 5. APP CONTENT
if isinstance(full_df, str): 
    st.error(full_df)
    st.info("Check that your Google Sheet has a column named exactly: Player/Team")
elif full_df is not None:
    st.markdown('<div class="header-banner">🏀 BPL HUB - POWERED BY QWIKTV</div>', unsafe_allow_html=True)
    
    div_col2 = st.columns([1,2,1])[1]
    division = div_col2.radio("SELECT DIVISION", ["HIGH SCHOOL", "COLLEGE", "PROS"], horizontal=True, label_visibility="collapsed")
    
    id_range = (1, 1999) if division == "HIGH SCHOOL" else (2000, 3999) if division == "COLLEGE" else (4000, 5999)
    df_div = full_df[full_df['Game_ID'].between(id_range[0], id_range[1])]

    seasons = sorted(df_div['Season'].unique(), reverse=True)
    opts = ["CAREER STATS"] + [f"Season {int(s)}" for s in seasons]
    sel_box = st.sidebar.selectbox("Scope", opts, index=min(1, len(opts)-1))
        
    df_active = df_div if sel_box == "CAREER STATS" else df_div[df_div['Season'] == int(sel_box.replace("Season ", ""))]
    df_reg = df_active[~df_active['Game_ID'].between(8000, 9999)]
    
    p_stats = get_stats(df_reg[df_reg['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
    t_stats = get_stats(df_reg[df_reg['Type'].str.lower() == 'team'], 'Team Name').set_index('Team Name')

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "🏆 POSTSEASON", "📖 HALL OF FAME"])

    with tabs[0]:
        if not p_stats.empty:
            p_disp = p_stats[['GP', 'PTS/G', 'AST/G', 'REB/G', 'PIE', 'FG%', 'Total_DD', 'Total_TD']].sort_values('PIE', ascending=False)
            sel_p = st.dataframe(p_disp, width="stretch", on_select="rerun", selection_mode="single-row", key="p_main")
            if len(sel_p.selection.rows) > 0: show_card(p_disp.index[sel_p.selection.rows[0]], p_stats, df_reg, True)
        else: st.info("No Player Data Found for this division/season.")

    with tabs[1]:
        if not t_stats.empty:
            t_stats['Record'] = t_stats['Total_Win'].astype(int).astype(str) + "-" + (t_stats['GP'] - t_stats['Total_Win']).astype(int).astype(str)
            st.dataframe(t_stats[['Record', 'PTS/G', 'AST/G', 'REB/G', 'FG%']].sort_values('Total_Win', ascending=False), width="stretch")

    with tabs[2]:
        l_cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "PIE"])
        if not p_stats.empty:
            st.plotly_chart(px.bar(p_stats.nlargest(10, l_cat), x=l_cat, y=p_stats.nlargest(10, l_cat).index, orientation='h', template="plotly_dark"), use_container_width=True)

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 BPL LEAGUE TRACKER</div>', unsafe_allow_html=True)
