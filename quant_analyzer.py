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
        """
        [實戰回測引擎] 
        1. 強制對位：解決找不到 K 棒的問題
        2. 停損停利：解決 97% 虛假勝率問題
        3. 交易成本：模擬真實手續費與滑價 (預設每口扣 2 點)
        """
        if df is None or not breakouts or len(breakouts) == 0:
            return 0.0
            
        success_count = 0
        total_valid = 0
        
        # 準備資料：強制轉型與清理
        work_df = df.copy().reset_index(drop=True)
        work_df['datetime'] = pd.to_datetime(work_df['datetime'].astype(str).str.strip(), errors='coerce')
        work_df['datetime'] = work_df['datetime'].apply(lambda x: x.replace(tzinfo=None) if pd.notnull(x) else x)
        
        for col in ['close', 'high', 'low']:
            work_df[col] = pd.to_numeric(work_df[col], errors='coerce')
        
        # --- 計算 ATR (作為未來動態參考，目前先用固定點數) ---
        # tr = np.maximum(work_df['high'] - work_df['low'], 
        #                np.maximum(abs(work_df['high'] - work_df['close'].shift(1)), 
        #                           abs(work_df['low'] - work_df['close'].shift(1))))
        # work_df['atr'] = tr.rolling(window=14).mean()

        print(f"\n--- 🚀 開始實戰回測 (成本: {cost} 點) ---")
        
        for bk in breakouts:
            try:
                # 1. 精準對位
                bk_time = pd.to_datetime(str(bk['datetime']).strip(), errors='coerce').replace(tzinfo=None)
                time_diff = (work_df['datetime'] - bk_time).abs()
                idx = time_diff.idxmin()
                
                # 排除太靠近現在或找不到的點
                if pd.isna(idx) or time_diff[idx] > pd.Timedelta(hours=1) or idx + forward_bars >= len(work_df):
                    continue
                
                total_valid += 1
                
                # 2. 加入交易成本 (滑價 + 手續費)
                # 做多買進：你會買得比收盤價貴 (加上 cost)
                # 做空賣出：你會賣得比收盤價便宜 (扣掉 cost)
                raw_close = float(work_df['close'].iloc[idx])
                bk_type = bk.get('type', bk.get('direction', 'resistance'))
                
                if 'resistance' in bk_type or 'bullish' in bk_type:
                    entry_price = raw_close + cost
                    mode = "LONG"
                else:
                    entry_price = raw_close - cost
                    mode = "SHORT"
                
                # 3. 逐根檢查未來走勢
                future_data = work_df.iloc[idx + 1 : idx + forward_bars + 1]
                is_win = False
                is_closed = False
                
                for _, bar in future_data.iterrows():
                    h, l, c = float(bar['high']), float(bar['low']), float(bar['close'])
                    
                    if mode == "LONG":
                        # 檢查是否先掃到停損
                        if l <= entry_price - stop_loss:
                            is_win = False
                            is_closed = True
                            break
                        # 檢查是否達到停利
                        elif h >= entry_price + take_profit:
                            is_win = True
                            is_closed = True
                            break
                    else: # SHORT
                        if h >= entry_price + stop_loss:
                            is_win = False
                            is_closed = True
                            break
                        elif l <= entry_price - take_profit:
                            is_win = True
                            is_closed = True
                            break
                
                # 如果時間到還沒分勝負，強制平倉
                if not is_closed:
                    final_c = float(future_data.iloc[-1]['close'])
                    is_win = (final_c > entry_price) if mode == "LONG" else (final_c < entry_price)
                
                if is_win:
                    success_count += 1
                    
            except Exception:
                continue

        if total_valid == 0: return 0.0
        
        final_rate = (success_count / total_valid) * 100.0
        print(f"--- 結算: 勝率 {final_rate:.1f}% (樣本: {total_valid}) ---")
        return final_rate