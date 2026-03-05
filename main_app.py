import streamlit as st
import pandas as pd
from quant_analyzer import QuantAnalyzer

# 導入自定義模組
try:
    from data_loader import DataLoader, calculate_basic_metrics
    from trendline_detector import TrendlineBreakoutDetector
    from chart_visualizer import ChartVisualizer, create_metric_cards_html
except ImportError as e:
    st.error(f"無法導入模組: {e}")
    st.stop()

st.set_page_config(page_title="專業量化儀表板", page_icon="📈", layout="wide")

class TradingDashboard:
    def __init__(self):
        self.data_loader = DataLoader()
        self.chart_visualizer = ChartVisualizer(theme='dark')
        if 'data' not in st.session_state: 
            st.session_state.data = None

    def render_sidebar(self):
        with st.sidebar:
            st.title("🚀 控制面板")
            file_path = st.text_input("檔案路徑", value="7652A_Hour.TXT")
            if st.button("載入資料", type="primary"):
                df = self.data_loader.load_from_text_file(file_path)
                if df is not None:
                    st.session_state.data = df
                    st.success(f"成功載入 {len(df)} 筆資料")

            st.markdown("---")
            max_len = 9974 if st.session_state.data is None else len(st.session_state.data)
            lookback_bars = st.slider("顯示 K 棒數量", 50, max_len, min(1300, max_len), 50)

            with st.expander("⚙️ 技術指標參數"):
                swing_window = st.number_input("搖擺點視窗", value=5, min_value=2)
                min_touches = st.number_input("趨勢線接觸點", value=3, min_value=2)
                breakout_threshold = st.number_input("突破閥值(%)", 0.3, step=0.1) / 100
            
            return {
                'lookback_bars': lookback_bars,
                'swing_window': swing_window,
                'min_touches': min_touches,
                'breakout_threshold': breakout_threshold,
                'max_trendlines': 5
            }

    def run(self):
        settings = self.render_sidebar()
        st.markdown("#### 📊 TX 期貨量化分析 (TradingView Style)")
        
        if st.session_state.data is None:
            st.info("👈 請先點擊左側「載入資料」按鈕。")
            return

        # 1. 切片資料
        df_display = st.session_state.data.tail(settings['lookback_bars']).copy()
        
        # 2. 顯示指標卡片
        metrics = calculate_basic_metrics(df_display)
        st.markdown(create_metric_cards_html(metrics), unsafe_allow_html=True)
        
        # 3. 執行偵測 (每次 run 都重新計算，解決點數累加問題)
        detector = TrendlineBreakoutDetector(
            swing_window=settings['swing_window'],
            min_touches=settings['min_touches'],
            breakout_threshold=settings['breakout_threshold'],
            lookback_bars=len(df_display)
        )
        analysis = detector.analyze(df_display)
        
        # 4. 量化分析 (R2 與 勝率)
        q_stats = QuantAnalyzer.run_regression_analysis(df_display, window=len(df_display))
        win_rate = QuantAnalyzer.backtest_breakout_winrate(st.session_state.data, analysis['breakouts'])

        # 5. 更新側邊欄驗證報告
        with st.sidebar:
            st.divider()
            st.header("🔬 量化驗證報告")
            c1, c2 = st.columns(2)
            c1.metric("歷史勝率", f"{win_rate:.1f}%")
            c2.metric("趨勢信心 (R²)", f"{q_stats['confidence']:.1f}%")
            st.caption(f"當前視窗偵測到 {len(analysis['breakouts'])} 個訊號點")

        # 6. 主圖表渲染
        fig = self.chart_visualizer.create_trendline_chart(df_display, analysis, settings['max_trendlines'])
        if fig:
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

if __name__ == "__main__":
    TradingDashboard().run()