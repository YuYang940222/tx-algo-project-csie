"""
圖表視覺化模組 (修正版：支援中文欄位自動對應與 K 線修復)
Author: Modified for Project Compliance
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from typing import Dict, List, Optional

class ChartVisualizer:
    """
    圖表視覺化器類別，負責創建交易圖表
    """
    
    def __init__(self, theme: str = 'dark'):
        self.theme = theme
        self.colors = self._get_color_scheme()
        
    def _get_color_scheme(self) -> Dict[str, str]:
        """設定配色方案 (台股習慣：紅漲綠跌)"""
        if self.theme == 'dark':
            return {
                'background': '#131722',      # 背景色
                'plot_bg': '#131722',         # 繪圖區背景
                'text': '#d1d4dc',            # 文字顏色
                'grid': '#1e222d',            # 格線顏色
                'up_candle': '#ff5252',       # 漲 (紅)
                'down_candle': '#00e676',     # 跌 (綠)
                'volume_up': 'rgba(255, 82, 82, 0.5)',
                'volume_down': 'rgba(0, 230, 118, 0.5)',
                'support': '#00e676',         # 支撐線
                'resistance': '#ff5252',      # 壓力線
                'breakout': '#ff9800'         # 突破點
            }
        else:
            return {
                'background': '#ffffff',
                'plot_bg': '#ffffff',
                'text': '#000000',
                'grid': '#f0f3fa',
                'up_candle': '#ff5252',
                'down_candle': '#00e676',
                'volume_up': 'rgba(255, 82, 82, 0.5)',
                'volume_down': 'rgba(0, 230, 118, 0.5)',
                'support': '#00ff00',
                'resistance': '#ff0000',
                'breakout': '#ff9800'
            }

    def _process_data(self, df_in: pd.DataFrame) -> pd.DataFrame:
        """
        內部處理：標準化欄位名稱並確保數據為數值
        這可以解決 'KeyError: datetime' 和 K 線畫不出來的問題
        """
        df = df_in.copy()
        
        # 1. 中文欄位對照表 (根據您的 kline_60min.TXT)
        mapping = {
            '日期': 'date', 'Date': 'date',
            '時間': 'time', 'Time': 'time',
            '開盤': 'open', 'Open': 'open',
            '最高': 'high', 'High': 'high',
            '最低': 'low', 'Low': 'low',
            '收盤': 'close', 'Close': 'close',
            '成交量': 'volume', 'Volume': 'volume'
        }
        df.rename(columns=mapping, inplace=True)

        # 2. 處理時間 (如果日期和時間分開，將其合併)
        try:
            if 'datetime' not in df.columns:
                if 'date' in df.columns and 'time' in df.columns:
                    # 合併 Date 和 Time
                    df['datetime'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str))
                elif 'date' in df.columns:
                    df['datetime'] = pd.to_datetime(df['date'])
            else:
                df['datetime'] = pd.to_datetime(df['datetime'])
        except Exception as e:
            st.error(f"時間格式處理錯誤: {e}")

        # 3. 強制轉型為數字 (解決 '文字型數字' 導致圖表空白的問題)
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 移除含有 NaN 的壞資料
        df.dropna(subset=[c for c in numeric_cols if c in df.columns], inplace=True)
        
        return df

    def create_chart(self, df: pd.DataFrame, support_lines: List[dict] = None, 
                    resistance_lines: List[dict] = None, breakouts: List[dict] = None) -> go.Figure:
        """
        主要繪圖方法：繪製 K 線、成交量與趨勢線
        """
        if df is None or df.empty:
            return go.Figure()

        # --- 步驟 1: 資料前處理 ---
        df = self._process_data(df)
        if df.empty:
            return go.Figure()

        # --- 步驟 2: 建立無間隙座標系統 (使用 Index) ---
        # 這能讓 K 線緊密排列，消除週末空隙
        df = df.reset_index(drop=True)
        df['x_idx'] = df.index  # 使用 0, 1, 2... 作為 X 軸

        # 建立 時間 -> Index 的查找表 (用於畫趨勢線)
        time_map = {pd.Timestamp(dt): idx for idx, dt in zip(df['x_idx'], df['datetime'])}

        # 設定 X 軸刻度顯示 (只顯示部分日期，避免擁擠)
        tick_vals = df['x_idx'][::max(1, len(df)//10)]
        tick_text = [dt.strftime('%m-%d %H:%M') for dt in df.iloc[tick_vals]['datetime']]

        # --- 步驟 3: 設定圖表佈局 (K線與成交量) ---
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.8, 0.2],
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )

        # 繪製 K 線 (Candlestick)
        fig.add_trace(
            go.Candlestick(
                x=df['x_idx'],
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                name='K線',
                increasing_line_color=self.colors['up_candle'],
                decreasing_line_color=self.colors['down_candle'],
                increasing_fillcolor=self.colors['up_candle'],
                decreasing_fillcolor=self.colors['down_candle']
            ), row=1, col=1
        )

        # 繪製成交量 (Volume)
        # 判斷顏色：收盤 >= 開盤 為紅，否則為綠
        colors_vol = [
            self.colors['volume_up'] if c >= o else self.colors['volume_down']
            for c, o in zip(df['close'], df['open'])
        ]
        
        fig.add_trace(
            go.Bar(
                x=df['x_idx'], y=df['volume'],
                name='成交量', marker_color=colors_vol, showlegend=False
            ), row=2, col=1
        )

        # --- 步驟 4: 繪製趨勢線 (座標轉換) ---
        # 因為 X 軸改成了 Index，所以必須把趨勢線的時間也轉成 Index
        def plot_lines(lines, color, name):
            if not lines: return
            for i, line in enumerate(lines):
                pts = line.get('points', [])
                if len(pts) < 2: continue
                
                # 取出頭尾兩點
                p1, p2 = pts[0], pts[-1]
                
                # 嘗試轉換時間
                try:
                    dt1 = pd.Timestamp(p1[1])
                    dt2 = pd.Timestamp(p2[1])
                    
                    idx1 = time_map.get(dt1)
                    idx2 = time_map.get(dt2)
                    
                    # 只有當兩個點都在目前畫面範圍內才畫
                    if idx1 is not None and idx2 is not None:
                        fig.add_trace(
                            go.Scatter(
                                x=[idx1, idx2],
                                y=[float(p1[2]), float(p2[2])],
                                mode='lines',
                                line=dict(color=color, width=2),
                                name=f'{name} {i+1}',
                                legendgroup=name,
                                showlegend=(i==0)
                            ), row=1, col=1
                        )
                except Exception:
                    continue

        if support_lines:
            plot_lines(support_lines, self.colors['support'], '支撐線')
        if resistance_lines:
            plot_lines(resistance_lines, self.colors['resistance'], '壓力線')

        # --- 步驟 5: 標記突破點 ---
        if breakouts:
            bk_x = []
            bk_y = []
            bk_sym = []
            for b in breakouts:
                try:
                    dt = pd.Timestamp(b['datetime'])
                    idx = time_map.get(dt)
                    if idx is not None:
                        bk_x.append(idx)
                        bk_y.append(float(b['price']))
                        bk_sym.append('triangle-up' if b['direction'] == 'up' else 'triangle-down')
                except: continue
            
            if bk_x:
                fig.add_trace(
                    go.Scatter(
                        x=bk_x, y=bk_y, mode='markers',
                        marker=dict(symbol=bk_sym, size=12, color=self.colors['breakout'], line=dict(width=1, color='white')),
                        name='突破訊號'
                    ), row=1, col=1
                )

        # --- 步驟 6: 樣式調整 (TradingView 風格) ---
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor=self.colors['background'],
            plot_bgcolor=self.colors['plot_bg'],
            margin=dict(l=10, r=60, t=30, b=10),
            xaxis_rangeslider_visible=False, # 隱藏下方 Slider
            hovermode='x unified',           # 統一游標
            xaxis=dict(
                tickmode='array', tickvals=tick_vals, ticktext=tick_text,
                gridcolor=self.colors['grid'], type='linear'
            ),
            yaxis=dict(
                gridcolor=self.colors['grid'], side='right', zeroline=False
            ),
            yaxis2=dict(
                gridcolor=self.colors['grid'], side='right', zeroline=False, showticklabels=False
            ),
            legend=dict(orientation="h", y=1.02, x=0)
        )

        return fig

def create_metric_cards_html(metrics: Dict) -> str:
    """
    創建指標卡片 HTML (保持功能不變，僅微調顏色)
    """
    price_change = metrics.get('price_change', 0)
    change_color = "#ff5252" if price_change >= 0 else "#00e676" # 紅漲綠跌
    
    html = f"""
    <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px;">
        <div style="flex: 1; min-width: 150px; background-color: #1e222d; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39;">
            <div style="color: #787b86; font-size: 12px; margin-bottom: 5px;">當前價格</div>
            <div style="color: #d1d4dc; font-size: 24px; font-weight: bold;">{metrics['current_price']:.0f}</div>
            <div style="color: {change_color}; font-size: 14px;">
                {metrics['price_change']:+.0f} ({metrics['price_change_pct']:+.2f}%)
            </div>
        </div>
        <div style="flex: 1; min-width: 150px; background-color: #1e222d; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39;">
            <div style="color: #787b86; font-size: 12px; margin-bottom: 5px;">期間高點</div>
            <div style="color: #d1d4dc; font-size: 24px; font-weight: bold;">{metrics['period_high']:.0f}</div>
        </div>
        <div style="flex: 1; min-width: 150px; background-color: #1e222d; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39;">
            <div style="color: #787b86; font-size: 12px; margin-bottom: 5px;">期間低點</div>
            <div style="color: #d1d4dc; font-size: 24px; font-weight: bold;">{metrics['period_low']:.0f}</div>
        </div>
        <div style="flex: 1; min-width: 150px; background-color: #1e222d; padding: 15px; border-radius: 8px; border: 1px solid #2a2e39;">
            <div style="color: #787b86; font-size: 12px; margin-bottom: 5px;">總成交量</div>
            <div style="color: #d1d4dc; font-size: 24px; font-weight: bold;">{metrics['total_volume']:,.0f}</div>
        </div>
    </div>
    """
    return html