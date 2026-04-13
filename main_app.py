import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from quant_analyzer import QuantAnalyzer

# 導入自定義模組
try:
    from data_loader import DataLoader, calculate_basic_metrics
    from trendline_detector import TrendlineBreakoutDetector
    from chart_visualizer import ChartVisualizer, create_metric_cards_html
except ImportError as e:
    st.error(f"無法導入模組: {e}")
    st.stop()

# 設定網頁標題與寬度
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
            
            st.markdown("---")
            st.subheader("💰 資金與部位設定")
            
            symbol = st.selectbox("切換商品", ["大台指 (TX)", "小台指 (MTX)"])
            
            if symbol == "大台指 (TX)":
                self.multiplier = 200
                default_capital = 167000
            else:
                self.multiplier = 50
                default_capital = 41750
            
            self.contracts = st.number_input("欲買口數", min_value=1, value=1, step=1)
            # 💡 修正：將「單口保證金」改為「總投入資金」，這樣才能正確計算整體帳戶槓桿
            self.total_capital = st.number_input(f"帳戶總投入資金 (NTD)", min_value=10000, value=default_capital, step=10000)
            
            st.markdown("---")
            st.subheader("🛡️ 單次回測風險參數")
            self.stop_loss = st.number_input("停損點數 (Stop Loss)", min_value=10, max_value=200, value=30, step=10)
            self.take_profit = st.number_input("停利點數 (Take Profit)", min_value=10, max_value=500, value=60, step=10)
            
            self.trade_cost = 1.0 
            st.caption(f"註：後台已扣除單邊 {self.trade_cost} 點交易成本 (含規費與滑點)")
            
            with st.expander("⚙️ 技術指標參數 (已固定)", expanded=True):
                swing_window = 20
                min_touches = 3
                breakout_threshold_display = 0.25
                breakout_threshold = breakout_threshold_display / 100
                
                st.markdown(f"**搖擺點視窗:** {swing_window}")
                st.markdown(f"**趨勢線接觸點:** {min_touches}")
                st.markdown(f"**突破閥值(%):** {breakout_threshold_display}")
            
            return {
                'lookback_bars': lookback_bars,
                'swing_window': swing_window,
                'min_touches': min_touches,
                'breakout_threshold': breakout_threshold,
                'max_trendlines': 5
            }

    def run(self):
        settings = self.render_sidebar()
        
        st.markdown("#### 📊 TX/MTX 期貨量化分析與最佳化")
        
        if st.session_state.data is None:
            st.info("👈 請先點擊左側「載入資料」按鈕。")
            return

        # 1. 切片資料
        df_display = st.session_state.data.tail(settings['lookback_bars']).copy()
        
        # 2. 顯示指標卡片
        metrics = calculate_basic_metrics(df_display)
        st.markdown(create_metric_cards_html(metrics), unsafe_allow_html=True)
        
        # 3. 資料讀取驗證區塊
        with st.expander("🔍 資料讀取驗證 (頭、中、尾 3組檢查點)", expanded=False):
            if len(df_display) >= 3:
                b1 = df_display.iloc[0]
                b2 = df_display.iloc[len(df_display) // 2]
                b3 = df_display.iloc[-1]
                
                col1, col2, col3 = st.columns(3)
                col1.info(f"**🟢 第 1 筆 (最舊起點)**\n\n時間: `{b1['datetime']}`\n\n開: {b1['open']} | 收: {b1['close']}")
                col2.warning(f"**🟡 第 {len(df_display)//2 + 1} 筆 (中間點)**\n\n時間: `{b2['datetime']}`\n\n開: {b2['open']} | 收: {b2['close']}")
                col3.error(f"**🔴 第 {len(df_display)} 筆 (最新終點)**\n\n時間: `{b3['datetime']}`\n\n開: {b3['open']} | 收: {b3['close']}")
        
        # 4. 執行偵測
        detector = TrendlineBreakoutDetector(
            swing_window=settings['swing_window'],
            min_touches=settings['min_touches'],
            breakout_threshold=settings['breakout_threshold'],
            lookback_bars=len(df_display)
        )
        analysis = detector.analyze(df_display)

        # ====== 💡 修正：計算真實槓桿 ======
        current_price = metrics['current_price']
        notional_value = current_price * self.multiplier * self.contracts  # 契約總價值 (名目本金)
        
        # 槓桿 = 總部位價值 / 總投入資金
        leverage = notional_value / self.total_capital if self.total_capital > 0 else 0

        # 顯示槓桿
        with st.sidebar:
            st.divider()
            st.subheader("⚖️ 帳戶風險與水位")
            
            # 如果資金連原始保證金都付不起，亮紅燈警告
            min_required = 167000 * self.contracts if self.multiplier == 200 else 41750 * self.contracts
            if self.total_capital < min_required:
                st.error(f"⚠️ 資金不足！{self.contracts} 口至少需要 {min_required:,} 元")
            
            st.metric(
                "當前實際槓桿", 
                f"{leverage:.2f} 倍", 
                help=f"算法: (最新收盤價 {current_price:,.0f} × 乘數 {self.multiplier} × 口數 {self.contracts}) ÷ 帳戶總資金 {self.total_capital:,.0f}"
            )

        tab_main, tab_opt = st.tabs(["📈 主圖表與單次回測", "🔬 停損停利最佳化 (多空分離)"])

        # ==========================================
        # 分頁 1：主圖表與單次回測
        # ==========================================
        with tab_main:
            report = QuantAnalyzer.backtest_breakout_winrate(
                df=st.session_state.data, 
                breakouts=analysis['breakouts'],
                stop_loss=self.stop_loss,
                take_profit=self.take_profit,
                cost=self.trade_cost
            )

            # 💡 修正：ROI 算法改用「總投入資金」當分母
            def calc_ntd_and_roi(exp_points):
                exp_ntd = exp_points * self.multiplier * self.contracts
                roi = (exp_ntd / self.total_capital) * 100 if self.total_capital > 0 else 0
                return exp_ntd, roi

            exp_ntd, exp_roi = calc_ntd_and_roi(report['expectancy'])
            long_exp_ntd, long_exp_roi = calc_ntd_and_roi(report['long_exp'])
            short_exp_ntd, short_exp_roi = calc_ntd_and_roi(report['short_exp'])

            with st.sidebar:
                st.divider()
                st.header(f"單次回測報告 (SL:{self.stop_loss}/TP:{self.take_profit})")
                
                s_tab1, s_tab2, s_tab3 = st.tabs(["📊 整體", "📈 多", "📉 空"])
                
                with s_tab1:
                    c1, c2 = st.columns(2)
                    c1.metric("整體勝率", f"{report['win_rate']:.1f}%")
                    c2.metric("單筆期望值", f"${exp_ntd:,.0f}", f"{exp_roi:+.2f}%")
                    st.caption(f"總訊號：{report['total_signals']} | 總淨利：${exp_ntd * report['total_signals']:,.0f}")
                
                with s_tab2:
                    c1, c2 = st.columns(2)
                    c1.metric("做多勝率", f"{report['long_win_rate']:.1f}%")
                    c2.metric("多軍期望值", f"${long_exp_ntd:,.0f}", f"{long_exp_roi:+.2f}%")
                    st.caption(f"做多訊號：{report['long_signals']} | 總淨利：${long_exp_ntd * report['long_signals']:,.0f}")
                
                with s_tab3:
                    c1, c2 = st.columns(2)
                    c1.metric("做空勝率", f"{report['short_win_rate']:.1f}%")
                    c2.metric("空軍期望值", f"${short_exp_ntd:,.0f}", f"{short_exp_roi:+.2f}%")
                    st.caption(f"做空訊號：{report['short_signals']} | 總淨利：${short_exp_ntd * report['short_signals']:,.0f}")

            fig = self.chart_visualizer.create_trendline_chart(df_display, analysis, settings['max_trendlines'])
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        # ==========================================
        # 分頁 2：參數最佳化 (支援多空分離)
        # ==========================================
        with tab_opt:
            st.markdown("### 🤖 自動尋找最佳參數高原")
            
            opt_direction = st.radio(
                "選擇要掃描的方向 (非常重要！多空特性通常不同)：", 
                ["📊 整體 (All)", "📈 只看做多 (Long Only)", "📉 只看做空 (Short Only)"], 
                horizontal=True
            )
            
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### 停損 (Stop Loss) 範圍")
                sl_start = st.number_input("SL 起始值", min_value=10, value=20, step=10)
                sl_end = st.number_input("SL 結束值", min_value=20, value=100, step=10)
                sl_step = st.number_input("SL 間隔", min_value=5, value=10, step=5)
            with col2:
                st.markdown("#### 停利 (Take Profit) 範圍")
                tp_start = st.number_input("TP 起始值", min_value=20, value=40, step=10)
                tp_end = st.number_input("TP 結束值", min_value=30, value=200, step=10)
                tp_step = st.number_input("TP 間隔", min_value=5, value=20, step=5)

            if st.button("🚀 開始多重回測掃描", type="primary", use_container_width=True):
                if not analysis['breakouts']:
                    st.warning("當前區間無突破訊號，無法最佳化。請增加 K 棒數量。")
                else:
                    with st.spinner("系統正在運算中，請稍候..."):
                        opt_results = []
                        
                        for sl in range(sl_start, sl_end + sl_step, sl_step):
                            for tp in range(tp_start, tp_end + tp_step, tp_step):
                                temp_report = QuantAnalyzer.backtest_breakout_winrate(
                                    df=st.session_state.data, 
                                    breakouts=analysis['breakouts'],
                                    stop_loss=sl,
                                    take_profit=tp,
                                    cost=self.trade_cost
                                )
                                
                                if "整體" in opt_direction:
                                    target_exp_points = temp_report['expectancy']
                                elif "做多" in opt_direction:
                                    target_exp_points = temp_report['long_exp']
                                elif "做空" in opt_direction:
                                    target_exp_points = temp_report['short_exp']
                                
                                exp_ntd = target_exp_points * self.multiplier * self.contracts
                                opt_results.append({
                                    'Stop Loss': sl,
                                    'Take Profit': tp,
                                    'Net Profit (NTD)': exp_ntd
                                })
                        
                        res_df = pd.DataFrame(opt_results)
                        pivot_df = res_df.pivot(index="Stop Loss", columns="Take Profit", values="Net Profit (NTD)")
                        
                        heatmap_fig = go.Figure(data=go.Heatmap(
                            z=pivot_df.values,
                            x=pivot_df.columns,  
                            y=pivot_df.index,    
                            colorscale='RdYlGn', 
                            zmid=0,              
                            texttemplate="$%{z:,.0f}", 
                            textfont={"size": 10},
                            hoverongaps=False
                        ))
                        
                        heatmap_fig.update_layout(
                            title=f"【{opt_direction}】期望值熱力圖 (NTD)",
                            xaxis_title="停利點數 (Take Profit)",
                            yaxis_title="停損點數 (Stop Loss)",
                            height=600,
                            margin=dict(l=50, r=50, t=50, b=50)
                        )
                        
                        st.success(f"✅ {opt_direction} 參數運算完成！")
                        st.plotly_chart(heatmap_fig, use_container_width=True)

if __name__ == "__main__":
    TradingDashboard().run()