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
        
        # Aggressive Cleaning: Remove empty rows and repeated header rows
        df = df.dropna(subset=[df.columns[0]])
        if 'Player/Team' in df.columns:
            df = df[df['Player/Team'].astype(str).str.contains('Player/Team|TOTAL|Total', case=False) == False]
        
        # Standardize crucial columns
        if 'Player/Team' not in df.columns: df['Player/Team'] = "Unknown"
        if 'Team Name' not in df.columns: df['Team Name'] = "Unknown"
        if 'Type' not in df.columns: df['Type'] = "player"

        # Numeric conversion
        req_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', 'FGA', 'FGM', '3PM', '3PA', 'FTA', 'FTM', 'Game_ID', 'Win', 'Season']
        for c in req_cols:
            if c not in df.columns: df[c] = 0
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
        df['is_ff'] = (df['PTS'] == 0) & (df['FGA'] == 0) & (df['REB'] == 0)
        
        # Calculate Multis
        def calc_multis(row):
            if row['is_ff']: return pd.Series([0, 0])
            s = [row['PTS'], row['REB'], row['AST'], row['STL'], row['BLK']]
            tens = sum(1 for x in s if x >= 10)
            return pd.Series([1 if tens >= 2 else 0, 1 if tens >= 3 else 0])
        df[['DD', 'TD']] = df.apply(calc_multis, axis=1)
        
        # Raw stats for advanced analytics
        df['PIE_Raw'] = (df['PTS'] + df['REB'] + df['AST'] + df['STL'] + df['BLK']) - (df['FGA'] * 0.5) - df['TO']
        df['Poss_Raw'] = df['FGA'] + 0.44 * df['FTA'] + df['TO']
        df['FG%_Raw'] = (df['FGM'] / df['FGA'].replace(0,1) * 100).round(1)
        
        return df
    except Exception as e: return f"System Error: {str(e)}"

full_df = load_data()

# 3. STATS LOGIC (REBUILT FOR STABILITY)
def get_stats(dataframe, group_col):
    if dataframe.empty or group_col not in dataframe.columns: 
        return pd.DataFrame()
    
    # Calculate GP
    total_gp = dataframe.groupby(group_col).size().reset_index(name='GP')
    
    # Calculate sums for all numeric columns
    numeric_df = dataframe.select_dtypes(include=['number']).copy()
    numeric_df[group_col] = dataframe[group_col]
    sums = numeric_df.groupby(group_col).sum().reset_index()
    
    # Merge and Calculate Averages
    m = pd.merge(sums, total_gp, on=group_col)
    
    # Identify played games (non-forfeits) for better averages
    played_counts = dataframe[dataframe['is_ff'] == False].groupby(group_col).size().reset_index(name='Played_GP')
    m = pd.merge(m, played_counts, on=group_col, how='left').fillna({'Played_GP': 1})
    m['Played_GP'] = m['Played_GP'].replace(0, 1)
    
    # Totals
    for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'Win', '3PM', 'DD', 'TD']:
        m[f'Total_{col}'] = m[col].astype(int)
    
    # Averages
    for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'PIE_Raw']:
        m[f'{col}/G'] = (m[col] / m['Played_GP']).round(2)
    
    m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(2)
    m['PIE'] = m['PIE_Raw/G']
    
    return m

# 4. DIALOG CARDS
@st.dialog("🏀 BPL SCOUTING REPORT", width="large")
def show_card(name, stats_df, is_player=True):
    row = stats_df.loc[name]
    st.title(f"{'👤' if is_player else '🏘️'} {name}")
    st.subheader("📈 Per Game Averages")
    c = st.columns(5)
    c[0].metric("PPG", row['PTS/G'])
    c[1].metric("RPG", row['REB/G'])
    c[2].metric("APG", row['AST/G'])
    c[3].metric("SPG", row['STL/G'])
    c[4].metric("BPG", row['BLK/G'])
    st.divider()
    if st.button("Close", use_container_width=True): st.rerun()

# 5. APP CONTENT
if isinstance(full_df, str): 
    st.error(full_df)
elif full_df is not None:
    st.markdown('<div class="header-banner">🏀 BPL HUB - POWERED BY QWIKTV</div>', unsafe_allow_html=True)
    
    division = st.radio("DIVISION", ["HIGH SCHOOL", "COLLEGE", "PROS"], horizontal=True, label_visibility="collapsed")
    id_range = (1, 1999) if division == "HIGH SCHOOL" else (2000, 3999) if division == "COLLEGE" else (4000, 5999)
    df_div = full_df[full_df['Game_ID'].between(id_range[0], id_range[1])]

    seasons = sorted(df_div['Season'].unique(), reverse=True)
    opts = ["CAREER"] + [f"Season {int(s)}" for s in seasons]
    sel_box = st.sidebar.selectbox("Scope", opts, index=min(1, len(opts)-1))
        
    df_active = df_div if "CAREER" in sel_box else df_div[df_div['Season'] == int(sel_box.replace("Season ", ""))]
    
    # Split Player vs Team
    p_raw = df_active[df_active['Type'].astype(str).str.lower() == 'player']
    t_raw = df_active[df_active['Type'].astype(str).str.lower() == 'team']
    
    p_stats = get_stats(p_raw, 'Player/Team').set_index('Player/Team') if not p_raw.empty else pd.DataFrame()
    t_stats = get_stats(t_raw, 'Team Name').set_index('Team Name') if not t_raw.empty else pd.DataFrame()

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS"])

    with tabs[0]:
        if not p_stats.empty:
            p_disp = p_stats[['GP', 'PTS/G', 'AST/G', 'REB/G', 'FG%', 'PIE']].sort_values('PIE', ascending=False)
            sel_p = st.dataframe(p_disp, width="stretch", on_select="rerun", selection_mode="single-row", key="p_main")
            if len(sel_p.selection.rows) > 0:
                show_card(p_disp.index[sel_p.selection.rows[0]], p_stats, True)
        else: st.info("No player data for this selection.")

    with tabs[1]:
        if not t_stats.empty:
            t_stats['Record'] = t_stats['Total_Win'].astype(int).astype(str) + "-" + (t_stats['GP'] - t_stats['Total_Win']).astype(int).astype(str)
            st.dataframe(t_stats[['Record', 'PTS/G', 'REB/G', 'FG%']].sort_values('Total_Win', ascending=False), width="stretch")

    with tabs[2]:
        if not p_stats.empty:
            l_cat = st.selectbox("Stat", ["PTS/G", "REB/G", "AST/G", "PIE"])
            st.plotly_chart(px.bar(p_stats.nlargest(10, l_cat), x=l_cat, template="plotly_dark"), use_container_width=True)

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 BPL LEAGUE TRACKER</div>', unsafe_allow_html=True)
