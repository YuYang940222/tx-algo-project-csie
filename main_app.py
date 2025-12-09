"""
TX期貨交易儀表板 - TradingView 風格版
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import os
import sys

# 導入模組
try:
    from data_loader import DataLoader, calculate_basic_metrics
    from trendline_detector import TrendlineBreakoutDetector
    from chart_visualizer import ChartVisualizer, create_metric_cards_html
except ImportError as e:
    st.error(f"無法導入模組: {e}")
    st.stop()

# 頁面配置 (使用寬螢幕模式以達到 TradingView 效果)
st.set_page_config(
    page_title="專業期貨分析 - TradingView 風格",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 樣式優化 (更接近看盤軟體)
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stApp {
        background-color: #0e1117;
    }
    /* 調整邊距，讓圖表更大 */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    /* 指標卡片樣式 */
    .metric-container {
        background-color: #1c1c21;
        padding: 10px;
        border-radius: 4px;
        border-left: 4px solid #2962ff;
    }
    .metric-label { font-size: 0.8rem; color: #b2b5be; }
    .metric-value { font-size: 1.2rem; font-weight: 600; color: #ffffff; }
</style>
""", unsafe_allow_html=True)

class TradingDashboard:
    def __init__(self):
        self.data_loader = DataLoader()
        self.chart_visualizer = ChartVisualizer(theme='dark')
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        if 'data' not in st.session_state:
            st.session_state.data = None
        if 'trendline_analysis' not in st.session_state:
            st.session_state.trendline_analysis = None
    
    def render_sidebar(self):
        with st.sidebar:
            st.caption("🚀 控制面板")
            
            # 1. 資料來源
            st.markdown("### 📂 資料來源")
            # 預設直接抓取 7652A_Hour.TXT
            default_file = "7652A_Hour.TXT"
            file_path = st.text_input("檔案路徑", value=default_file)
            
            if st.button("載入資料", type="primary"):
                self.load_data(file_path)

            # 2. 顯示設定 (解決 500 筆限制的關鍵)
            st.markdown("### 👁️ 顯示設定")
            
            # 計算最大可用資料量
            max_len = 10000
            if st.session_state.data is not None:
                max_len = len(st.session_state.data)
            
            # !!! 這裡將 max_value 改大，預設值也改大 !!!
            lookback_bars = st.slider(
                "顯示 K 棒數量",
                min_value=50, 
                max_value=max_len,  # 動態上限，可以讀取全部 9000+ 筆
                value=min(1000, max_len), # 預設顯示 1000 筆
                step=50,
                help="拖拉以查看更多歷史資料"
            )

            # 3. 技術分析參數
            with st.expander("⚙️ 技術指標參數"):
                swing_window = st.number_input("搖擺點視窗", value=5, min_value=2)
                min_touches = st.number_input("趨勢線接觸點", value=3, min_value=2)
                breakout_threshold = st.number_input("突破閥值(%)", value=0.3, step=0.1) / 100
            
            return {
                'lookback_bars': lookback_bars,
                'swing_window': swing_window,
                'min_touches': min_touches,
                'breakout_threshold': breakout_threshold,
                'max_trendlines': 5
            }

    def load_data(self, file_path):
        with st.spinner("正在讀取並分析資料..."):
            df = self.data_loader.load_from_text_file(file_path)
            if df is not None:
                st.session_state.data = df
                st.success(f"成功載入 {len(df)} 筆資料")
            else:
                st.session_state.data = None

    def run(self):
        settings = self.render_sidebar()
        
        # 標題區
        st.markdown("#### 📊 TX 期貨專業圖表 (TradingView Style)")
        
        if st.session_state.data is None:
            st.info(f"👈 請在左側確認檔案路徑並點擊「載入資料」。(預設讀取 {settings.get('file_path', '7652A_Hour.TXT')})")
            return

        # 取得要分析的資料切片 (根據 Slider 的數值)
        # 我們取最後 N 筆資料來分析，這樣才能看到最新的走勢
        lookback = settings['lookback_bars']
        df_display = st.session_state.data.tail(lookback).copy()
        
        # 計算指標
        metrics = calculate_basic_metrics(df_display)
        st.markdown(create_metric_cards_html(metrics), unsafe_allow_html=True)
        
        # 執行即時分析
        detector = TrendlineBreakoutDetector(
            swing_window=settings['swing_window'],
            min_touches=settings['min_touches'],
            breakout_threshold=settings['breakout_threshold'],
            lookback_bars=len(df_display) # 分析當前顯示的所有資料
        )
        
        st.session_state.trendline_analysis = detector.analyze(df_display)
        
        # 繪製主圖表
        fig = self.chart_visualizer.create_trendline_chart(
            df_display,
            st.session_state.trendline_analysis,
            max_lines=settings['max_trendlines']
        )
        
        if fig:
            # 使用 container width 充滿螢幕
            st.plotly_chart(fig, use_container_width=True, config={
                'scrollZoom': True, # 啟用滾輪縮放
                'displayModeBar': True,
                'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'] # 加入繪圖工具
            })
            
            # 顯示簡單的文字摘要
            analysis = st.session_state.trendline_analysis
            if analysis['breakouts']:
                last_bk = analysis['breakouts'][0]
                color = "green" if last_bk['direction'] == 'bullish_breakout' else "red"
                msg = "看漲突破" if last_bk['direction'] == 'bullish_breakout' else "看跌跌破"
                st.markdown(f"🚨 **最新訊號**: <span style='color:{color}'>{msg}</span> @ {last_bk['price']:.0f} ({last_bk['datetime']})", unsafe_allow_html=True)

if __name__ == "__main__":
    dashboard = TradingDashboard()
    dashboard.run()