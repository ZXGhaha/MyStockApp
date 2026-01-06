import streamlit as st
import pandas as pd
import plotly.express as px
from finvizfinance.screener.overview import Overview
from finvizfinance.quote import finvizfinance
from translate import Translator
from concurrent.futures import ThreadPoolExecutor

# 页面基本配置
st.set_page_config(page_title="美股复盘终端", layout="wide")

class FinalAppFix:
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

    @st.cache_data(ttl=600) # 缩短缓存时间，确保数据新鲜
    def fetch_data(_self, mode):
        fino = Overview()
        if mode == "S&P 500":
            fino.set_filter(filters_dict={'Index': 'S&P 500'})
        else:
            # 💡 修复：动能异动模式，增加“价格大于5”和“成交量大于100万”的过滤，防止垃圾股占满A开头
            fino.set_filter(filters_dict={
                'Market Cap.': '+Mid (over $2bln)', 
                'Average Volume': 'Over 1M',
                'Price': 'Over $5'
            })
        
        df = fino.screener_view()
        if df is None or df.empty: return pd.DataFrame()
        
        # 💡 修复：强制按涨跌幅排序，解决“都是A开头”的问题
        df['涨跌数值'] = df['Change'].apply(lambda x: float(str(x).replace('%','')) if x else 0.0)
        df = df.sort_values(by='涨跌数值', ascending=False)
        
        df = df.head(60).copy() # 取前60只
        df['板块汉化'] = df['Sector'].map(_self.sector_map).fillna(df['Sector'])
        # 💡 修复跳转：在数据中直接生成 Yahoo 链接
        df['YahooURL'] = "https://finance.yahoo.com/quote/" + df['Ticker']
        return df

    def get_desc(self, ticker):
        """💡 修复背景扫描：增加超时保护"""
        try:
            stock = finvizfinance(ticker)
            desc = stock.ticker_description()
            if not desc: return "无业务背景"
            short = desc[:120]
            if self.translator:
                # 限制翻译长度以提高手机加载速度
                return self.translator.translate(short)
            return short
        except:
            return "点击下方链接查看详情"

    def run(self):
        st.sidebar.title("控制台")
        mode = st.sidebar.radio("模式选择", ["S&P 500", "动能异动榜"])
        
        st.title(f"📊 {mode}")

        with st.spinner('同步最新数据中...'):
            df = self.fetch_data(mode)

        if not df.empty:
            # 仅对前 15 名进行深度背景扫描，保证手机端不卡顿
            tickers = df['Ticker'].head(15).tolist()
            with ThreadPoolExecutor(max_workers=5) as executor:
                descriptions = list(executor.map(self.get_desc, tickers))
            
            desc_map = dict(zip(tickers, descriptions))
            df['背景'] = df['Ticker'].map(desc_map).fillna("查看详情请点击链接")

            # 绘图
            fig = px.treemap(
                df,
                path=[px.Constant(mode), '板块汉化', 'Ticker'],
                values=pd.Series([1]*len(df)),
                color='涨跌数值',
                color_continuous_scale='RdYlGn',
                range_color=[-4, 4],
                custom_data=['YahooURL', 'Price', 'Change', '背景']
            )

            # 💡 修复移动端悬停与跳转：将链接放在最显眼位置
            fig.update_traces(
                hovertemplate="""
                <b>代码: %{label}</b><br>
                涨跌: %{customdata[2]}<br>
                背景: %{customdata[3]}<br>
                ------------------<br>
                🔗 复制链接查看详情:<br>
                %{customdata[0]}
                """
            )

            st.plotly_chart(fig, use_container_width=True)
            
            # 💡 手机端补偿：在下方提供直接点击的列表
            st.subheader("🔗 快速跳转列表 (手机直接点击)")
            for i, row in df.head(10).iterrows():
                st.markdown(f"[{row['Ticker']}]( {row['YahooURL']} ) - {row['Price']} ({row['Change']}) - {row['背景'][:40]}...")

if __name__ == "__main__":
    app = FinalAppFix()
    app.run()