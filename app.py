import streamlit as st
import pandas as pd
import plotly.express as px
from finvizfinance.screener.overview import Overview
from finvizfinance.quote import finvizfinance
from translate import Translator
from concurrent.futures import ThreadPoolExecutor

# 1. 极简移动端页面配置
st.set_page_config(
    page_title="Pro Stock Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed" # 手机端默认收起侧边栏
)

# 自定义 CSS：打造 App 质感
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border-radius: 10px; padding: 10px; border: 1px solid #30363d; }
    .stock-card {
        background: linear-gradient(145deg, #1e222d, #14171e);
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        border: 1px solid #30363d;
    }
    .ticker-name { font-size: 1.2rem; font-weight: bold; color: #e6edf3; }
    .price-tag { font-family: 'Courier New', monospace; font-size: 1.1rem; }
    .change-up { color: #39d353; font-weight: bold; background: rgba(57, 211, 83, 0.1); padding: 2px 8px; border-radius: 4px; }
    .change-down { color: #ff7b72; font-weight: bold; background: rgba(255, 123, 114, 0.1); padding: 2px 8px; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

class ProStockApp:
    def __init__(self):
        self.sector_map = {
            'Technology': '科技', 'Financial': '金融', 'Healthcare': '医疗',
            'Consumer Cyclical': '可选消费', 'Industrials': '工业', 'Communication Services': '通讯',
            'Consumer Defensive': '必需消费', 'Energy': '能源', 'Real Estate': '地产',
            'Utilities': '公用事业', 'Basic Materials': '材料'
        }
        self.translator = Translator(to_lang="zh")

    @st.cache_data(ttl=300)
    def get_data(_self, mode):
        fino = Overview()
        if mode == "S&P 500":
            fino.set_filter(filters_dict={'Index': 'S&P 500'})
        else:
            fino.set_filter(filters_dict={'Price': 'Over $5', 'Average Volume': 'Over 1M', 'Market Cap.': '+Mid (over $2bln)'})
        
        df = fino.screener_view()
        if df is None or df.empty: return pd.DataFrame()

        # 强制数值排序逻辑
        change_col = next((c for c in df.columns if 'Change' in c), None)
        df['N_Change'] = df[change_col].apply(lambda x: float(str(x).replace('%','').replace('+','')) if x else 0.0)
        df = df.sort_values(by='N_Change', ascending=False).head(30) # 手机端只看前30最强
        df['ZH_Sec'] = df['Sector'].map(_self.sector_map).fillna(df['Sector'])
        return df

    def get_zh_desc(self, ticker):
        try:
            desc = finvizfinance(ticker).ticker_description()
            return self.translator.translate(desc.split('.')[0]) if desc else "暂无描述"
        except: return "数据更新中..."

    def run(self):
        # 顶部导航
        st.markdown("<h2 style='text-align: center; color: white;'>PRO 终端</h2>", unsafe_allow_html=True)
        mode = st.tabs(["🔥 今日强劲动能", "🏆 标普500精选"])
        
        selected_mode = "Momentum" if mode[0].active else "S&P 500" # 伪代码逻辑，Streamlit Tabs 默认自选

        with st.spinner(''):
            # 简化模式选择
            tab_choice = st.radio("", ["强劲动能", "标普500"], horizontal=True, label_visibility="collapsed")
            df = self.get_data("S&P 500" if tab_choice == "标普500" else "Momentum")

        if not df.empty:
            # 1. 核心视觉：精简版热力图
            fig = px.treemap(
                df, path=['ZH_Sec', 'Ticker'], values=[1]*len(df),
                color='N_Change', color_continuous_scale='RdYlGn', range_color=[-3, 3],
                template="plotly_dark"
            )
            fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=300)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            # 2. 移动端列表：卡片式设计
            st.markdown("### 实时行情")
            
            # 预抓取前 5 名背景
            top_tickers = df['Ticker'].head(5).tolist()
            with ThreadPoolExecutor(max_workers=5) as executor:
                descs = list(executor.map(self.get_zh_desc, top_tickers))
            desc_map = dict(zip(top_tickers, descs))

            for idx, row in df.iterrows():
                with st.container():
                    change_class = "change-up" if row['N_Change'] > 0 else "change-down"
                    arrow = "▲" if row['N_Change'] > 0 else "▼"
                    
                    # 手机端卡片 HTML
                    st.markdown(f"""
                        <div class="stock-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span class="ticker-name">{row['Ticker']}</span>
                                    <span style="color: #8b949e; font-size: 0.8rem; margin-left: 8px;">{row['ZH_Sec']}</span>
                                </div>
                                <div class="price-tag">
                                    <span style="color: white; margin-right: 10px;">${row['Price']}</span>
                                    <span class="{change_class}">{arrow} {abs(row['N_Change'])}%</span>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # 详情按钮与跳转
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        if idx < 5:
                            with st.expander("业务背景"):
                                st.caption(desc_map.get(row['Ticker'], "暂无详情"))
                    with c2:
                        st.link_button(f"查看 {row['Ticker']} 行情", f"https://finance.yahoo.com/quote/{row['Ticker']}", use_container_width=True)
        else:
            st.error("数据加载中...")

if __name__ == "__main__":
    app = ProStockApp()
    app.run()