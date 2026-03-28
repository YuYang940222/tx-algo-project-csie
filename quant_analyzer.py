"""
量化分析模組 - 實戰進階版 (含停損、停利、交易成本與 ATR 邏輯)
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
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, prices)
        r_squared = r_value**2
        
        return {
            'r_squared': r_squared,
            'confidence': r_squared * 100,
            'is_stable': r_squared > 0.6 and p_value < 0.05
        }

    @staticmethod
    def backtest_breakout_winrate(df, breakouts, forward_bars=10, stop_loss=30, take_profit=60, cost=2):
        """實戰回測引擎 (多空分離版)"""
        

        # 準備記分板：整體、做多、做空
        total_valid, success_count = 0, 0
        long_valid, long_success = 0, 0
        short_valid, short_success = 0, 0
        
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
                
                if pd.isna(idx) or time_diff[idx] > pd.Timedelta(hours=1) or idx + forward_bars >= len(work_df):
                    continue
                
                total_valid += 1
                raw_close = float(work_df['close'].iloc[idx])
                bk_type = bk.get('type', bk.get('direction', 'resistance'))
                
                # 判斷多空方向，並記錄次數
                if 'resistance' in bk_type or 'bullish' in bk_type:
                    entry_price = raw_close + cost
                    mode = "LONG"
                    long_valid += 1
                else:
                    entry_price = raw_close - cost
                    mode = "SHORT"
                    short_valid += 1
                
                future_data = work_df.iloc[idx + 1 : idx + forward_bars + 1]
                is_win = False
                is_closed = False
                
                # 逐根檢查停損停利
                for _, bar in future_data.iterrows():
                    h, l, c = float(bar['high']), float(bar['low']), float(bar['close'])
                    if mode == "LONG":
                        if l <= entry_price - stop_loss:
                            is_win, is_closed = False, True
                            break
                        elif h >= entry_price + take_profit:
                            is_win, is_closed = True, True
                            break
                    else:
                        if h >= entry_price + stop_loss:
                            is_win, is_closed = False, True
                            break
                        elif l <= entry_price - take_profit:
                            is_win, is_closed = True, True
                            break
                
                if not is_closed:
                    final_c = float(future_data.iloc[-1]['close'])
                    is_win = (final_c > entry_price) if mode == "LONG" else (final_c < entry_price)
                
                # 結算勝場
                if is_win:
                    success_count += 1
                    if mode == "LONG":
                        long_success += 1
                    else:
                        short_success += 1
                        
            except Exception:
                continue

        if total_valid == 0: 
            return {'win_rate': 0.0, 'expectancy': 0.0, 'total_signals': 0,
                    'long_win_rate': 0.0, 'long_exp': 0.0, 'long_signals': 0,
                    'short_win_rate': 0.0, 'short_exp': 0.0, 'short_signals': 0}

        # --- 計算整體期望值 ---
        fail_count = total_valid - success_count
        net_pnl = (success_count * take_profit) - (fail_count * stop_loss) - (total_valid * cost * 2)
        expectancy = net_pnl / total_valid
        win_rate = (success_count / total_valid) * 100.0
        
        # --- 計算做多期望值 ---
        long_exp = 0.0
        long_win_rate = 0.0
        if long_valid > 0:
            long_fail = long_valid - long_success
            long_pnl = (long_success * take_profit) - (long_fail * stop_loss) - (long_valid * cost * 2)
            long_exp = long_pnl / long_valid
            long_win_rate = (long_success / long_valid) * 100.0

        # --- 計算做空期望值 ---
        short_exp = 0.0
        short_win_rate = 0.0
        if short_valid > 0:
            short_fail = short_valid - short_success
            short_pnl = (short_success * take_profit) - (short_fail * stop_loss) - (short_valid * cost * 2)
            short_exp = short_pnl / short_valid
            short_win_rate = (short_success / short_valid) * 100.0

        return {
            'win_rate': win_rate, 'expectancy': expectancy, 'total_signals': total_valid,
            'long_win_rate': long_win_rate, 'long_exp': long_exp, 'long_signals': long_valid,
            'short_win_rate': short_win_rate, 'short_exp': short_exp, 'short_signals': short_valid
        }