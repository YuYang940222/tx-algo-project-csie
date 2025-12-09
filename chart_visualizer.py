"""
圖表視覺化模組 - TradingView 風格版
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from typing import Dict, List, Optional

class ChartVisualizer:
    def __init__(self, theme: str = 'dark'):
        self.theme = theme
        self.colors = {
            'background': '#131722', # TradingView 經典深色背景
            'plot_bg': '#131722',
            'text': '#d1d4dc',
            'grid': '#363c4e',       # 深色格線
            'up_candle': '#ef5350',  # 台股紅漲 (若習慣美股綠漲可改 #26a69a)
            'down_candle': '#26a69a',# 台股綠跌 (若習慣美股紅跌可改 #ef5350)
            'volume_up': '#ef5350',
            'volume_down': '#26a69a',
            'support': '#2962ff',    # 藍色支撐
            'resistance': '#e91e63', # 粉色壓力
        }
    
    def create_trendline_chart(self, df: pd.DataFrame, trendline_analysis: Dict, max_lines: int = 3) -> go.Figure:
        """建立 TradingView 風格的主圖表"""
        if df is None or len(df) == 0:
            return None
            
        # 創建子圖 (價格 + 成交量)
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02, # 讓兩張圖靠更近
            row_heights=[0.8, 0.2],
            specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
        )
        
        # 1. K線圖 (Candlestick)
        fig.add_trace(
            go.Candlestick(
                x=df['datetime'],
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                name='Price',
                increasing_line_color=self.colors['up_candle'],
                decreasing_line_color=self.colors['down_candle'],
                increasing_fillcolor=self.colors['up_candle'],
                decreasing_fillcolor=self.colors['down_candle'],
                showlegend=False
            ),
            row=1, col=1
        )
        
        # 2. 成交量 (Volume) - 根據漲跌變色
        colors = [self.colors['volume_up'] if c >= o else self.colors['volume_down'] 
                 for c, o in zip(df['close'], df['open'])]
        
        fig.add_trace(
            go.Bar(
                x=df['datetime'],
                y=df['volume'],
                marker_color=colors,
                name='Volume',
                showlegend=False,
                opacity=0.5 # 讓成交量稍微透明，不搶眼
            ),
            row=2, col=1
        )

        # 3. 繪製趨勢線
        self._add_trendlines(fig, trendline_analysis, df, max_lines)
        
        # 4. 繪製突破點
        self._add_breakouts(fig, trendline_analysis['breakouts'])

        # 更新 Layout 設定 (關鍵：TradingView 風格)
        fig.update_layout(
            plot_bgcolor=self.colors['plot_bg'],
            paper_bgcolor=self.colors['background'],
            font=dict(color=self.colors['text'], family="Roboto, sans-serif"),
            margin=dict(l=10, r=10, t=30, b=10), # 縮小邊距
            height=700,
            xaxis_rangeslider_visible=False, # 隱藏預設的 rangeslider，因為我們自己控制縮放
            hovermode='x unified', # 類似 TradingView 的十字游標
            dragmode='pan', # 預設為平移模式
        )
        
        # 設定 X 軸 (隱藏週末空窗需要更複雜的處理，這裡先用日期時間軸)
        fig.update_xaxes(
            showgrid=True, gridcolor=self.colors['grid'], gridwidth=1,
            linecolor=self.colors['grid'],
            showspikes=True, spikemode='across', spikesnap='cursor', # 十字線效果
            spikethickness=1, spikecolor='#555555',
            rangebreaks=[ dict(bounds=["sat", "mon"]) ] # 嘗試隱藏週末 (對期貨很有用)
        )
        
        fig.update_yaxes(
            showgrid=True, gridcolor=self.colors['grid'], gridwidth=1,
            linecolor=self.colors['grid'],
            side='right', # 價格軸在右邊 (TradingView 預設)
            showspikes=True, spikemode='across', spikesnap='cursor',
            spikethickness=1, spikecolor='#555555',
            row=1, col=1
        )
        
        fig.update_yaxes(
            showgrid=False, 
            side='right',
            row=2, col=1
        )

        return fig

    def _add_trendlines(self, fig, analysis, df, max_lines):
        """繪製延伸趨勢線"""
        # 輔助函式：計算兩點連線
        # 為了簡化，直接畫出線段。若要無限延伸，需要計算斜率並推算邊界
        # 這裡僅畫出分析範圍內的線
        
        def plot_lines(lines, color, name_prefix):
            count = 0
            for line in lines:
                if count >= max_lines: break
                
                # 取得線段的起點和終點
                x_coords = [p[1] for p in line['points']] # 時間
                y_coords = [p[2] for p in line['points']] # 價格
                
                # 畫線
                fig.add_trace(
                    go.Scatter(
                        x=[line['start_point'][1], line['end_point'][1]], 
                        y=[line['start_point'][2], line['end_point'][2]],
                        mode='lines',
                        line=dict(color=color, width=2),
                        name=f'{name_prefix} ({line["touches"]} touches)',
                        showlegend=True
                    ),
                    row=1, col=1
                )
                count += 1

        if analysis:
            plot_lines(analysis['support_lines'], self.colors['support'], 'Support')
            plot_lines(analysis['resistance_lines'], self.colors['resistance'], 'Resistance')

    def _add_breakouts(self, fig, breakouts):
        """標記突破點"""
        for bk in breakouts:
            symbol = 'triangle-up' if bk['direction'] == 'bullish_breakout' else 'triangle-down'
            color = '#00ff00' if bk['direction'] == 'bullish_breakout' else '#ff0000'
            
            fig.add_trace(
                go.Scatter(
                    x=[bk['datetime']],
                    y=[bk['price']],
                    mode='markers',
                    marker=dict(symbol=symbol, size=12, color=color, line=dict(width=2, color='white')),
                    name='Breakout',
                    showlegend=False
                ),
                row=1, col=1
            )

def create_metric_cards_html(metrics: Dict) -> str:
    """產生上方數據卡的 HTML"""
    if not metrics: return ""
    
    p_change = metrics.get('price_change', 0)
    color = "#ef5350" if p_change > 0 else "#26a69a" # 紅漲綠跌
    
    return f"""
    <div style="display: flex; gap: 20px; margin-bottom: 20px;">
        <div class="metric-container">
            <div class="metric-label">當前價格</div>
            <div class="metric-value">{metrics['current_price']:.0f}</div>
        </div>
        <div class="metric-container">
            <div class="metric-label">漲跌幅</div>
            <div class="metric-value" style="color: {color}">
                {metrics['price_change']:+.0f} ({metrics['price_change_pct']:+.2f}%)
            </div>
        </div>
        <div class="metric-container">
            <div class="metric-label">最高價</div>
            <div class="metric-value">{metrics['period_high']:.0f}</div>
        </div>
        <div class="metric-container">
            <div class="metric-label">最低價</div>
            <div class="metric-value">{metrics['period_low']:.0f}</div>
        </div>
        <div class="metric-container">
            <div class="metric-label">資料筆數</div>
            <div class="metric-value">{metrics['data_points']}</div>
        </div>
    </div>
    """