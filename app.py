import streamlit as st
import pandas as pd
import plotly.express as px
from finvizfinance.screener.overview import Overview
from finvizfinance.quote import finvizfinance
from translate import Translator
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="美股复盘终极修复", layout="wide")

class FinalDiagnosticApp:
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
        # 1. 设置过滤器
        if mode == "S&P 500":
            fino.set_filter(filters_dict={'Index': 'S&P 500'})
        else:
            fino.set_filter(filters_dict={
                'Market Cap.': '+Mid (over $2bln)',
                'Average Volume': 'Over 1M',
                'Price': 'Over $5'
            })
        
        df = fino.screener_view()
        
        if df is None or df.empty:
            return pd.DataFrame()

        # 💡 [核心修复1] 自动寻找包含 "Change" 字样的列名（解决表头偏移）
        target_col = None
        for col in df.columns:
            if 'Change' in col:
                target_col = col
                break
        
        if not target_col:
            st.error(f"找不到涨跌幅列，当前列名有: {df.columns.tolist()}")
            return df

        # 💡 [核心修复2] 暴力清洗：去除百分号、转浮点数
        def force_float(val):
            try:
                # 处理 "+2.50%" 或 "2.50" 甚至括号的情况
                clean_val = str(val).replace('%', '').replace('+', '').strip()
                return float(clean_val)
            except:
                return 0.0

        df['Change_Value'] = df[target_col].apply(force_float)
        
        # 💡 [核心修复3] 强制降序排列（确保最高涨幅在最前）
        df = df.sort_values(by='Change_Value', ascending=False)
        
        # 只取前 50 只
        df = df.head(50).copy()
        df['板块汉化'] = df['Sector'].map(_self.sector_map).fillna(df['Sector'])
        df['YahooURL'] = "https://finance.yahoo.com/quote/" + df['Ticker']
        
        return df

    def get_desc(self, ticker):
        try:
            stock = finvizfinance(ticker)
            desc = stock.ticker_description()
            if not desc: return "无详细描述"
            short = desc.split('.')[0]
            if self.translator:
                return self.translator.translate(short)
            return short
        except:
            return "获取中..."

    def run(self):
        st.sidebar.header("配置")
        mode = st.sidebar.selectbox("切换模式", ["动能异动榜", "S&P 500"])
        
        st.title(f"🚀 {mode}")

        df = self.fetch_data(mode)

        if not df.empty:
            # 💡 [核心修复4] 移动端跳转按钮：使用更稳定的 st.markdown 模拟按钮
            st.write("### 🎯 深度调研 (点击以下代码跳转)")
            
            # 展示前 10 名的跳转链接（解决手机端无法点击图表的问题）
            top_10 = df.head(10)
            cols = st.columns(5) # 手机端建议分两列，这里先用5列展示
            for i, (idx, row) in enumerate(top_10.iterrows()):
                with cols[i % 5]:
                    color = "green" if row['Change_Value'] > 0 else "red"
                    # 使用 Markdown 创建一个带颜色的大链接
                    st.markdown(f"**[{row['Ticker']}]({row['YahooURL']})**")
                    st.markdown(f"<span style='color:{color}'>{row['Change_Value']}%</span>", unsafe_allow_html=True)

            # 背景扫描 (Top 5)
            with st.expander("查看核心公司业务背景"):
                tickers = df['Ticker'].head(5).tolist()
                with ThreadPoolExecutor(max_workers=5) as executor:
                    descriptions = list(executor.map(self.get_desc, tickers))
                for t, d in zip(tickers, descriptions):
                    st.write(f"**{t}**: {d}")

            # 绘图
            fig = px.treemap(
                df,
                path=[px.Constant(mode), '板块汉化', 'Ticker'],
                values=pd.Series([1]*len(df)),
                color='Change_Value',
                color_continuous_scale='RdYlGn',
                range_color=[-4, 4],
                custom_data=['YahooURL', 'Price', target_col if 'target_col' in locals() else 'Change_Value']
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.warning("数据抓取中或筛选结果为空，请稍后...")

if __name__ == "__main__":
    app = FinalDiagnosticApp()
    app.run()