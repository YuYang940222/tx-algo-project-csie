import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import warnings

# --- 1. 環境與忽略警告 ---
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
np.random.seed(42)

from data_loader import DataLoader
from trendline_detector import TrendlineBreakoutDetector

# --- 2. 核心參數 ---
BEST_TOUCHES = 3
BEST_WINDOW = 20
BEST_THRESHOLD = 0.0025
LOOKBACK_BARS = 9000  
FORWARD_BARS = 10     

def get_single_trade_result(df, entry_idx, forward_bars):
    exit_idx = entry_idx + forward_bars
    if exit_idx >= len(df): return None 
    close_col = next((c for c in df.columns if c.lower() == 'close'), None)
    entry_price = df[close_col].iloc[entry_idx]
    exit_price = df[close_col].iloc[exit_idx]
    return 1 if (exit_price - entry_price) > 0 else 0

def run_sensitivity_analysis():
    # --- 3. 資料載入 ---
    loader = DataLoader()
    full_df = loader.load_from_text_file("7652A_Hour.TXT")
    if full_df is None: return
    df_sliced = full_df.tail(LOOKBACK_BARS).reset_index(drop=True)
    
    # --- 4. 偵測原始突破訊號 ---
    detector = TrendlineBreakoutDetector(
        swing_window=BEST_WINDOW, 
        min_touches=BEST_TOUCHES, 
        breakout_threshold=BEST_THRESHOLD, 
        lookback_bars=len(df_sliced)
    )
    analysis = detector.analyze(df_sliced)
    breakouts = analysis['breakouts']
    
    time_col = next((c for c in df_sliced.columns if c.lower() in ['datetime', 'date', 'time']), None)
    open_col = next((c for c in df_sliced.columns if c.lower() == 'open'), None)
    close_col = next((c for c in df_sliced.columns if c.lower() == 'close'), None)

    raw_signals = []
    for b in breakouts:
        matches = df_sliced.index[df_sliced[time_col] == b['datetime']].tolist()
        if not matches: continue
        idx = matches[0]
        amp = abs(df_sliced[close_col].iloc[idx] - df_sliced[open_col].iloc[idx]) / df_sliced[open_col].iloc[idx]
        is_win = get_single_trade_result(df_sliced, idx, FORWARD_BARS)
        if is_win is not None:
            raw_signals.append({'Amplitude': amp, 'IsWin': is_win})
    
    df_all = pd.DataFrame(raw_signals)

    # --- 5. 執行敏感度掃描 ---
    thresholds = [0.0000, 0.0005, 0.0010, 0.0015, 0.0020, 0.0025, 0.0030, 0.0035, 0.0040]
    sensitivity_results = []

    print("\n" + "="*70)
    print(f"{'門檻(%)':>8} | {'樣本數(N)':>10} | {'總勝率':>10} | {'R2':>10} | {'P-Value':>10}")
    print("-" * 70)

    for thr in thresholds:
        subset = df_all[df_all['Amplitude'] >= thr]
        n_count = len(subset)
        if n_count < 10: continue

        win_rate = subset['IsWin'].mean()
        
        try:
            num_bins = min(8, max(4, n_count // 15))
            subset['Bin'] = pd.qcut(subset['Amplitude'], q=num_bins, duplicates='drop')
            bin_stats = subset.groupby('Bin', observed=True).agg({'Amplitude':'mean', 'IsWin':'mean'}).reset_index()
            slope, intercept, r_val, p_val, _ = stats.linregress(bin_stats['Amplitude'], bin_stats['IsWin'])
            
            p_str = f"{p_val:.4f}"
            if p_val < 0.05: p_str += " *" 
            
            print(f"{thr*100:>9.2f}% | {n_count:>12} | {win_rate:>11.2%} | {r_val**2:>10.4f} | {p_str:>10}")
            
            sensitivity_results.append({
                'Threshold': thr, 'WinRate': win_rate, 'PValue': p_val, 'N': n_count
            })
        except:
            continue

    print("="*70)

    # --- 6. 繪製敏感度趨勢圖 ---
    if sensitivity_results:
        res_df = pd.DataFrame(sensitivity_results)
        fig, ax1 = plt.subplots(figsize=(12, 7))

        # 勝率軸 (左側)
        color_wr = 'tab:blue'
        ax1.set_xlabel('Min Amplitude Threshold (%)', fontsize=12)
        ax1.set_ylabel('Win Rate', color=color_wr, fontsize=12, fontweight='bold')
        line1 = ax1.plot(res_df['Threshold']*100, res_df['WinRate'], marker='o', color=color_wr, linewidth=3, label='Win Rate')
        ax1.tick_params(axis='y', labelcolor=color_wr)
        ax1.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)

        # 在勝率點上標註勝率數值
        for i, txt in enumerate(res_df['WinRate']):
            ax1.annotate(f"{txt:.1%}", (res_df['Threshold'].iloc[i]*100, res_df['WinRate'].iloc[i]), 
                         textcoords="offset points", xytext=(0,10), ha='center', color=color_wr, fontweight='bold')

        # P-Value 軸 (右側)
        ax2 = ax1.twinx()
        color_pv = 'tab:red'
        ax2.set_ylabel('P-Value (Lower is Better)', color=color_pv, fontsize=12, fontweight='bold')
        line2 = ax2.plot(res_df['Threshold']*100, res_df['PValue'], marker='s', color=color_pv, linestyle=':', alpha=0.7, label='P-Value')
        ax2.tick_params(axis='y', labelcolor=color_pv)
        ax2.set_ylim(0, 1.1) # 讓刻度固定在 0-1 之間

        # 重要：在 P-Value 點旁標註數值
        for i, txt in enumerate(res_df['PValue']):
            ax2.annotate(f"P={txt:.3f}", (res_df['Threshold'].iloc[i]*100, res_df['PValue'].iloc[i]), 
                         textcoords="offset points", xytext=(0,-15), ha='center', color=color_pv, fontsize=9)

        plt.title('Threshold Sensitivity Analysis: Identifying the Signal/Noise Boundary', fontsize=14, pad=20)
        fig.tight_layout()
        plt.show()

if __name__ == '__main__':
    run_sensitivity_analysis()