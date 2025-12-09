"""
資料載入和處理模組
Author: Your Name
Date: 2024

這個模組負責載入和處理TX期貨的OHLCV資料
"""

import pandas as pd
import numpy as np
import os
from typing import Optional, List, Dict
import streamlit as st


class DataLoader:
    """
    資料載入器類別，負責從各種來源載入和處理OHLCV資料
    """
    
    def __init__(self, file_path: str = "output/kline_60min.txt"):
        """
        初始化資料載入器
        
        Args:
            file_path: 預設的資料檔案路徑
        """
        self.file_path = file_path
        self.supported_encodings = ['utf-8', 'utf-8-sig', 'big5', 'gbk', 'cp950', 'latin1']
        
    def load_from_text_file(self, file_path: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        從文字檔載入資料
        
        Args:
            file_path: 檔案路徑，如果為None則使用預設路徑
            
        Returns:
            處理後的DataFrame，如果載入失敗則返回None
        """
        if file_path is None:
            file_path = self.file_path
            
        try:
            # 檢查檔案是否存在
            if not os.path.exists(file_path):
                # 嘗試在 output 資料夾尋找
                if os.path.exists(os.path.join("output", file_path)):
                    file_path = os.path.join("output", file_path)
                elif os.path.exists(os.path.join(os.getcwd(), file_path)):
                    pass # 就在當前目錄
                else:
                    st.error(f"資料檔案不存在: {file_path}")
                    return None
            
            # 嘗試不同的編碼格式讀取
            df = self._try_different_encodings(file_path)
            if df is None:
                st.error("無法使用任何支援的編碼格式讀取檔案")
                return None
            
            # 處理欄位名稱和格式 (修正重點：增加對英文標題的判斷)
            df = self._process_columns(df)
            if df is None:
                return None
            
            # 資料清理和驗證
            df = self._clean_and_validate(df)
            if df is None or len(df) == 0:
                st.error("處理後沒有有效的資料")
                return None
            
            st.success(f"成功載入 {len(df)} 筆資料")
            return df
            
        except Exception as e:
            st.error(f"載入資料時發生錯誤: {str(e)}")
            return None
    
    def _try_different_encodings(self, file_path: str) -> Optional[pd.DataFrame]:
        """嘗試不同編碼格式讀取檔案"""
        for encoding in self.supported_encodings:
            try:
                # 修正：使用 sep='\s+' 來處理空白鍵對齊的檔案
                # engine='python' 比較穩定
                df = pd.read_csv(file_path, sep='\s+', encoding=encoding, on_bad_lines='skip')
                # 簡單檢查：如果讀出來只有1欄，可能分隔符號不對，繼續試
                if len(df.columns) < 3:
                    continue
                return df
            except (UnicodeDecodeError, Exception):
                continue
        return None
    
    def _process_columns(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """處理欄位名稱和格式 (智慧判斷版)"""
        try:
            # 1. 先標準化目前的欄位名稱 (轉小寫、去空白)
            current_cols = [str(c).lower().strip() for c in df.columns]
            
            # 2. 判斷是否已經包含英文標題 (針對 7652A_Hour.TXT)
            # 檢查關鍵字是否存在於欄位中
            has_date = any('date' in c for c in current_cols) or any('time' in c for c in current_cols)
            has_open = any('open' in c for c in current_cols)
            has_close = any('close' in c for c in current_cols)
            
            if has_date and has_open and has_close:
                # 已經有正確標題，進行映射
                col_map = {}
                for col in df.columns:
                    c_lower = str(col).lower().strip()
                    if 'date' in c_lower: col_map[col] = 'date'
                    elif 'time' in c_lower: col_map[col] = 'time'
                    elif 'open' in c_lower: col_map[col] = 'open'
                    elif 'high' in c_lower: col_map[col] = 'high'
                    elif 'low' in c_lower: col_map[col] = 'low'
                    elif 'close' in c_lower: col_map[col] = 'close'
                    elif 'vol' in c_lower: col_map[col] = 'volume'
                
                df.rename(columns=col_map, inplace=True)
                
            else:
                # 沒有標題，依照欄位數量猜測 (相容舊程式邏輯)
                if len(df.columns) == 8:
                    df.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'volume', 'turnover']
                elif len(df.columns) == 7:
                    # 這裡是舊程式的 bug 點：7欄可能是 [Date, Time, O, H, L, C, V] 也可能是 [Date, O, H, L, C, V, Turnover]
                    # 我們透過檢查第2欄的數據類型來判斷
                    # 如果第2欄包含 ":" (像 09:45:00)，那它就是時間
                    sample_val = str(df.iloc[0, 1])
                    if ':' in sample_val:
                        df.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
                    else:
                        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'turnover']
                elif len(df.columns) == 6:
                    df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                else:
                    st.error(f"不支援的欄位數量: {len(df.columns)}")
                    return None
            
            # 處理日期時間欄位 (合併 Date + Time)
            df = self._process_datetime(df)
            
            # 最後確認必要欄位名稱是否都叫 datetime, open, high, low, close, volume
            # 如果還是中文，這裡做最後一次轉換
            chinese_map = {
                '日期': 'datetime', '完整時間': 'datetime',
                '開盤': 'open', '最高': 'high', '最低': 'low', '收盤': 'close',
                '成交量': 'volume'
            }
            df.rename(columns=chinese_map, inplace=True)
            
            return df
            
        except Exception as e:
            st.error(f"處理欄位時發生錯誤: {str(e)}")
            return None
    
    def _process_datetime(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """處理日期時間欄位"""
        try:
            # 情況 A: 有 date 和 time 兩欄 -> 合併
            if 'date' in df.columns and 'time' in df.columns:
                # 清理日期格式 (將 2023/05/04 轉為標準格式)
                date_str = df['date'].astype(str).str.replace('/', '-').str.replace('.', '-')
                time_str = df['time'].astype(str)
                df['datetime'] = pd.to_datetime(date_str + ' ' + time_str, errors='coerce')
                
            # 情況 B: 只有 date 一欄 (可能包含時間)
            elif 'date' in df.columns:
                df['datetime'] = pd.to_datetime(df['date'], errors='coerce')
                
            else:
                # 嘗試找看看有沒有叫 '日期' 的
                if '日期' in df.columns and '時間' in df.columns:
                     df['datetime'] = pd.to_datetime(df['日期'].astype(str) + ' ' + df['時間'].astype(str), errors='coerce')
                elif '日期' in df.columns:
                    df['datetime'] = pd.to_datetime(df['日期'], errors='coerce')
                else:
                    st.error("找不到日期欄位")
                    return None
            
            # 移除轉換失敗的日期 (NaT)
            if df['datetime'].isna().sum() > 0:
                # st.warning(f"發現 {df['datetime'].isna().sum()} 筆無效日期，已移除")
                df = df.dropna(subset=['datetime'])
            
            return df
            
        except Exception as e:
            st.error(f"處理日期時間時發生錯誤: {str(e)}")
            return None
    
    def _clean_and_validate(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """清理和驗證資料"""
        try:
            # 轉換數值欄位
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                if col in df.columns:
                    # 強制轉數值，無法轉的變 NaN
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 移除包含NaN值的行
            essential_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            df = df.dropna(subset=[col for col in essential_columns if col in df.columns])
            
            # 按時間排序
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # 檢查必要欄位是否存在
            required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                st.error(f"缺少必要欄位: {missing_cols}")
                return None
            
            return df
            
        except Exception as e:
            st.error(f"清理資料時發生錯誤: {str(e)}")
            return None
    
    def _validate_ohlc(self, df: pd.DataFrame) -> pd.DataFrame:
        """驗證OHLC資料的合理性 (保留原本的邏輯)"""
        # 這裡為了避免太嚴格的驗證把所有資料刪光，先只做簡單過濾
        # 例如 High 必須 >= Low
        if len(df) > 0:
            df = df[df['high'] >= df['low']]
        return df
    
    def get_data_info(self, df: pd.DataFrame) -> dict:
        """獲取資料基本資訊"""
        if df is None or len(df) == 0:
            return {}
        
        return {
            'total_records': len(df),
            'date_range': {
                'start': df['datetime'].min(),
                'end': df['datetime'].max()
            },
            'price_range': {
                'min_low': df['low'].min(),
                'max_high': df['high'].max(),
                'current_price': df['close'].iloc[-1]
            },
            'volume_stats': {
                'total_volume': df['volume'].sum(),
                'avg_volume': df['volume'].mean(),
                'max_volume': df['volume'].max()
            }
        }
    
    def filter_data_by_date(self, df: pd.DataFrame, start_date: str = None, 
                           end_date: str = None) -> pd.DataFrame:
        """根據日期範圍過濾資料"""
        if df is None or len(df) == 0:
            return df
        
        filtered_df = df.copy()
        if start_date:
            filtered_df = filtered_df[filtered_df['datetime'] >= pd.to_datetime(start_date)]
        if end_date:
            filtered_df = filtered_df[filtered_df['datetime'] <= pd.to_datetime(end_date)]
        
        return filtered_df
    
    def resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """重新取樣資料到不同的時間週期"""
        if df is None or len(df) == 0:
            return df
        
        df_resampled = df.set_index('datetime').resample(timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        
        return df_resampled


def calculate_basic_metrics(df: pd.DataFrame) -> dict:
    """計算基本的市場指標"""
    if df is None or len(df) < 2:
        return {}
    
    current_price = df['close'].iloc[-1]
    previous_price = df['close'].iloc[-2]
    
    price_change = current_price - previous_price
    price_change_pct = (price_change / previous_price) * 100
    
    return {
        'current_price': current_price,
        'price_change': price_change,
        'price_change_pct': price_change_pct,
        'period_high': df['high'].max(),
        'period_low': df['low'].min(),
        'period_range': df['high'].max() - df['low'].min(),
        'total_volume': df['volume'].sum(),
        'avg_volume': df['volume'].mean(),
        'current_volume': df['volume'].iloc[-1],
        'volatility_pct': df['close'].pct_change().std() * 100,
        'data_points': len(df)
    }


def create_test_data(num_bars: int = 100, start_price: float = 15000.0, 
                    with_trend: bool = True) -> pd.DataFrame:
    """創建測試用的OHLCV資料"""
    # 僅作佔位符，保留接口
    dates = pd.date_range('2024-01-01', periods=num_bars, freq='H')
    df = pd.DataFrame({
        'datetime': dates,
        'open': [start_price]*num_bars,
        'high': [start_price]*num_bars,
        'low': [start_price]*num_bars,
        'close': [start_price]*num_bars,
        'volume': [1000]*num_bars
    })
    return df

# 程式進入點 (測試用)
if __name__ == "__main__":
    loader = DataLoader()
    print("DataLoader module loaded.")