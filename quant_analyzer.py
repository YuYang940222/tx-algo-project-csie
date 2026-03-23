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
        print(f"\n[DEBUG 報告] 收到 {len(breakouts) if breakouts else 0} 個突破點準備回測...")
        
        if df is None or not breakouts or len(breakouts) == 0:
            return 0.0
            
        success_count = 0
        total_valid = 0
        
        work_df = df.copy().reset_index(drop=True)
        
        # 🟢 【關鍵修復 1】強制清理所有隱形的空白與格式，再轉成純時間！(把之前不小心刪掉的加回來)
        work_df['datetime'] = pd.to_datetime(work_df['datetime'].astype(str).str.strip(), errors='coerce')
        work_df['datetime'] = work_df['datetime'].apply(lambda x: x.replace(tzinfo=None) if pd.notnull(x) else x)
        
        # 🟢 【關鍵修復 2】強制把開高低收變成數字 (Float)，避免字母比大小的 Bug！
        for col in ['close', 'high', 'low']:
            work_df[col] = pd.to_numeric(work_df[col], errors='coerce')
            
        print(f"--- 🔍 開始逐一檢查 {len(breakouts)} 個點 ---")
        
        for bk in breakouts:
            try:
                # 突破點的時間也一樣要清理乾淨
                bk_time = pd.to_datetime(str(bk['datetime']).strip(), errors='coerce').replace(tzinfo=None)
                
                time_diff = (work_df['datetime'] - bk_time).abs()
                idx = time_diff.idxmin()
                min_diff = time_diff[idx]
                
                if pd.isna(idx):
                    print(f"   ❌ 失敗：找不到對應的 K 棒 (NaT) - 尋找目標: {bk_time}")
                    continue
                if min_diff > pd.Timedelta(hours=1):
                    print(f"   ❌ 失敗：時間誤差太大 (差了 {min_diff}) - 尋找目標: {bk_time}")
                    continue
                if idx + forward_bars >= len(work_df):
                    print(f"   ⏳ 失敗：{bk_time} 太新了，後面沒有 {forward_bars} 根可看")
                    continue
                
                total_valid += 1
                entry_price = float(work_df['close'].iloc[idx])
                future_data = work_df.iloc[idx + 1 : idx + forward_bars + 1]
                
                f_high = float(future_data['high'].max())
                f_low = float(future_data['low'].min())
                
                bk_type = bk.get('type', bk.get('direction', 'resistance'))
                
                is_win = False
                if 'resistance' in bk_type:
                    is_win = (f_high > entry_price)
                else:
                    is_win = (f_low < entry_price)
                    
                if is_win:
                    success_count += 1
                    
                print(f"   ✅ 成功對位！進場: {entry_price:.0f} | 最高: {f_high:.0f} | 最低: {f_low:.0f} | 獲利: {is_win}")
                    
            except Exception as e:
                print(f"   🚨 發生嚴重錯誤: {e}")

        print(f"--- 📊 最終結算: 賺錢 {success_count} 次 / 總共買了 {total_valid} 次 ---\n")
        
        if total_valid == 0:
            return 0.0
            
        return (success_count / total_valid) * 100.0