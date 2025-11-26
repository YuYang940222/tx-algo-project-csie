"""
資料載入和處理模組
Author: Your Name
Date: 2024

這個模組負責載入和處理TX期貨的OHLCV資料
"""

import pandas as pd
import numpy as np
import os
from typing import Optional, List
import streamlit as st
from pandas.api.types import is_datetime64_any_dtype


class DataLoader:
    """
    資料載入器類別，負責從各種來源載入和處理OHLCV資料
    """
    
    # 預設使用小時資料檔案
    def __init__(self, file_path: str = "output/7652A_Hour.TXT"): 
        """
        初始化資料載入器
        """
        self.file_path = file_path
        self.supported_encodings = ['utf-8', 'utf-8-sig', 'big5', 'gbk', 'cp950', 'latin1']
        
    def load_from_text_file(self, file_path: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        從文字檔載入資料
        """
        if file_path is None:
            file_path = self.file_path
            
        try:
            # 檢查檔案是否存在
            if not os.path.exists(file_path):
                st.error(f"資料檔案不存在: {file_path}")
                return None
            
            # 嘗試不同的編碼格式
            df = self._try_different_encodings(file_path)
            if df is None:
                st.error("無法使用任何支援的編碼格式讀取檔案")
                return None
            
            # 處理欄位名稱和格式 (包括日期時間合併)
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
                # 核心修正：處理所有空白，並讓 pandas 讀取英文標頭
                df = pd.read_csv(
                    file_path, 
                    sep='\s+',             # 允許一個或多個空格作為分隔符
                    encoding=encoding, 
                    on_bad_lines='skip',
                    header=0,               
                    skipinitialspace=True,  # 忽略行首和分隔符後的多餘空白
                    index_col=False         # 確保開頭的空白不會被誤判為索引欄位
                )
                
                # 清理欄位名稱，移除 pandas 讀取後可能殘留的空白
                df.columns = df.columns.str.strip().str.replace(' ', '')
                
                return df
            except (UnicodeDecodeError, Exception):
                continue
        return None
    
    def _process_columns(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """處理欄位名稱和格式"""
        try:
            
            # --- 原始英文欄位名稱映射 ---
            column_mapping = {
                'Date': 'Date', 
                'Time': 'Time',
                'Open': 'open', 
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                # 這裡保留映射，但因 TXT 檔中已移除這兩個欄位，它們不會出現在 df.columns 中
                'Value_Tx': 'turnover',  
                'Count_Tx': 'trade_count' 
            }
            
            # 執行重命名
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

            # --- 合併日期時間欄位 ---
            if 'Date' in df.columns and 'Time' in df.columns:
                # 合併為唯一的 'datetime' 字串
                df['datetime'] = df['Date'].astype(str) + ' ' + df['Time'].astype(str)
                
                # 轉換為 datetime 類型
                df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce') 
                
                # 移除原始欄位和不需要的欄位 (使用 errors='ignore' 確保安全)
                df = df.drop(columns=['Date', 'Time', 'turnover', 'trade_count'], errors='ignore') 
            else:
                 st.error("錯誤：資料載入器找不到 'Date' 和 'Time' 欄位。請檢查 TXT 檔標頭是否正確。")
                 return None
            
            # 確保最後只留下 OHLCV 和 datetime 欄位
            df = df[['datetime', 'open', 'high', 'low', 'close', 'volume']] 
            
            return df
            
        except Exception as e:
            st.error(f"處理欄位時發生錯誤: {str(e)}")
            return None
    
    def _process_datetime(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """處理日期時間欄位 (已在 _process_columns 中處理，此處僅作為檢查)"""
        try:
            if 'datetime' not in df.columns:
                return df
            
            # 再次檢查確保是 datetime 類型
            if not is_datetime64_any_dtype(df['datetime']):
                 df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
            
            nan_count = df['datetime'].isna().sum()
            if nan_count > 0:
                st.warning(f"發現 {nan_count} 個無效的日期時間項目")
            
            return df
            
        except Exception:
            return None 

    
    def _clean_and_validate(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """清理和驗證資料"""
        try:
            # 確保 datetime 欄位已存在並被正確處理
            df = self._process_datetime(df)
            if df is None:
                return None

            # 轉換數值欄位
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce', downcast='float')
            
            # 移除包含NaN值的行
            essential_columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            df = df.dropna(subset=[col for col in essential_columns if col in df.columns])
            
            # 驗證OHLC資料的合理性
            df = self._validate_ohlc(df)
            
            # 按時間排序
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # 檢查必要欄位
            required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                st.error(f"缺少必要欄位: {missing_cols}")
                return None
            
            # 🚨 最終修正：不再將 datetime 設為索引，讓它保持欄位
            
            return df
            
        except Exception as e:
            st.error(f"清理資料時發生錯誤: {str(e)}")
            return None
    
    def _validate_ohlc(self, df: pd.DataFrame) -> pd.DataFrame:
        """驗證OHLC資料的合理性"""
        original_length = len(df)
        
        # 移除不合理的OHLC資料
        df = df[
            (df['high'] >= df['low']) & 
            (df['high'] >= df['open']) & 
            (df['high'] >= df['close']) &
            (df['low'] <= df['open']) & 
            (df['low'] <= df['close']) &
            (df['open'] > 0) &
            (df['high'] > 0) &
            (df['low'] > 0) &
            (df['close'] > 0) &
            (df['volume'] >= 0)
        ]
        
        removed_count = original_length - len(df)
        if removed_count > 0:
            st.warning(f"移除了 {removed_count} 筆不合理的OHLC資料")
        
        return df
    
    def get_data_info(self, df: pd.DataFrame) -> dict:
        """
        獲取資料基本資訊
        """
        if df is None or len(df) == 0:
            return {}
        
        # 這裡需要將 datetime 欄位作為索引來計算 min/max
        if 'datetime' in df.columns:
             df_indexed = df.set_index('datetime')
        else:
             df_indexed = df # 假設它已經是索引了

        return {
            'total_records': len(df_indexed),
            'date_range': {
                'start': df_indexed.index.min(),
                'end': df_indexed.index.max()
            },
            'price_range': {
                'min_low': df_indexed['low'].min(),
                'max_high': df_indexed['high'].max(),
                'current_price': df_indexed['close'].iloc[-1]
            },
            'volume_stats': {
                'total_volume': df_indexed['volume'].sum(),
                'avg_volume': df_indexed['volume'].mean(),
                'max_volume': df_indexed['volume'].max()
            },
            'data_quality': {
                'missing_values': df_indexed.isnull().sum().to_dict(),
                'duplicate_timestamps': df_indexed.index.duplicated().sum()
            }
        }
    
    def filter_data_by_date(self, df: pd.DataFrame, start_date: str = None, 
                           end_date: str = None) -> pd.DataFrame:
        """
        根據日期範圍過濾資料
        """
        if df is None or len(df) == 0:
            return df
        
        filtered_df = df.copy()
        
        # 過濾前先將 datetime 設為索引
        if 'datetime' in filtered_df.columns:
            filtered_df = filtered_df.set_index('datetime')
        
        if start_date:
            start_dt = pd.to_datetime(start_date)
            filtered_df = filtered_df[filtered_df.index >= start_dt]
        
        if end_date:
            end_dt = pd.to_datetime(end_date)
            filtered_df = filtered_df[filtered_df.index <= end_dt]
            
        # 恢復 datetime 欄位
        return filtered_df.reset_index()
    
    def resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        重新取樣資料到不同的時間週期
        """
        if df is None or len(df) == 0:
            return df
            
        # 重新取樣前必須是 datetime index
        if 'datetime' in df.columns:
            df_indexed = df.set_index('datetime')
        else:
            df_indexed = df
        
        df_resampled = df_indexed.resample(timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        return df_resampled.reset_index()


def calculate_basic_metrics(df: pd.DataFrame) -> dict:
    """
    計算基本市場指標
    """
    if df is None or len(df) < 2:
        return {}
    
    # 確保資料是基於 index 排序的
    df_reset = df.reset_index(drop=False)
    
    current_price = df_reset['close'].iloc[-1]
    previous_price = df_reset['close'].iloc[-2]
    
    price_change = current_price - previous_price
    price_change_pct = (price_change / previous_price) * 100
    
    period_high = df_reset['high'].max()
    period_low = df_reset['low'].min()
    period_range = period_high - period_low
    
    total_volume = df_reset['volume'].sum()
    avg_volume = df_reset['volume'].mean()
    current_volume = df_reset['volume'].iloc[-1]
    
    price_changes = df_reset['close'].pct_change().dropna()
    volatility = price_changes.std() * 100
    
    return {
        'current_price': current_price,
        'price_change': price_change,
        'price_change_pct': price_change_pct,
        'period_high': period_high,
        'period_low': period_low,
        'period_range': period_range,
        'total_volume': total_volume,
        'avg_volume': avg_volume,
        'current_volume': current_volume,
        'volatility_pct': volatility,
        'data_points': len(df_reset)
    }

def create_test_data(num_bars: int = 100, start_price: float = 15000.0, 
                    with_trend: bool = True) -> pd.DataFrame:
    """
    創建一個用於測試的模擬 OHLCV DataFrame
    """
    np.random.seed(42)
    dates = pd.date_range('2024-01-01 09:00:00', periods=num_bars, freq='H')
    
    if with_trend:
        trend = np.linspace(0, start_price * 0.1, num_bars)
    else:
        trend = np.zeros(num_bars)
    
    random_walk = np.cumsum(np.random.randn(num_bars) * start_price * 0.005)
    base_prices = start_price + trend + random_walk
    
    opens = base_prices + np.random.randn(num_bars) * start_price * 0.002
    closes = opens + np.random.randn(num_bars) * start_price * 0.003
    
    daily_range = np.abs(np.random.randn(num_bars)) * start_price * 0.01
    highs = np.maximum(opens, closes) + daily_range * 0.6
    lows = np.minimum(opens, closes) - daily_range * 0.4
    
    base_volume = 5000
    volume_variation = np.random.randint(-2000, 3000, num_bars)
    volumes = np.maximum(base_volume + volume_variation, 100)
    
    df = pd.DataFrame({
        'datetime': dates,
        'open': opens.round(0),
        'high': highs.round(0),
        'low': lows.round(0),
        'close': closes.round(0),
        'volume': volumes
    })
    
    return df


if __name__ == "__main__":
    # 測試資料載入器
    print("=== 資料載入器測試 ===")
    
    # 創建測試資料
    test_data = create_test_data(200, 15000, True)
    print(f"創建測試資料: {len(test_data)} 筆")
    
    # 測試基本指標計算
    metrics = calculate_basic_metrics(test_data)
    print(f"\n基本指標:")
    print(f"- 當前價格: {metrics['current_price']:.0f}")
    print(f"- 價格變化: {metrics['price_change']:+.0f} ({metrics['price_change_pct']:+.2f}%)")
    print(f"- 期間高點: {metrics['period_high']:.0f}")
    print(f"- 期間低點: {metrics['period_low']:.0f}")
    print(f"- 總成交量: {metrics['total_volume']:,.0f}")
    print(f"- 波動率: {metrics['volatility_pct']:.2f}%")
    
    # 測試資料載入器（模擬）
    loader = DataLoader()
    data_info = loader.get_data_info(test_data)
    print(f"\n資料資訊:")
    print(f"- 總筆數: {data_info['total_records']}")
    print(f"- 時間範圍: {data_info['date_range']['start']} 到 {data_info['date_range']['end']}")
    print(f"- 價格範圍: {data_info['price_range']['min_low']:.0f} - {data_info['price_range']['max_high']:.0f}")
    
    # 測試資料重新取樣
    resampled_4h = loader.resample_data(test_data, '4H')
    print(f"\n重新取樣到4小時: {len(resampled_4h)} 筆資料")
    
    print("\n測試完成！")