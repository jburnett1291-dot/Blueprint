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
        
        # ADDED VALIDATION AS REQUESTED
        for col in ['Player/Team', 'Team Name', 'Type']:
            if col not in df.columns:
                df[col] = "Unknown"

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
    except Exception as e: return str(e)

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
    m['Total_Poss'] = m['Poss_Raw'].astype(int)
    
    divisor = m['Played_GP'].replace(0, 1)
    for col in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TO', '3PM', '3PA', 'FTM', 'FTA', 'Poss_Raw', 'FGA', 'FGM', 'PIE_Raw', 'DD', 'TD']:
        m[f'{col}/G'] = (m[col] / divisor).round(2)
    m['FG%'] = (m['FGM'] / m['FGA'].replace(0,1) * 100).round(2)
    m['TS%'] = (m['PTS'] / (2 * (m['FGA'] + 0.44 * m['FTA']).replace(0, 1)) * 100).round(2)
    m['PPS'] = (m['PTS'] / m['FGA'].replace(0, 1)).round(2)
    m['OffRtg'] = (m['PTS'] / m['Poss_Raw'].replace(0,1) * 100).round(1)
    m['DefRtg'] = (100 * (1 - ((m['STL'] + m['BLK'] + (m['REB'] * 0.7)) / m['Poss_Raw'].replace(0,1)))).round(1)
    m['PIE'] = m['PIE_Raw/G']
    m['Poss/G'] = m['Poss_Raw/G']
    return m

# 4. DIALOG CARDS
@st.dialog("🏀 BPL SCOUTING REPORT", width="large")
def show_card(name, stats_df, raw_df, is_player=True):
    row = stats_df.loc[name]
    st.title(f"{'👤' if is_player else '🏘️'} {name}")
    st.subheader("📈 Per Game Averages")
    c = st.columns(5); c[0].metric("PPG", row['PTS/G']); c[1].metric("RPG", row['REB/G']); c[2].metric("APG", row['AST/G']); c[3].metric("SPG", row['STL/G']); c[4].metric("BPG", row['BLK/G'])
    st.subheader("📊 Totals (Selected View)")
    t = st.columns(5); t[0].metric("Total PTS", row['Total_PTS']); t[1].metric("Total REB", row['Total_REB']); t[2].metric("Total AST", row['Total_AST']); t[3].metric("Total STL", row['Total_STL']); t[4].metric("Total BLK", row['Total_BLK'])
    st.markdown("---"); st.subheader("🏆 Season Highs")
    s_col = 'Player/Team' if is_player else 'Team Name'
    personal = raw_df[(raw_df[s_col] == name) & (raw_df['Type'].str.lower() == ('player' if is_player else 'team'))]
    h = st.columns(5); h[0].metric("Max PTS", int(personal['PTS'].max() if not personal.empty else 0)); h[1].metric("Max REB", int(personal['REB'].max() if not personal.empty else 0)); h[2].metric("Max AST", int(personal['AST'].max() if not personal.empty else 0)); h[3].metric("Max STL", int(personal['STL'].max() if not personal.empty else 0)); h[4].metric("Max BLK", int(personal['BLK'].max() if not personal.empty else 0))
    st.markdown("---"); st.subheader("🕒 Recent Form")
    recent = personal.sort_values(['Season', 'Game_ID'], ascending=False).head(3)
    for _, g in recent.iterrows():
        res = "✅ W" if g['Win'] == 1 else "❌ L"
        label = f"Game {int(g['Game_ID'])} | {res}"
        if g['is_ff']: st.info(f"{label} - FORFEIT")
        else:
            f = st.columns(6); f[0].metric(f"{label}", f"{int(g['PTS'])} PTS"); f[1].metric("REB", int(g['REB'])); f[2].metric("AST", int(g['AST'])); f[3].metric("STL", int(g['STL'])); f[4].metric("BLK", int(g['BLK'])); f[5].metric("FG%", f"{g['FG%_Raw']}%")
    if st.button("Close Card & Clear Selection", use_container_width=True): st.rerun()

# 5. APP CONTENT
if isinstance(full_df, str): st.error(f"⚠️ DATA ERROR: {full_df}")
elif full_df is not None:
    # Header & Division Filter
    st.markdown('<div class="header-banner">🏀 BPL HUB - POWERED BY QWIKTV</div>', unsafe_allow_html=True)
    
    div_col1, div_col2, div_col3 = st.columns([1,2,1])
    with div_col2:
        division = st.radio("SELECT DIVISION", ["HIGH SCHOOL", "COLLEGE", "PROS"], horizontal=True, label_visibility="collapsed")
    
    id_range = (1, 1999) if division == "HIGH SCHOOL" else (2000, 3999) if division == "COLLEGE" else (4000, 5999)
    df_div = full_df[full_df['Game_ID'].between(id_range[0], id_range[1])]

    seasons = sorted(df_div['Season'].unique(), reverse=True)
    opts = ["CAREER STATS"] + [f"Season {int(s)}" for s in seasons]
    with st.sidebar: 
        sel_box = st.selectbox("Scope", opts, index=min(1, len(opts)-1))
        
    df_active = df_div if sel_box == "CAREER STATS" else df_div[df_div['Season'] == int(sel_box.replace("Season ", ""))]
    df_reg = df_active[~df_active['Game_ID'].between(8000, 9999)]
    
    p_stats = get_stats(df_reg[df_reg['Type'].str.lower() == 'player'], 'Player/Team').set_index('Player/Team')
    t_stats = get_stats(df_reg[df_reg['Type'].str.lower() == 'team'], 'Team Name').set_index('Team Name')

    # BPL Leader Ticker
    if not p_stats.empty:
        ticker_min = p_stats['GP'].max() * 0.4
        qualified_p = p_stats[p_stats['GP'] >= ticker_min]
        if not qualified_p.empty:
            leads = [f"🏆 {c}: {qualified_p.nlargest(1, f'{c}/G').index[0]} ({qualified_p.nlargest(1, f'{c}/G').iloc[0][f'{c}/G']})" for c in ['PTS', 'AST', 'REB', 'STL', 'BLK']]
            st.markdown(f'<div class="ticker-wrap"><div class="ticker-content"><span class="ticker-item">{" • ".join(leads)}</span></div></div>', unsafe_allow_html=True)

    tabs = st.tabs(["👤 PLAYERS", "🏘️ STANDINGS", "🔝 LEADERS", "⚔️ VERSUS", "🏆 POSTSEASON", "📖 HALL OF FAME", "🔐 THE VAULT"])

    with tabs[0]:
        if not p_stats.empty:
            p_disp = p_stats[['GP', 'PTS/G', 'AST/G', 'REB/G', '3PM/G', '3PA/G', 'FGM/G', 'FGA/G', 'TO/G', 'PIE', 'FG%', 'Total_DD', 'Total_TD']].sort_values('PIE', ascending=False)
            sel_p = st.dataframe(p_disp, width="stretch", on_select="rerun", selection_mode="single-row", key="p_main")
            if len(sel_p.selection.rows) > 0: show_card(p_disp.index[sel_p.selection.rows[0]], p_stats, df_reg, True)
        else: st.info("No Player Data.")

    with tabs[1]:
        if not t_stats.empty:
            t_stats['Record'] = t_stats['Total_Win'].astype(int).astype(str) + "-" + (t_stats['GP'] - t_stats['Total_Win']).astype(int).astype(str)
            t_disp = t_stats.sort_values('Total_Win', ascending=False)[['Record', 'PTS/G', 'AST/G', 'REB/G', '3PM/G', '3PA/G', 'FGM/G', 'FGA/G', 'TO/G', 'PIE', 'FG%', 'DefRtg', 'OffRtg']]
            sel_t = st.dataframe(t_disp, width="stretch", on_select="rerun", selection_mode="single-row", key="t_main")
            if len(sel_t.selection.rows) > 0: show_card(t_disp.index[sel_t.selection.rows[0]], t_stats, df_reg, False)

    with tabs[2]:
        st.subheader("🔝 CATEGORY LEADERS")
        l_min = p_stats['GP'].max() * 0.4 if not p_stats.empty else 0
        filt_p = p_stats[p_stats['GP'] >= l_min]
        l_cat = st.selectbox("Category", ["PTS/G", "REB/G", "AST/G", "STL/G", "BLK/G", "PIE"])
        c_p, c_t = st.columns(2)
        with c_p:
            st.markdown("**👤 Player Leaders**")
            if not filt_p.empty:
                t10p = filt_p.nlargest(10, l_cat)[[l_cat]]
                st.dataframe(t10p, use_container_width=True)
                st.plotly_chart(px.bar(t10p, x=l_cat, y=t10p.index, orientation='h', template="plotly_dark", color_discrete_sequence=['#007bff']), use_container_width=True)
        with c_t:
            st.markdown("**🏘️ Team Leaders**")
            if not t_stats.empty:
                t10t = t_stats.nlargest(10, l_cat)[[l_cat]]
                st.dataframe(t10t, use_container_width=True)
                st.plotly_chart(px.bar(t10t, x=l_cat, y=t10t.index, orientation='h', template="plotly_dark", color_discrete_sequence=['#004085']), use_container_width=True)

    with tabs[3]:
        v_mode = st.radio("Comparison Mode", ["Player vs Player", "Team vs Team"], horizontal=True)
        v1, mid, v2 = st.columns([2, 1, 2])
        source = p_stats if v_mode == "Player vs Player" else t_stats
        if not source.empty:
            p1 = v1.selectbox("Choice 1", source.index, index=0)
            p2 = v2.selectbox("Choice 2", source.index, index=min(1, len(source)-1))
            d1, d2 = source.loc[p1], source.loc[p2]
            metrics = [('PPG', 'PTS/G'), ('APG', 'AST/G'), ('RPG', 'REB/G'), ('PIE', 'PIE'), ('FG%', 'FG%')]
            avg_df = source[[m[1] for m in metrics]].mean()
            for label, col in metrics:
                c1, cm, c2 = st.columns([2, 1, 2])
                c1.metric(p1, d1[col], round(d1[col]-d2[col], 2))
                cm.markdown(f"<div style='text-align:center; color:#007bff;'>{label}<br>{avg_df[col]:.1f}<br><small>AVG</small></div>", unsafe_allow_html=True)
                c2.metric(p2, d2[col], round(d2[col]-d1[col], 2))

    with tabs[4]:
        st.header("🏆 POSTSEASON BRACKETOLOGY")
        mode = st.radio("Mode", ["Playoffs (9k)", "Tournament (8k)"], horizontal=True)
        target_id = 9000 if "Playoffs" in mode else 8000
        post_df = df_active[df_active['Game_ID'] >= target_id]
        if post_df.empty: st.info(f"No {mode} data found.")
        else:
            ps_type = st.radio("Postseason View", ["Players", "Teams"], horizontal=True)
            col_id = 'Player/Team' if ps_type == "Players" else 'Team Name'
            ps_stats = get_stats(post_df[post_df['Type'].str.lower() == ps_type[:-1].lower()], col_id).set_index(col_id)
            if not ps_stats.empty:
                ps_disp = ps_stats[['GP', 'PTS/G', 'AST/G', 'REB/G', 'FG%', 'PIE']].sort_values('PIE', ascending=False)
                sel_ps = st.dataframe(ps_disp, width="stretch", on_select="rerun", selection_mode="single-row", key="ps_df")
                if len(sel_ps.selection.rows) > 0: show_card(ps_disp.index[sel_ps.selection.rows[0]], ps_stats, post_df, ps_type == "Players")

    with tabs[5]:
        st.header("📖 HALL OF FAME")
        st.subheader("🎯 BPL Milestone Tracker")
        
        # FIXED: Specific Thresholds
        milestones = {
            "Total_PTS": [50, 100, 200, 500, 1000, 2000], 
            "Total_AST": [25, 50, 100, 200, 500],
            "Total_REB": [50, 100, 200, 500, 1000], 
            "Total_STL": [20, 50, 100, 250],
            "Total_BLK": [10, 25, 50, 100, 200],
            "Total_3PM": [50, 100, 250, 500]
        }
        
        m_col = st.selectbox("Stat Category", list(milestones.keys()), format_func=lambda x: x.replace("Total_", ""))
        ms_data = []
        if not p_stats.empty:
            for entity_name, row in p_stats.iterrows():
                for goal in milestones[m_col]:
                    if row[m_col] >= goal: ms_data.append({"Achiever": entity_name, "Goal": goal, "Current": int(row[m_col]), "Status": "✅ COMPLETED"})
                    elif row[m_col] >= (goal * 0.85): ms_data.append({"Achiever": entity_name, "Goal": goal, "Current": int(row[m_col]), "Status": "👀 CLOSE"})
        if ms_data: st.dataframe(pd.DataFrame(ms_data).sort_values(["Goal", "Current"], ascending=[False, False]), use_container_width=True, hide_index=True)
        
        st.divider(); st.subheader("🌟 BPL All-Time Highs")
        valid_games = df_div[df_div['is_ff'] == False]
        h_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', '3PM']
        
        at_p, at_t = st.columns(2)
        with at_p:
            st.markdown("### 👤 Player Records")
            p_games = valid_games[valid_games['Type'].str.lower() == 'player']
            for col in h_cols:
                if not p_games.empty:
                    val = p_games[col].max(); best = p_games.loc[p_games[col].idxmax()]
                    st.metric(f"Record {col}", f"{int(val)}", f"by {best['Player/Team']}")
        with at_t:
            st.markdown("### 🏘️ Team Records")
            t_games = valid_games[valid_games['Type'].str.lower() == 'team']
            for col in h_cols:
                if not t_games.empty:
                    val = t_games[col].max(); best = t_games.loc[t_games[col].idxmax()]
                    st.metric(f"Record {col}", f"{int(val)}", f"by {best['Team Name']}")

        st.divider(); st.subheader(f"📅 Season {int(seasons[0])} Highs")
        latest_df = valid_games[valid_games['Season'] == seasons[0]]
        sh_p, sh_t = st.columns(2)
        with sh_p:
            st.markdown("### 👤 Player Season High")
            p_latest = latest_df[latest_df['Type'].str.lower() == 'player']
            for col in h_cols:
                if not p_latest.empty:
                    val = p_latest[col].max(); best = p_latest.loc[p_latest[col].idxmax()]
                    st.metric(f"Season {col}", f"{int(val)}", f"by {best['Player/Team']}")
        with sh_t:
            st.markdown("### 🏘️ Team Season High")
            t_latest = latest_df[latest_df['Type'].str.lower() == 'team']
            for col in h_cols:
                if not t_latest.empty:
                    val = t_latest[col].max(); best = t_latest.loc[t_latest[col].idxmax()]
                    st.metric(f"Season {col}", f"{int(val)}", f"by {best['Team Name']}")

    with tabs[6]:
        st.header("🔐 THE VAULT")
        if st.text_input("Passcode", type="password") == "BPL2026":
            st.success("Access Granted.")
            vault_cols = ['Total_PTS', 'Total_REB', 'Total_AST', 'Total_STL', 'Total_BLK', 'Total_3PM', 'Total_Win', 'Total_DD', 'Total_TD']
            st.dataframe(p_stats[vault_cols].sort_values('Total_PTS', ascending=False), width="stretch")
            st.divider(); st.markdown("### 📊 Advanced Analytics")
            adv = p_stats[p_stats['Played_GP'] > 0].reset_index().copy()
            st.dataframe(adv[['Player/Team', 'Poss/G', 'PPS', 'TS%', 'OffRtg', 'DefRtg', 'PIE']].sort_values('OffRtg', ascending=False), use_container_width=True, hide_index=True)
            v_view = st.selectbox("Vault Visualization", ["Vol vs Eff", "Off vs Def", "Poss Control"])
            ap = adv.rename(columns={'FGA/G': 'FGA_G', 'PTS/G': 'PTS_G', 'Poss/G': 'Poss_G', 'TO/G': 'TO_G'})
            if v_view == "Vol vs Eff": fig = px.scatter(ap, x='FGA_G', y='PTS_G', size='PIE', color='Player/Team', template="plotly_dark")
            elif v_view == "Off vs Def": fig = px.scatter(ap, x='OffRtg', y='DefRtg', size='PIE', color='Player/Team', template="plotly_dark"); fig.update_yaxes(autorange="reversed")
            else: fig = px.scatter(ap, x='Poss_G', y='TO_G', size='AST/G', color='Player/Team', template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            st.divider(); st.subheader("🔥 Performance Trends")
            streaks = []
            for p in p_stats.index:
                p_games = df_reg[(df_reg['Player/Team'] == p) & (df_reg['is_ff'] == False)]
                if len(p_games) >= 3:
                    avg_p = p_stats.loc[p, 'PTS/G']; l3 = p_games.sort_values('Game_ID', ascending=False).head(3)['PTS'].mean()
                    if l3 > avg_p * 1.2: streaks.append({"Entity": p, "Status": "🔥 HOT", "Trend": f"+{round(l3-avg_p,1)} PPG"})
                    elif l3 < avg_p * 0.8: streaks.append({"Entity": p, "Status": "❄️ COLD", "Trend": f"{round(l3-avg_p,1)} PPG"})
            if streaks: st.table(pd.DataFrame(streaks))

    st.markdown("---")
    la1, la2 = st.columns(2)
    if not p_stats.empty:
        p_avg = p_stats[['PTS/G', 'REB/G', 'AST/G', 'FG%']].mean()
        la1.write(f"**👤 Player Averages:** {p_avg['PTS/G']:.1f} PPG | {p_avg['REB/G']:.1f} RPG | {p_avg['FG%']:.1f}% FG")
    if not t_stats.empty:
        t_avg = t_stats[['PTS/G', 'OffRtg', 'DefRtg']].mean()
        la2.write(f"**🏘️ Team Averages:** {t_avg['PTS/G']:.1f} PPG | {t_avg['OffRtg']:.1f} OffRtg | {t_avg['DefRtg']:.1f} DefRtg")

    st.markdown('<div style="text-align: center; color: #444; padding: 30px;">© 2026 BPL LEAGUE TRACKER | POWERED BY QWIKTV | </div>', unsafe_allow_html=True)
