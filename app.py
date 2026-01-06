import streamlit as st
import pandas as pd
import plotly.express as px
from finvizfinance.screener.overview import Overview
from finvizfinance.quote import finvizfinance
from translate import Translator
from concurrent.futures import ThreadPoolExecutor

# 1. 页面基本配置 (移动端优化)
st.set_page_config(page_title="美股深度复盘", layout="wide")

class IntegratedStockApp:
    def __init__(self):
        # 整合：板块汉化碎片
        self.sector_map = {
            'Technology': '信息技术', 'Financial': '金融服务', 'Healthcare': '医疗保健',
            'Consumer Cyclical': '可选消费', 'Industrials': '工业制造', 'Communication Services': '通讯服务',
            'Consumer Defensive': '必需消费', 'Energy': '能源石油', 'Real Estate': '房地产',
            'Utilities': '公用事业', 'Basic Materials': '基础材料'
        }
        # 整合：翻译引擎碎片
        try:
            self.translator = Translator(to_lang="zh")
        except:
            self.translator = None

    @st.cache_data(ttl=3600)
    def fetch_data(_self, mode):
        # 整合：Finviz抓取与异常降级碎片
        fino = Overview()
        try:
            if mode == "S&P 500":
                fino.set_filter(filters_dict={'Index': 'S&P 500'})
            else:
                fino.set_filter(filters_dict={'Market Cap.': '+Mid (over $2bln)', 'Average Volume': 'Over 500K'})
            df = fino.screener_view()
        except:
            return pd.DataFrame()
        
        if df is None or df.empty: return pd.DataFrame()
        
        # 整合：数据清洗与权重过滤碎片 (取前60只防止白屏)
        df = df.head(60).copy()
        df['涨跌'] = df['Change'].apply(lambda x: float(str(x).replace('%','')) if x else 0.0)
        df['板块'] = df['Sector'].map(_self.sector_map).fillna(df['Sector'])
        df['URL'] = "https://finance.yahoo.com/quote/" + df['Ticker']
        return df

    def get_zh_desc(self, ticker):
        # 整合：业务背景深度扫描碎片
        try:
            stock = finvizfinance(ticker)
            desc_en = stock.ticker_description()
            if not desc_en: return "暂无背景描述"
            short_en = desc_en[:120]
            if self.translator:
                return self.translator.translate(short_en)
            return f"[英] {short_en}"
        except:
            return "描述抓取中..."

    def run(self):
        st.title("🚀 美股全功能复盘看板")
        
        # 侧边栏控制
        mode = st.sidebar.radio("选择模式", ["S&P 500", "今日强势股"])
        
        with st.spinner('正在同步全球金融碎片数据...'):
            df = self.fetch_data(mode)

        if not df.empty:
            # 整合：异步多线程翻译碎片
            tickers = df['Ticker'].head(20).tolist()
            with ThreadPoolExecutor(max_workers=5) as executor:
                descriptions = list(executor.map(self.get_zh_desc, tickers))
            
            desc_map = dict(zip(tickers, descriptions))
            df['背景'] = df['Ticker'].map(desc_map).fillna("点击跳转查看详情")

            # 整合：交互式热力图与点击跳转逻辑
            fig = px.treemap(
                df,
                path=[px.Constant(mode), '板块', 'Ticker'],
                values=pd.Series([1]*len(df)),
                color='涨跌',
                color_continuous_scale='RdYlGn',
                range_color=[-3, 3],
                custom_data=['URL', 'Price', 'Change', '背景']
            )

            fig.update_traces(
                hovertemplate="<b>%{label}</b><br>现价: %{customdata[1]}<br>涨跌: %{customdata[2]}<br>背景: %{customdata[3]}"
            )

            # 手机端自适应显示
            st.plotly_chart(fig, use_container_width=True)
            
            # 整合：详细清单展示
            st.dataframe(df[['Ticker', 'Price', 'Change', '板块']], use_container_width=True)
        else:
            st.warning("数据抓取超时，请尝试刷新。")

if __name__ == "__main__":
    app = IntegratedStockApp()
    app.run()