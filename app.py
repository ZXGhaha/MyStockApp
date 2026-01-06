import streamlit as st
import pandas as pd
import plotly.express as px
from finvizfinance.screener.overview import Overview
from finvizfinance.quote import finvizfinance
from translate import Translator
from concurrent.futures import ThreadPoolExecutor

# 页面配置：适配最新 Streamlit 版本
st.set_page_config(page_title="美股深度复盘终端", layout="wide")

class WebTerminalApp:
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
    def fetch_clean_data(_self, mode):
        fino = Overview()
        if mode == "S&P 500":
            fino.set_filter(filters_dict={'Index': 'S&P 500'})
        else:
            # 动能筛选：股价>5，成交量>1M，过滤掉A开头的低价死水股
            fino.set_filter(filters_dict={'Price': 'Over $5', 'Average Volume': 'Over 1M', 'Market Cap.': '+Mid (over $2bln)'})
        
        df = fino.screener_view()
        if df is None or df.empty: return pd.DataFrame()

        # --- 核心修复：强制数值化排序 ---
        def to_float(val):
            try:
                return float(str(val).replace('%', '').replace('+', '').strip())
            except:
                return 0.0

        # 寻找涨跌幅列（防偏移）
        change_col = next((c for c in df.columns if 'Change' in c), None)
        if change_col:
            df['Num_Change'] = df[change_col].apply(to_float)
            # 强制降序排列，确保“动能”在前
            df = df.sort_values(by='Num_Change', ascending=False)
        
        df = df.head(40).copy() # 取前40只精选
        df['ZH_Sector'] = df['Sector'].map(_self.sector_map).fillna(df['Sector'])
        df['URL'] = "https://finance.yahoo.com/quote/" + df['Ticker']
        return df

    def get_summary(self, ticker):
        """背景扫描：仅取首句，加速翻译"""
        try:
            stock = finvizfinance(ticker)
            desc = stock.ticker_description()
            if not desc: return "无业务描述"
            first_sent = desc.split('.')[0]
            return self.translator.translate(first_sent) if self.translator else first_sent
        except:
            return "点击下方按钮查看详情"

    def run(self):
        st.sidebar.title("💎 终端控制")
        mode = st.sidebar.radio("数据维度", ["今日动能榜", "S&P 500"])
        
        st.title(f"🚀 {mode} 全功能看板")
        
        with st.spinner('正在同步碎片功能并重构排序...'):
            df = self.fetch_clean_data(mode)

        if not df.empty:
            # 背景扫描（仅针对前12名，保证加载速度）
            top_list = df.head(12).tolist() if isinstance(df.head(12), list) else df['Ticker'].head(12).tolist()
            with ThreadPoolExecutor(max_workers=4) as executor:
                summaries = list(executor.map(self.get_summary, top_list))
            
            summary_map = dict(zip(top_list, summaries))
            df['Business'] = df['Ticker'].map(summary_map).fillna("实时动能个股")

            # 绘图：修复日志中的 width 警告
            fig = px.treemap(
                df,
                path=[px.Constant(mode), 'ZH_Sector', 'Ticker'],
                values=pd.Series([1]*len(df)),
                color='Num_Change',
                color_continuous_scale='RdYlGn',
                range_color=[-4, 4],
                custom_data=['URL', 'Price', 'Change', 'Business']
            )

            fig.update_traces(
                hovertemplate="<b>%{label}</b><br>涨幅: %{customdata[2]}<br>背景: %{customdata[3]}"
            )

            # 使用符合新版本要求的参数
            st.plotly_chart(fig, width='stretch')
            
            # --- 核心修复：手机端大按钮跳转 ---
            st.write("---")
            st.subheader("🎯 手机端点击跳转 (直接点击下方代码)")
            
            # 采用 2 列布局，方便单手操作
            cols = st.columns(2)
            for i, (idx, row) in enumerate(df.head(12).iterrows()):
                with cols[i % 2]:
                    # 使用 st.link_button 实现原生跳转
                    st.link_button(
                        label=f"{row['Ticker']} | {row['Change']} | {row['Price']}",
                        url=row['URL'],
                        use_container_width=True # 这里的参数在按钮中依然有效
                    )
                    st.caption(f"简介: {row['Business']}")
        else:
            st.error("无法获取实时行情，请尝试刷新。")

if __name__ == "__main__":
    app = WebTerminalApp()
    app.run()