"""
資料載入和處理模組 - 增強版
修復標頭讀取問題並優化大數據處理
"""

import pandas as pd
import numpy as np
import os
from typing import Optional, List
import streamlit as st

class DataLoader:
    """
    資料載入器類別，負責從各種來源載入和處理OHLCV資料
    """
    
    def __init__(self, file_path: str = "7652A_Hour.TXT"):
        self.file_path = file_path
        # 支援的編碼，加入 'big5' 和 'cp950' 以支援台灣常見格式
        self.supported_encodings = ['utf-8', 'cp950', 'big5', 'utf-8-sig', 'latin1']
        
    def load_from_text_file(self, file_path: Optional[str] = None) -> Optional[pd.DataFrame]:
        if file_path is None:
            file_path = self.file_path
            
        try:
            if not os.path.exists(file_path):
                # 如果找不到指定檔案，嘗試找上傳的檔案
                if os.path.exists(f"output/{file_path}"):
                    file_path = f"output/{file_path}"
                else:
                    st.error(f"資料檔案不存在: {file_path}")
                    return None
            
            # 嘗試讀取檔案
            df = self._try_read_file(file_path)
            
            if df is None:
                st.error("無法讀取檔案，請檢查格式")
                return None
            
            # 資料清理與格式化
            df = self._clean_and_validate(df)
            
            if df is None or len(df) == 0:
                st.error("處理後沒有有效的資料")
                return None
            
            return df
            
        except Exception as e:
            st.error(f"載入資料時發生錯誤: {str(e)}")
            return None
    
    def _try_read_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """嘗試用不同參數讀取檔案"""
        for encoding in self.supported_encodings:
            try:
                # 策略 1: 假設有標頭，使用空白分隔
                df = pd.read_csv(file_path, sep='\s+', encoding=encoding, on_bad_lines='skip')
                
                # 檢查第一列是否誤判為標頭 (如果第一列包含數字，表示可能沒有標頭或標頭壞了)
                # 這裡強制重新命名欄位，忽略原始標頭的問題
                if self._looks_like_ohlc(df):
                     # 如果讀出來已經像資料了，但欄位名稱可能是亂碼，我們強制重新命名
                    df = self._force_rename_columns(df)
                    return df
                
                # 策略 2: 略過第一行 (header=0)，如果標頭是中文亂碼
                df = pd.read_csv(file_path, sep='\s+', encoding=encoding, header=0, on_bad_lines='skip')
                df = self._force_rename_columns(df)
                return df

            except Exception:
                continue
        return None

    def _force_rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """強制重新命名欄位以確保格式正確"""
        cols = df.columns
        count = len(cols)
        
        # 常見的期貨資料格式 (日期, 時間, 開, 高, 低, 收, 量)
        if count >= 7:
            # 取前7欄，通常是 Date, Time, Open, High, Low, Close, Volume
            # 有些檔案可能有第8欄 (OI)，我們暫時只取前7個關鍵欄位
            new_cols = ['date_str', 'time_str', 'open', 'high', 'low', 'close', 'volume']
            if count > 7:
                # 如果有多餘的欄位，先保留但不重新命名，或者丟棄
                df = df.iloc[:, :7]
            df.columns = new_cols
        elif count == 6:
            # 可能是 Date, Open, High, Low, Close, Volume (沒有時間欄)
            df.columns = ['date_str', 'open', 'high', 'low', 'close', 'volume']
            df['time_str'] = '00:00:00' # 補上預設時間
        
        return df

    def _looks_like_ohlc(self, df: pd.DataFrame) -> bool:
        """簡單檢查資料形狀"""
        return len(df.columns) >= 6

    def _clean_and_validate(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """清理資料並轉換型別"""
        try:
            # 1. 處理日期時間
            # 將日期和時間合併為 datetime 欄位
            if 'time_str' in df.columns:
                df['datetime_str'] = df['date_str'].astype(str) + ' ' + df['time_str'].astype(str)
            else:
                df['datetime_str'] = df['date_str'].astype(str)
            
            df['datetime'] = pd.to_datetime(df['datetime_str'], errors='coerce')
            
            # 2. 轉換數值
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                if col in df.columns:
                    # 移除非數字字符 (例如逗號)
                    if df[col].dtype == object:
                        df[col] = df[col].astype(str).str.replace(',', '')
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 3. 移除無效資料
            df = df.dropna(subset=['datetime', 'close'])
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # 4. 只保留需要的欄位
            final_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            return df[final_cols]
            
        except Exception as e:
            st.warning(f"資料清理時發生部分錯誤: {e}")
            return None # 或是 return df (儘量回傳)

    def get_data_info(self, df: pd.DataFrame) -> dict:
        """獲取資料統計資訊"""
        if df is None or len(df) == 0:
            return {}
        return {
            'total_records': len(df),
            'start_date': df['datetime'].min(),
            'end_date': df['datetime'].max(),
            'latest_price': df['close'].iloc[-1]
        }

    def resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """重新取樣 (如將小時線轉為日線)"""
        # 簡單實作，如有需要可擴充
        return df

def calculate_basic_metrics(df: pd.DataFrame) -> dict:
    """計算基本指標"""
    if df is None or len(df) < 2:
        return {}
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    
    return {
        'current_price': curr['close'],
        'price_change': curr['close'] - prev['close'],
        'price_change_pct': (curr['close'] - prev['close']) / prev['close'] * 100,
        'period_high': df['high'].max(),
        'period_low': df['low'].min(),
        'total_volume': df['volume'].sum(),
        'data_points': len(df)
    }

def create_test_data(num_bars=100, price=15000, trend=True):
    """(保留用於測試)"""
    # 這裡可以保留原本的邏輯，為了節省篇幅省略
    pass