import streamlit as st
import pandas as pd
import plotly.express as px
from finvizfinance.screener.overview import Overview
from finvizfinance.quote import finvizfinance
from translate import Translator
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="美股复盘终极版", layout="wide")

class FinalStockApp:
    def __init__(self):
        self.sector_map = {
            'Technology': '信息技术', 'Financial': '金融服务', 'Healthcare': '医疗保健',
            'Consumer Cyclical': '可选消费', 'Industrials': '工业制造', 'Communication Services': '通讯服务',
            'Consumer Defensive': '必需消费', 'Energy': '能源石油', 'Real Estate': '房地产',
            'Utilities': '公用事业', 'Basic Materials': '基础材料'
        }
        try:
            self.translator = Translator(to_lang="zh")
        except:
            self.translator = None

    @st.cache_data(ttl=300)
    def fetch_data(_self, mode):
        fino = Overview()
        # 1. 设置更严谨的过滤器
        if mode == "S&P 500":
            fino.set_filter(filters_dict={'Index': 'S&P 500'})
        else:
            # 动能榜：过滤掉低价股和低成交量，专注活跃中大盘
            fino.set_filter(filters_dict={
                'Market Cap.': '+Mid (over $2bln)',
                'Average Volume': 'Over 1M',
                'Price': 'Over $5'
            })
        
        df = fino.screener_view()
        if df is None or df.empty: return pd.DataFrame()

        # 2. 核心修复：强制转换 Change 为数值进行排序
        def clean_change(x):
            try:
                return float(str(x).replace('%', '').strip())
            except:
                return 0.0

        df['Change_Num'] = df['Change'].apply(clean_change)
        
        # 3. 强制按涨幅从高到低排序，解决“A开头”问题
        df = df.sort_values(by='Change_Num', ascending=False)
        
        # 4. 只取前 50 只最强的股票，确保加载速度
        df = df.head(50).copy()
        df['板块汉化'] = df['Sector'].map(_self.sector_map).fillna(df['Sector'])
        df['YahooURL'] = "https://finance.yahoo.com/quote/" + df['Ticker']
        return df

    def get_desc(self, ticker):
        try:
            stock = finvizfinance(ticker)
            desc = stock.ticker_description()
            if not desc: return "无详细描述"
            # 仅取一句话，防止手机端崩溃
            short = desc.split('.')[0] 
            if self.translator:
                return self.translator.translate(short)
            return short
        except:
            return "点击下方链接查看公司详情"

    def run(self):
        st.sidebar.header("复盘配置")
        mode = st.sidebar.selectbox("切换榜单", ["今日强势异动", "S&P 500"])
        
        st.title(f"🚀 {mode} (Top 50)")

        with st.spinner('正在分析实时动能...'):
            df = self.fetch_data(mode)

        if not df.empty:
            # 5. 深度背景扫描 (仅限 Top 10，确保手机端秒开)
            top_tickers = df['Ticker'].head(10).tolist()
            with ThreadPoolExecutor(max_workers=5) as executor:
                descriptions = list(executor.map(self.get_desc, top_tickers))
            
            desc_map = dict(zip(top_tickers, descriptions))
            df['背景'] = df['Ticker'].map(desc_map).fillna("实时行情火热，点击下方链接深入了解")

            # 6. 绘图：优化移动端显示
            fig = px.treemap(
                df,
                path=[px.Constant(mode), '板块汉化', 'Ticker'],
                values=pd.Series([1]*len(df)),
                color='Change_Num',
                color_continuous_scale='RdYlGn',
                range_color=[-4, 4],
                custom_data=['YahooURL', 'Price', 'Change', '背景']
            )

            fig.update_traces(
                hovertemplate="<b>%{label}</b><br>涨幅: %{customdata[2]}<br>背景: %{customdata[3]}"
            )

            st.plotly_chart(fig, use_container_width=True)
            
            # 7. 终极跳转解决方案：手机端点击磁贴
            st.write("### 🎯 深度调研 (直接点击跳转)")
            # 采用分栏显示，节省手机空间
            cols = st.columns(2)
            for idx, row in df.head(10).iterrows():
                with cols[idx % 2]:
                    # 按钮样式跳转
                    st.link_button(f"🔍 {row['Ticker']}: {row['Change']}", row['YahooURL'], use_container_width=True)
                    st.caption(f"{row['背景']}")
        else:
            st.error("数据加载失败，请刷新页面。")

if __name__ == "__main__":
    app = FinalStockApp()
    app.run()