import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
from data_loader import DataLoader
from trendline_detector import TrendlineBreakoutDetector
from quant_analyzer import QuantAnalyzer

# --- 核心參數調整 ---
LOOKBACK_BARS = 3000      # 改回 500 根，適合快速測試
FIXED_SL = 50                  
FIXED_TP = 50                  
# 因為總 K 棒只有 500，我們將門檻降到 10，否則圖表會被遮光光
MIN_SIGNALS_THRESHOLD = 10     

def run_test(args):
    win, touches, thr, df_sliced = args
    detector = TrendlineBreakoutDetector(win, touches, thr, len(df_sliced))
    analysis = detector.analyze(df_sliced)
    backtest = QuantAnalyzer.backtest_breakout_winrate(df_sliced, analysis['breakouts'], FIXED_SL, FIXED_TP, 2)
    
    total = backtest['total_signals']
    rate = backtest['win_rate']
    wins = round(total * rate / 100)
    
    # 格式：勝率% \n (成功次數/總次數)
    annot_text = f"{rate:.1f}%\n({wins}/{total})"
    
    return {
        'Touches': touches,
        'Threshold': thr,
        'Window': win,
        'WinRate': rate,
        'Total': total,
        'Wins': wins,
        'Annot': annot_text
    }

if __name__ == '__main__':
    loader = DataLoader("7652A_Hour.TXT")
    full_df = loader.load_from_text_file()
    
    if full_df is not None:
        df_sliced = full_df.tail(LOOKBACK_BARS).reset_index(drop=True)
        print(f"🔬 快速測試模式：讀取最近 {LOOKBACK_BARS} 根 K 棒")

        # 定義網格範圍 (測試時可以不用跑太密，省時間)
        windows = [4, 8, 12, 16, 20] 
        thresholds = [0.0005, 0.001, 0.0015, 0.002]
        touches_list = [2, 3]
        
        tasks = [(w, t, h, df_sliced) for t in touches_list for h in thresholds for w in windows]

        print(f"⚡ 正在運算 {len(tasks)} 組組合...")
        with ProcessPoolExecutor() as executor:
            results = list(tqdm(executor.map(run_test, tasks), total=len(tasks)))

        res_df = pd.DataFrame(results)

        # 繪圖
        fig, axes = plt.subplots(1, 2, figsize=(18, 8), sharey=True)
        
        for i, touches in enumerate(touches_list):
            subset = res_df[res_df['Touches'] == touches]
            pivot_rate = subset.pivot(index="Threshold", columns="Window", values="WinRate")
            pivot_annot = subset.pivot(index="Threshold", columns="Window", values="Annot")
            
            # 過濾掉樣本數不足的格子
            mask = subset.pivot(index="Threshold", columns="Window", values="Total") < MIN_SIGNALS_THRESHOLD
            
            sns.heatmap(pivot_rate, annot=pivot_annot, fmt="", cmap="YlGnBu", 
                        mask=mask, cbar_kws={'label': 'Win Rate (%)'}, ax=axes[i])
            
            axes[i].set_title(f"Min Touches = {touches} (Min Signals: {MIN_SIGNALS_THRESHOLD})")

        plt.suptitle(f"Parameter Calibration (Sample: {LOOKBACK_BARS} Bars)", fontsize=16)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()