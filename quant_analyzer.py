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
    def backtest_breakout_winrate(df, breakouts, forward_bars=10, stop_loss=30, take_profit=60):
        """
        [真實戰場版] 引入固定點數停損停利機制 (預設停損30點，停利60點)
        """
        if df is None or not breakouts or len(breakouts) == 0:
            return 0.0
            
        success_count = 0
        total_valid = 0
        
        work_df = df.copy().reset_index(drop=True)
        work_df['datetime'] = pd.to_datetime(work_df['datetime'].astype(str).str.strip(), errors='coerce')
        work_df['datetime'] = work_df['datetime'].apply(lambda x: x.replace(tzinfo=None) if pd.notnull(x) else x)
        
        for col in ['close', 'high', 'low']:
            work_df[col] = pd.to_numeric(work_df[col], errors='coerce')
            
        for bk in breakouts:
            try:
                bk_time = pd.to_datetime(str(bk['datetime']).strip(), errors='coerce').replace(tzinfo=None)
                
                time_diff = (work_df['datetime'] - bk_time).abs()
                idx = time_diff.idxmin()
                
                if pd.isna(idx) or time_diff[idx] > pd.Timedelta(hours=1):
                    continue
                if idx + forward_bars >= len(work_df):
                    continue
                
                total_valid += 1
                entry_price = float(work_df['close'].iloc[idx])
                future_data = work_df.iloc[idx + 1 : idx + forward_bars + 1]
                
                bk_type = bk.get('type', bk.get('direction', 'resistance'))
                
                is_win = False
                is_closed = False
                
                # 逐根 K 棒模擬未來走勢
                for _, future_bar in future_data.iterrows():
                    bar_high = float(future_bar['high'])
                    bar_low = float(future_bar['low'])
                    
                    if 'resistance' in bk_type:  # 做多 (向上突破)
                        # 先看最低價有沒有掃到停損
                        if bar_low <= entry_price - stop_loss:
                            is_win = False
                            is_closed = True
                            break # 出場，結束這筆交易
                        # 再看最高價有沒有碰到停利
                        elif bar_high >= entry_price + take_profit:
                            is_win = True
                            is_closed = True
                            break # 獲利入袋，結束這筆交易
                            
                    else:  # 做空 (向下突破)
                        if bar_high >= entry_price + stop_loss:
                            is_win = False
                            is_closed = True
                            break
                        elif bar_low <= entry_price - take_profit:
                            is_win = True
                            is_closed = True
                            break
                
                # 如果過了 10 根 K 棒都沒碰到停損也沒碰到停利，時間到強制平倉 (看最後一根的收盤價)
                if not is_closed:
                    final_close = float(future_data.iloc[-1]['close'])
                    if 'resistance' in bk_type:
                        is_win = (final_close > entry_price)
                    else:
                        is_win = (final_close < entry_price)
                        
                if is_win:
                    success_count += 1
                    
            except Exception as e:
                continue
        
        if total_valid == 0:
            return 0.0
            
        return (success_count / total_valid) * 100.0