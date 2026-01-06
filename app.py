import streamlit as st
import pandas as pd
import plotly.express as px
from finvizfinance.screener.overview import Overview
from finvizfinance.quote import finvizfinance
from translate import Translator
from concurrent.futures import ThreadPoolExecutor

# 1. 页面配置与移动端沉浸式设置
st.set_page_config(page_title="Market Heatmap Pro", layout="wide", initial_sidebar_state="collapsed")

# 2. 注入核心 CSS (复刻参考图的精致感)
st.markdown("""
    <style>
    /* 全局背景与字体 */
    [data-testid="stAppViewContainer"] { background-color: #0b0e14; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    
    /* 模拟手机端 Tab 按钮 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 40px; white-space: pre; background-color: #1e222d;
        border-radius: 20px; color: #848e9c; border: none; padding: 0px 20px;
    }
    .stTabs [aria-selected="true"] { background-color: #2ebd85 !important; color: white !important; }

    /* 精致行情卡片 */
    .market-card {
        background: #1e222d; border-radius: 12px; padding: 16px; margin-bottom: 12px;
        border: 1px solid #2b3139; transition: transform 0.2s;
    }
    .ticker-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .ticker-symbol { font-size: 1.1rem; font-weight: 700; color: #ffffff; }
    .ticker-sector { font-size: 0.75rem; color: #848e9c; }
    .price-box { text-align: right; }
    .price-main { font-size: 1.1rem; font-weight: 600; color: #ffffff; display: block; }
    .change-tag {
        font-size: 0.85rem; padding: 4px 10px; border-radius: 6px; font-weight: 600;
        display: inline-block; margin-top: 4px;
    }
    .up { background-color: rgba(46, 189, 133, 0.2); color: #2ebd85; }
    .down { background-color: rgba(246, 70, 93, 0.2); color: #f6465d; }
    
    /* 业务背景装饰 */
    .desc-text { font-size: 0.8rem; color: #b7bdc6; line-height: 1.4; border-top: 1px solid #2b3139; pt: 10px; mt: 10px; }
    
    /* 底部虚拟导航栏 */
    .nav-bar {
        position: fixed; bottom: 0; left: 0; width: 100%; background: #161a1e;
        display: flex; justify-content: space-around; padding: 10px 0; border-top: 1px solid #2b3139; z-index: 999;
    }
    .nav-item { text-align: center; color: #848e9c; font-size: 0.65rem; }
    .nav-item.active { color: #2ebd85; }
    </style>
""", unsafe_allow_html=True)

class ProApp:
    def __init__(self):
        self.sector_map = {'Technology': '科技', 'Financial': '金融', 'Healthcare': '医疗', 'Consumer Cyclical': '消费', 'Industrials': '工业', 'Communication Services': '通讯', 'Energy': '能源'}
        self.translator = Translator(to_lang="zh")

    @st.cache_data(ttl=300)
    def fetch_data(_self, mode):
        fino = Overview()
        fino.set_filter(filters_dict={'Index': 'S&P 500'} if mode == "S&P 500" else {'Price': 'Over $5', 'Average Volume': 'Over 1M'})
        df = fino.screener_view()
        if df is None or df.empty: return pd.DataFrame()
        
        # 强制排序修复
        df['Change_Val'] = df['Change'].apply(lambda x: float(str(x).replace('%','').replace('+','')) if x else 0.0)
        df = df.sort_values(by='Change_Val', ascending=False).head(25)
        df['ZH_Sec'] = df['Sector'].map(_self.sector_map).fillna(df['Sector'])
        return df

    def get_zh_desc(self, ticker):
        try:
            desc = finvizfinance(ticker).ticker_description()
            return self.translator.translate(desc.split('.')[0]) if desc else "持仓观望中"
        except: return "查看实时行情..."

    def run(self):
        # 头部标题 (复刻参考图样式)
        st.markdown("<h2 style='color: white; margin-bottom:0;'>市场热力图 <span style='font-weight:300; font-size:1.2rem; color:#848e9c;'>Market Heatmap</span></h2>", unsafe_allow_html=True)
        st.markdown("<p style='color:#848e9c; font-size:0.85rem; margin-top:0;'>市场板块可视化 Market Sector Visualization</p>", unsafe_allow_html=True)

        # 模式切换 Tab
        t1, t2 = st.tabs(["标普500 S&P 500", "动能异动 Momentum"])
        
        with t1:
            self.display_content("S&P 500")
        with t2:
            self.display_content("Momentum")

        # 底部导航栏虚拟占位
        st.markdown("""
            <div style='height: 80px;'></div>
            <div class="nav-bar">
                <div class="nav-item">🏠<br>首页</div>
                <div class="nav-item active">🧱<br>热力图</div>
                <div class="nav-item">📈<br>热门</div>
                <div class="nav-item">⚡<br>妖股</div>
                <div class="nav-item">📄<br>资讯</div>
            </div>
        """, unsafe_allow_html=True)

    def display_content(self, mode):
        df = self.fetch_data(mode)
        if df.empty: return st.error("正在同步全球行情...")

        # 1. 迷你热力图 (紧凑布局)
        fig = px.treemap(
            df, path=['ZH_Sec', 'Ticker'], values=[1]*len(df),
            color='Change_Val', color_continuous_scale=['#f6465d', '#1e222d', '#2ebd85'],
            range_color=[-3, 3]
        )
        fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), height=240, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        fig.update_traces(marker=dict(cornerradius=5), textinfo="label+value")
        st.plotly_chart(fig, width='stretch', config={'displayModeBar': False})

        # 2. 精致列表区
        st.markdown("### 实时概览")
        
        # 为了速度，只扫描涨幅前 5 的背景
        top_list = df['Ticker'].head(5).tolist()
        with ThreadPoolExecutor(max_workers=5) as executor:
            descs = list(executor.map(self.get_zh_desc, top_list))
        desc_map = dict(zip(top_list, descs))

        for idx, row in df.iterrows():
            c_class = "up" if row['Change_Val'] > 0 else "down"
            prefix = "+" if row['Change_Val'] > 0 else ""
            
            # 卡片 HTML
            st.markdown(f"""
                <div class="market-card">
                    <div class="ticker-header">
                        <div>
                            <span class="ticker-symbol">{row['Ticker']}</span><br>
                            <span class="ticker-sector">{row['ZH_Sec']}</span>
                        </div>
                        <div class="price-box">
                            <span class="price-main">${row['Price']}</span>
                            <span class="change-tag {c_class}">{prefix}{row['Change_Val']}%</span>
                        </div>
                    </div>
                    {"<div class='desc-text'><b>业务:</b> " + desc_map.get(row['Ticker']) + "</div>" if row['Ticker'] in desc_map else ""}
                </div>
            """, unsafe_allow_html=True)
            
            # 点击跳转链接
            st.link_button(f"🔗 进入 {row['Ticker']} 详情页", f"https://finance.yahoo.com/quote/{row['Ticker']}", use_container_width=True)

if __name__ == "__main__":
    app = ProApp()
    app.run()