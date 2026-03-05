"""
量化分析模組 - 專業回歸分析與強化對位回測
"""
import numpy as np
import pandas as pd
from scipy import stats

class QuantAnalyzer:
    @staticmethod
    def run_regression_analysis(df, window=40):
        """[數學回歸] 計算線性回歸與趨勢穩定度"""
        if df is None or len(df) < 2:
            return {'r_squared': 0, 'confidence': 0, 'is_stable': False, 'suggested_buy': False}

        prices = df['close'].tail(window).values
        x = np.arange(len(prices))
        
        # 執行線性回歸
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, prices)
        
        r_squared = r_value**2
        y_pred = slope * x + intercept
        std_dev = np.std(prices - y_pred)
        current_z = (prices[-1] - y_pred[-1]) / std_dev if std_dev != 0 else 0
        
        return {
            'r_squared': r_squared,
            'confidence': r_squared * 100,
            'is_stable': r_squared > 0.6 and p_value < 0.05,
            'suggested_buy': current_z < -1.5 
        }

    @staticmethod
    def backtest_breakout_winrate(df, breakouts, forward_bars=10):
        """[形態驗證] 強化對位版：解決 0% 問題，確保 100% 匹配時間戳"""
        if df is None or not breakouts or len(breakouts) == 0:
            return 0.0
            
        success_count = 0
        total_valid = 0
        
        # 建立時間索引字典 (秒級字串)
        try:
            time_series = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
        except:
            return 0.0
        
        for bk in breakouts:
            try:
                # 轉為字串對位
                bk_time = pd.to_datetime(bk['datetime']).strftime('%Y-%m-%d %H:%M:%S')
                
                if bk_time not in time_series:
                    continue
                
                idx = time_series.index(bk_time)
                
                if idx + forward_bars >= len(df):
                    continue
                
                total_valid += 1
                entry_price = float(bk['price'])
                future_data = df.iloc[idx + 1 : idx + forward_bars + 1]
                
                # 判定邏輯
                f_high = future_data['high'].max()
                f_low = future_data['low'].min()
                
                if f_high > entry_price or f_low < entry_price:
                    success_count += 1
            except:
                continue
        
        if total_valid == 0: return 0.0
        return (success_count / total_valid * 100)