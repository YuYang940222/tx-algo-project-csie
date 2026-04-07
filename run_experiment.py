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
LOOKBACK_BARS = 2000           # 測試的總 K 棒數量
MIN_SIGNALS_THRESHOLD = 10     # 最少要有 10 次訊號，才具備統計意義
FORWARD_BARS = 10              # 裁判：我們固定看突破後第 10 根 K 棒的表現 (不設停損停利)

def run_test(args):
    win, touches, thr, df_sliced = args
    
    # 1. 雷達：掃描突破點
    detector = TrendlineBreakoutDetector(
        swing_window=win, 
        min_touches=touches, 
        breakout_threshold=thr, 
        lookback_bars=len(df_sliced)
    )
    analysis = detector.analyze(df_sliced)
    
    # 2. 裁判：呼叫全新的純粹裁判！(固定 N 根 K 棒報酬率)
    backtest = QuantAnalyzer.calculate_forward_return(
        df=df_sliced, 
        breakouts=analysis['breakouts'], 
        forward_bars=FORWARD_BARS
    )
    
    total = backtest['total_signals']
    rate = backtest['win_rate']
    avg_ret = backtest['avg_return']
    
    # 格式改為：平均點數 \n (勝率%)
    annot_text = f"{avg_ret:.1f} pts\nN={total} ({rate:.1f}%)"    
    return {
        'Touches': touches,
        'Threshold': thr,
        'Window': win,
        'AvgReturn': avg_ret,
        'Total': total,
        'Annot': annot_text
    }

if __name__ == '__main__':
    # 載入資料 (保險起見，使用你主程式習慣的載入方式)
    loader = DataLoader()
    full_df = loader.load_from_text_file("7652A_Hour.TXT")
    
    if full_df is not None:
        # 取最近的 N 根 K 棒進行快速回測
        df_sliced = full_df.tail(LOOKBACK_BARS).reset_index(drop=True)
        print(f"🔬 第一階段：尋找黃金雷達 (純粹訊號測試) - 讀取最近 {LOOKBACK_BARS} 根 K 棒")

        # 定義網格範圍
        windows = [10, 15, 20, 25, 30] 
        thresholds = [0.0005, 0.001, 0.0015, 0.002, 0.003] 
        touches_list = [2, 3]
        
        # 建立多核心運算任務清單
        tasks = [(w, t, h, df_sliced) for t in touches_list for h in thresholds for w in windows]

        print(f"⚡ 正在運算 {len(tasks)} 組組合 (無停損停利，看 {FORWARD_BARS} 根 K 棒後表現)...")
        with ProcessPoolExecutor() as executor:
            results = list(tqdm(executor.map(run_test, tasks), total=len(tasks)))

        # 將結果轉為 DataFrame
        res_df = pd.DataFrame(results)

        # --- 開始繪圖 ---
        fig, axes = plt.subplots(1, 2, figsize=(18, 8), sharey=True)
        
        for i, touches in enumerate(touches_list):
            subset = res_df[res_df['Touches'] == touches]
            
            # 以 Threshold 為 Y 軸，Window 為 X 軸，值為 AvgReturn
            pivot_rate = subset.pivot(index="Threshold", columns="Window", values="AvgReturn")
            pivot_annot = subset.pivot(index="Threshold", columns="Window", values="Annot")
            
            # 過濾掉樣本數不足的格子 (避免隨機致富)
            mask = subset.pivot(index="Threshold", columns="Window", values="Total") < MIN_SIGNALS_THRESHOLD
            
            # 畫熱力圖：使用 RdYlGn (紅黃綠)，center=0 讓大於0變綠色，小於0變紅色
            sns.heatmap(pivot_rate, annot=pivot_annot, fmt="", cmap="RdYlGn", center=0,
                        mask=mask, cbar_kws={'label': f'Avg Forward Return ({FORWARD_BARS} Bars)'}, ax=axes[i])
            
            axes[i].set_title(f"Min Touches = {touches} (Min Signals: {MIN_SIGNALS_THRESHOLD})")

        plt.suptitle(f"Phase 1: Entry Signal Quality (Sample: {LOOKBACK_BARS} Bars, No SL/TP)", fontsize=16)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.show()
    else:
        print("資料載入失敗，請確認檔案路徑與格式！")