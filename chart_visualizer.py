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
            'background': '#131722', 
            'plot_bg': '#131722',
            'text': '#d1d4dc',
            'grid': '#363c4e',       
            'up_candle': '#ef5350',  
            'down_candle': '#26a69a',
            'volume_up': '#ef5350',
            'volume_down': '#26a69a',
            'support': '#2962ff',    
            'resistance': '#e91e63', 
        }
    
    def create_trendline_chart(self, df: pd.DataFrame, trendline_analysis: Dict, max_lines: int = 3) -> go.Figure:
        if df is None or len(df) == 0:
            return None
            
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02, 
            row_heights=[0.8, 0.2],
            specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
        )
        
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
        
        colors = [self.colors['volume_up'] if c >= o else self.colors['volume_down'] 
                 for c, o in zip(df['close'], df['open'])]
        
        fig.add_trace(
            go.Bar(
                x=df['datetime'],
                y=df['volume'],
                marker_color=colors,
                name='Volume',
                showlegend=False,
                opacity=0.5 
            ),
            row=2, col=1
        )

        self._add_trendlines(fig, trendline_analysis, df, max_lines)
        self._add_breakouts(fig, trendline_analysis['breakouts'])

        fig.update_layout(
            plot_bgcolor=self.colors['plot_bg'],
            paper_bgcolor=self.colors['background'],
            font=dict(color=self.colors['text'], family="Roboto, sans-serif"),
            margin=dict(l=10, r=10, t=30, b=10), 
            height=700,
            xaxis_rangeslider_visible=False, 
            hovermode='x unified', 
            
            dragmode='pan',  
            newshape_line_color='yellow',  
            newshape_line_width=2,
            newshape_opacity=0.8 
        )
        
        fig.update_xaxes(
            showgrid=True, gridcolor=self.colors['grid'], gridwidth=1,
            linecolor=self.colors['grid'],
            showspikes=True, spikemode='across', spikesnap='cursor', 
            spikethickness=1, spikecolor='#555555',
            rangebreaks=[ dict(bounds=["sat", "mon"]) ] 
        )
        
        fig.update_yaxes(
            showgrid=True, gridcolor=self.colors['grid'], gridwidth=1,
            linecolor=self.colors['grid'],
            side='right', 
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
        def plot_lines(lines, color, name_prefix):
            count = 0
            for line in lines:
                if count >= max_lines: break
                
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

    def _add_breakouts(self, fig: go.Figure, breakouts: List[Dict]):
        if not breakouts:
            return

        bull_times, bull_prices = [], []
        bear_times, bear_prices = [], []

        for bk in breakouts:
            if 'bullish' in bk['direction']:
                bull_times.append(bk['datetime'])
                bull_prices.append(bk['price'])
            else:
                bear_times.append(bk['datetime'])
                bear_prices.append(bk['price'])

        if bull_times:
            fig.add_trace(go.Scatter(
                x=bull_times,
                y=bull_prices,
                mode='markers',
                marker=dict(
                    symbol='triangle-up', 
                    size=14, 
                    color='#00E676', 
                    line=dict(width=1, color='black')
                ),
                name='向上突破',
                hoverinfo='x+y'  
            ), row=1, col=1)

        if bear_times:
            fig.add_trace(go.Scatter(
                x=bear_times,
                y=bear_prices,
                mode='markers',
                marker=dict(
                    symbol='triangle-down', 
                    size=14, 
                    color='#FF5252', 
                    line=dict(width=1, color='black')
                ),
                name='向下突破',
                hoverinfo='x+y'  
            ), row=1, col=1)

def create_metric_cards_html(metrics: Dict) -> str:
    """產生上方數據卡的 HTML (已移除漲跌幅)"""
    if not metrics: return ""
    
    return f"""
    <div style="display: flex; gap: 20px; margin-bottom: 20px;">
        <div class="metric-container">
            <div class="metric-label">當前價格</div>
            <div class="metric-value">{metrics['current_price']:.0f}</div>
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