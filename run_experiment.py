import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor

# 導入自定義模組
from data_loader import DataLoader
from trendline_detector import TrendlineBreakoutDetector
from quant_analyzer import QuantAnalyzer

# --- 核心參數調整 ---
LOOKBACK_BARS = 1000           
MIN_SIGNALS_THRESHOLD = 10      # 💡 提示：因為 Touches 增加，建議稍微調低門檻 (例如 5)，否則 Touches=5 可能會全白
FORWARD_BARS = 10              

def run_test(args):
    win, touches, thr, df_sliced = args
    
    detector = TrendlineBreakoutDetector(
        swing_window=win, 
        min_touches=touches, 
        breakout_threshold=thr, 
        lookback_bars=len(df_sliced)
    )
    analysis = detector.analyze(df_sliced)
    
    # 呼叫純粹裁判邏輯
    backtest = QuantAnalyzer.calculate_forward_return(
        df=df_sliced, 
        breakouts=analysis['breakouts'], 
        forward_bars=FORWARD_BARS
    )
    
    total = backtest['total_signals']
    rate = backtest['win_rate']
    avg_ret_points = backtest['avg_return']  # 這是原本的「點數」
    
    # 依照你的交易商品設定乘數：大台指=200，小台指=50
    POINT_MULTIPLIER = 200  
    
    # 將平均點數乘上倍數，算出平均獲利金額
    avg_ret_ntd = avg_ret_points * POINT_MULTIPLIER
    
    # 修改顯示文字：把 pts 換成 NTD。
    # 金額通常不需要顯示小數點，所以把 .1f 改成 .0f 取整數
    annot_text = f"{avg_ret_ntd:.0f} NTD\nN={total} ({rate:.1f}%)"    
    # ==========================================
    
    return {
        'Touches': touches,
        'Threshold': thr,
        'Window': win,
        'AvgReturn': avg_ret_ntd,  # 這裡也可以一併回傳轉換後的金額，這樣熱力圖的顏色深淺也會基於真實金額
        'Total': total,
        'Annot': annot_text
    }

if __name__ == '__main__':
    loader = DataLoader()
    full_df = loader.load_from_text_file("7652A_Hour.TXT")
    
    if full_df is not None:
        df_sliced = full_df.tail(LOOKBACK_BARS).reset_index(drop=True)
        print(f"🔬 擴展測試：掃描 Touches 2~5 - 讀取最近 {LOOKBACK_BARS} 根 K 棒")

        # 定義網格範圍
        windows = [10, 15, 20, 25, 30]  # 💡 修改點 1：增加到 10, 15, 20, 25, 30
        thresholds = [0.0015, 0.002, 0.0025, 0.003] 
        touches_list = [2, 3, 4, 5]  # 💡 修改點 1：增加到 2, 3, 4, 5
        
        tasks = [(w, t, h, df_sliced) for t in touches_list for h in thresholds for w in windows]

        print(f"⚡ 正在運算 {len(tasks)} 組組合 (多核心執行中)...")
        with ProcessPoolExecutor() as executor:
            results = list(tqdm(executor.map(run_test, tasks), total=len(tasks)))

        res_df = pd.DataFrame(results)

        # --- 開始繪圖 ---
        # 💡 修改點 2：改成 2x2 佈局 (共 4 張圖)
        fig, axes = plt.subplots(2, 2, figsize=(20, 16), sharey=True, sharex=True)
        axes_flat = axes.flatten() # 攤平成一維陣列方便用迴圈跑
        
        for i, touches in enumerate(touches_list):
            subset = res_df[res_df['Touches'] == touches]
            
            pivot_rate = subset.pivot(index="Threshold", columns="Window", values="AvgReturn")
            pivot_annot = subset.pivot(index="Threshold", columns="Window", values="Annot")
            mask = subset.pivot(index="Threshold", columns="Window", values="Total") < MIN_SIGNALS_THRESHOLD
            
            sns.heatmap(pivot_rate, annot=pivot_annot, fmt="", cmap="RdYlGn", center=0,
                        mask=mask, cbar_kws={'label': 'Avg Return'}, ax=axes_flat[i])
            
            axes_flat[i].set_title(f"Min Touches = {touches}", fontsize=14, fontweight='bold')

        plt.suptitle(f"Phase 1: Entry Quality Comparison (Touches 2-5)\nTotal Sample: {LOOKBACK_BARS} K-Bars | Fixed Forward: {FORWARD_BARS} Bars, No SL/TP", fontsize=20)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()
    else: 
        print("資料載入失敗！")