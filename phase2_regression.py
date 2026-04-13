import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import warnings

# --- 1. 環境設定 ---
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
np.random.seed(42)

from data_loader import DataLoader
from trendline_detector import TrendlineBreakoutDetector

# --- 2. 核心參數 ---
BEST_TOUCHES = 3
BEST_WINDOW = 30
BEST_THRESHOLD = 0.0025

# 修正建議：將過濾門檻拉高到 0.1% (0.001) 試試看
MIN_AMPLITUDE = 0.003  

LOOKBACK_BARS = 1000  
FORWARD_BARS = 10     

def get_single_trade_result(df, entry_idx, forward_bars):
    """計算單筆交易勝負 (1=贏, 0=輸)"""
    exit_idx = entry_idx + forward_bars
    if exit_idx >= len(df):
        return None 
    
    close_col = next((c for c in df.columns if c.lower() == 'close'), None)
    if close_col is None:
        return None

    entry_price = df[close_col].iloc[entry_idx]
    exit_price = df[close_col].iloc[exit_idx]
    
    return 1 if (exit_price - entry_price) > 0 else 0

def run_phase2_validation():
    # --- 3. 資料載入 ---
    loader = DataLoader()
    full_df = loader.load_from_text_file("7652A_Hour.TXT")
    if full_df is None: return
        
    df_sliced = full_df.tail(LOOKBACK_BARS).reset_index(drop=True)
    
    # --- 4. 偵測突破 ---
    detector = TrendlineBreakoutDetector(
        swing_window=BEST_WINDOW, 
        min_touches=BEST_TOUCHES, 
        breakout_threshold=BEST_THRESHOLD, 
        lookback_bars=len(df_sliced)
    )
    analysis = detector.analyze(df_sliced)
    breakouts = analysis['breakouts']
    
    if not breakouts: return

    time_col = next((c for c in df_sliced.columns if c.lower() in ['datetime', 'date', 'time']), None)
    open_col = next((c for c in df_sliced.columns if c.lower() == 'open'), None)
    close_col = next((c for c in df_sliced.columns if c.lower() == 'close'), None)

    # --- 5. 訊號萃取 ---
    signal_data = []
    for b in breakouts:
        entry_idx = None
        if time_col is not None:
            matches = df_sliced.index[df_sliced[time_col] == b['datetime']].tolist()
            if matches: entry_idx = matches[0]

        if entry_idx is None: continue
            
        e_open = df_sliced[open_col].iloc[entry_idx]
        e_close = df_sliced[close_col].iloc[entry_idx]
        amplitude = abs(e_close - e_open) / e_open if e_open != 0 else 0
        
        # 過濾門檻
        if amplitude < MIN_AMPLITUDE: continue
             
        is_win = get_single_trade_result(df_sliced, entry_idx, FORWARD_BARS)
        if is_win is not None:
            signal_data.append({'Amplitude': amplitude, 'IsWin': is_win})
            
    df_signals = pd.DataFrame(signal_data)
    total_signals = len(df_signals)
    
    # --- 6. 計算勝率並印出 (你要的數據) ---
    if total_signals > 0:
        win_count = df_signals['IsWin'].sum()
        win_rate = win_count / total_signals
        print("\n" + "="*40)
        print(f"📊 策略實測結果 (N={total_signals})")
        print(f"🔹 過濾門檻: {MIN_AMPLITUDE*100:.2f}%")
        print(f"✅ 獲利筆數: {int(win_count)}")
        print(f"❌ 虧損筆數: {int(total_signals - win_count)}")
        print(f"🏆 總體平均勝率: {win_rate:.2%}")
        print("="*40 + "\n")
    else:
        print("沒有符合條件的訊號。")
        return

    # --- 7. 回歸分析繪圖 ---
    num_bins = min(10, max(4, total_signals // 10)) 
    df_signals['Bin'] = pd.qcut(df_signals['Amplitude'], q=num_bins, duplicates='drop')
    bin_analysis = df_signals.groupby('Bin', observed=True).agg({'Amplitude': 'mean', 'IsWin': 'mean'}).reset_index()

    slope, intercept, r_value, p_value, std_err = stats.linregress(bin_analysis['Amplitude'], bin_analysis['IsWin'])
    
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(11, 7))
    sns.regplot(x='Amplitude', y='IsWin', data=bin_analysis, 
                scatter_kws={'s': 180, 'alpha': 0.85, 'color': '#2E86AB', 'edgecolor': 'white', 'linewidths': 2},
                line_kws={'color': '#D62828', 'linewidth': 3, 'label': f'Trend: y={slope:.2f}x + {intercept:.2f}'})
    
    plt.title(f'Phase 2: Signal Quality Check (Win Rate: {win_rate:.2%})', fontsize=16, fontweight='bold')
    plt.xlabel('Breakout Amplitude (%)')
    plt.ylabel('Win Rate')
    plt.ylim(-0.05, 1.05) 
    
    stats_text = f'$R^2$ = {r_value**2:.4f}\nCorr (r) = {r_value:.3f}\n$p$-value = {p_value:.4f}'
    plt.text(0.05, 0.78, stats_text, transform=plt.gca().transAxes, bbox=dict(facecolor='white', alpha=0.9), fontsize=12)
    
    plt.legend(loc='lower right')
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    run_phase2_validation()