請點擊下方區塊右上角的「複製」按鈕，貼上至記事本或 VS Code 後，直接存檔為 `README.md` 即可：

```markdown
# 📈 Quantitative Trading Dashboard (專業量化交易分析儀表板)

這是一個基於 Python 與 Streamlit 開發的量化交易回測與分析系統。本專案專注於**趨勢線突破 (Trendline Breakout)** 策略的自動化檢測，並提供 TradingView 風格的互動式圖表、動態參數最佳化 (停損/停利熱力圖) 以及訊號品質的統計回歸分析。

支援台灣常見的期貨/股票歷史資料格式 (OHLCV)，可協助交易者快速驗證交易邏輯的期望值與勝率。

## ✨ 核心功能 (Features)

* **📊 互動式圖表視覺化**：整合 Plotly 打造 TradingView 風格的深色主題 K 線圖，自動標記支撐/壓力線與突破點。
* **🎯 趨勢線自動偵測**：基於自訂的 `swing_window` 與 `min_touches` 演算法，自動尋找圖表上的關鍵轉折點並繪製趨勢線。
* **⚙️ 量化回測引擎**：支援多空分離的回測邏輯，可自訂向前看的 K 棒數 (Forward Bars)、停損停利點數與交易成本，並計算真實淨利。
* **🔥 參數最佳化熱力圖**：一鍵產生停損 vs. 停利參數矩陣的期望值熱力圖，快速找出最佳風險報酬比 (Risk-Reward Ratio)。
* **📈 統計與回歸分析**：利用線性回歸與分箱分析 (Bin Analysis) 檢驗交易訊號的品質與穩定度，過濾無效突破。

## 📂 專案架構 (Project Structure)

- `main_app.py`：Streamlit 網頁應用程式主程式 (入口點)
- `data_loader.py`：資料載入與清理模組 (支援 utf-8, cp950, big5 等多種編碼)
- `trendline_detector.py`：核心演算法：搖擺點計算與趨勢線/突破點偵測
- `quant_analyzer.py`：量化回測引擎：計算勝率、期望值與投資組合表現
- `chart_visualizer.py`：圖表渲染模組：封裝 Plotly 與前端數據卡 HTML
- `run_experiment.py`：批次實驗腳本：利用多核心進行多組參數的暴力破解與測試
- `phase2_regression.py`：第二階段分析：針對突破訊號進行線性回歸與散佈圖分析
- `7652A_Hour.TXT`：測試用的 OHLCV 歷史資料範例
- `experiment_results.csv`：參數實驗輸出的回測結果紀錄

## 🚀 快速啟動 (Getting Started)

### 1. 準備環境
建議使用虛擬環境來執行此專案。請在終端機中輸入以下指令：

**建立虛擬環境 (可選)**
```bash
python -m venv venv
```

**啟動虛擬環境**
- Windows:
  ```bash
  venv\Scripts\activate
  ```
- macOS/Linux:
  ```bash
  source venv/bin/activate
  ```

### 2. 安裝依賴套件
請確保安裝了以下核心套件：

```bash
pip install pandas numpy plotly streamlit scipy seaborn matplotlib tqdm
```

### 3. 執行儀表板
在終端機輸入以下指令啟動 Streamlit 應用程式：

```bash
streamlit run main_app.py
```
啟動後，瀏覽器會自動開啟 `http://localhost:8501`，即可開始使用量化儀表板。

## 💡 使用說明 (Usage)

1. **載入資料**：在左側控制面板確認檔案路徑 (預設為 `7652A_Hour.TXT`)，點擊「載入資料」。
2. **設定參數**：調整 `Swing Window` (尋找轉折點的區間) 與 `Min Touches` (趨勢線最少觸碰次數)。
3. **執行檢測**：點擊「執行趨勢線分析」，系統會自動標記圖表上的進場訊號。
4. **進階回測**：在「進階回測與最佳化」區塊，輸入你預期的停損、停利範圍，系統會運算並輸出期望值熱力圖，輔助制定交易策略。

## 🛠️ 開發與維護 (Development)

* **開發者**：[YuYang940222,seven940611]
* **主力語言**：Python 3.x
* **前端框架**：Streamlit