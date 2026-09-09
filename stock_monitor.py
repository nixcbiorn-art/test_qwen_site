"""
Модуль для работы с финансовыми данными рынка акций.
Поддерживает получение котировок, расчет индикаторов и нормализацию данных.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import pandas as pd
import pandas_ta as ta
import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class StockQuote:
    """Модель котировки акции."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None


@dataclass
class Candlestick:
    """Модель свечи (OHLCV)."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockDataFetcher:
    """Класс для получения данных об акциях через Yahoo Finance."""
    
    def __init__(self, cache_ttl_seconds: int = 60):
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, tuple[pd.DataFrame, datetime]] = {}
    
    async def fetch_historical_data(
        self, 
        symbol: str, 
        period: str = "1mo", 
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Получить исторические данные по акции.
        
        Args:
            symbol: Тикер акции (например, "AAPL", "GOOGL")
            period: Период данных ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
            interval: Интервал ("1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo")
        
        Returns:
            DataFrame с колонками: Open, High, Low, Close, Adj Close, Volume
        """
        cache_key = f"{symbol}_{period}_{interval}"
        
        # Проверка кэша
        if cache_key in self._cache:
            df, cached_at = self._cache[cache_key]
            if (datetime.now() - cached_at).total_seconds() < self.cache_ttl_seconds:
                logger.info(f"Using cached data for {symbol}")
                return df.copy()
        
        try:
            logger.info(f"Fetching data for {symbol} (period={period}, interval={interval})")
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No data received for {symbol}")
                return pd.DataFrame()
            
            # Сохранение в кэш
            self._cache[cache_key] = (df.copy(), datetime.now())
            logger.info(f"Successfully fetched {len(df)} records for {symbol}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def fetch_multiple_stocks(
        self, 
        symbols: List[str], 
        period: str = "1mo", 
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """Получить данные по нескольким акциям параллельно."""
        tasks = [
            self.fetch_historical_data(symbol, period, interval) 
            for symbol in symbols
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        data_dict = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {symbol}: {result}")
                data_dict[symbol] = pd.DataFrame()
            else:
                data_dict[symbol] = result
        
        return data_dict
    
    def normalize_to_quotes(self, df: pd.DataFrame, symbol: str) -> List[StockQuote]:
        """Преобразовать DataFrame в список StockQuote."""
        if df.empty:
            return []
        
        quotes = []
        for idx, row in df.iterrows():
            quote = StockQuote(
                symbol=symbol,
                timestamp=idx.to_pydatetime() if hasattr(idx, 'to_pydatetime') else idx,
                open=float(row.get('Open', 0)),
                high=float(row.get('High', 0)),
                low=float(row.get('Low', 0)),
                close=float(row.get('Close', 0)),
                volume=int(row.get('Volume', 0)),
                adjusted_close=float(row.get('Adj Close', 0)) if 'Adj Close' in row else None
            )
            quotes.append(quote)
        
        return quotes


class TechnicalAnalyzer:
    """Класс для расчета технических индикаторов."""
    
    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитать набор технических индикаторов.
        
        Добавляет колонки:
        - SMA_20, SMA_50: Скользящие средние
        - EMA_12, EMA_26: Экспоненциальные скользящие средние
        - RSI_14: Индекс относительной силы
        - MACD_12_26_9: MACD линия
        - BB_upper, BB_lower: Полосы Боллинджера
        - Volume_SMA: Скользящая средняя объема
        """
        if df.empty:
            return df
        
        df_copy = df.copy()
        
        # Убедиться, что имена колонок в правильном формате для pandas_ta
        df_copy.columns = df_copy.columns.str.strip().str.upper()
        
        # Скользящие средние
        df_copy['SMA_20'] = ta.sma(df_copy['CLOSE'], length=20)
        df_copy['SMA_50'] = ta.sma(df_copy['CLOSE'], length=50)
        df_copy['EMA_12'] = ta.ema(df_copy['CLOSE'], length=12)
        df_copy['EMA_26'] = ta.ema(df_copy['CLOSE'], length=26)
        
        # RSI
        df_copy['RSI_14'] = ta.rsi(df_copy['CLOSE'], length=14)
        
        # MACD
        macd = ta.macd(df_copy['CLOSE'], fast=12, slow=26, signal=9)
        df_copy = pd.concat([df_copy, macd], axis=1)
        
        # Полосы Боллинджера
        bbands = ta.bbands(df_copy['CLOSE'], length=20, std=2)
        df_copy = pd.concat([df_copy, bbands], axis=1)
        
        # Объем
        df_copy['VOLUME_SMA'] = ta.sma(df_copy['VOLUME'], length=20)
        
        logger.info("Technical indicators calculated successfully")
        return df_copy
    
    @staticmethod
    def generate_signals(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Сгенерировать торговые сигналы на основе индикаторов.
        
        Returns:
            Словарь с сигналами: trend, momentum, volatility, recommendation
        """
        if df.empty or len(df) < 50:
            return {"trend": "unknown", "momentum": "neutral", "volatility": "unknown", "recommendation": "hold"}
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        signals = {}
        
        # Тренд (по SMA)
        if pd.notna(latest.get('SMA_20')) and pd.notna(latest.get('SMA_50')):
            if latest['SMA_20'] > latest['SMA_50']:
                signals['trend'] = 'bullish'
            elif latest['SMA_20'] < latest['SMA_50']:
                signals['trend'] = 'bearish'
            else:
                signals['trend'] = 'neutral'
        else:
            signals['trend'] = 'unknown'
        
        # Моментум (по RSI)
        rsi = latest.get('RSI_14')
        if pd.notna(rsi):
            if rsi > 70:
                signals['momentum'] = 'overbought'
            elif rsi < 30:
                signals['momentum'] = 'oversold'
            else:
                signals['momentum'] = 'neutral'
        else:
            signals['momentum'] = 'neutral'
        
        # Волатильность (по полосам Боллинджера)
        if pd.notna(latest.get('BBU_20_2.0')) and pd.notna(latest.get('BBL_20_2.0')):
            bandwidth = (latest['BBU_20_2.0'] - latest['BBL_20_2.0']) / latest['CLOSE']
            if bandwidth > 0.1:
                signals['volatility'] = 'high'
            elif bandwidth < 0.05:
                signals['volatility'] = 'low'
            else:
                signals['volatility'] = 'normal'
        else:
            signals['volatility'] = 'unknown'
        
        # Рекомендация
        recommendation = 'hold'
        if signals['trend'] == 'bullish' and signals['momentum'] == 'oversold':
            recommendation = 'strong_buy'
        elif signals['trend'] == 'bullish' and signals['momentum'] == 'neutral':
            recommendation = 'buy'
        elif signals['trend'] == 'bearish' and signals['momentum'] == 'overbought':
            recommendation = 'strong_sell'
        elif signals['trend'] == 'bearish' and signals['momentum'] == 'neutral':
            recommendation = 'sell'
        
        signals['recommendation'] = recommendation
        signals['timestamp'] = datetime.now()
        
        logger.info(f"Signals generated: {signals['recommendation']}")
        return signals


class StockMonitor:
    """Основной класс мониторинга акций с интеграцией в систему."""
    
    def __init__(self):
        self.fetcher = StockDataFetcher()
        self.analyzer = TechnicalAnalyzer()
        self._watchlist: List[str] = []
    
    def add_to_watchlist(self, symbol: str):
        """Добавить акцию в список наблюдения."""
        if symbol not in self._watchlist:
            self._watchlist.append(symbol)
            logger.info(f"Added {symbol} to watchlist")
    
    def remove_from_watchlist(self, symbol: str):
        """Удалить акцию из списка наблюдения."""
        if symbol in self._watchlist:
            self._watchlist.remove(symbol)
            logger.info(f"Removed {symbol} from watchlist")
    
    async def update_watchlist(self, period: str = "1d", interval: str = "1m") -> Dict[str, Any]:
        """
        Обновить данные по всем акциям из watchlist.
        
        Returns:
            Словарь с данными, индикаторами и сигналами по каждой акции
        """
        if not self._watchlist:
            logger.warning("Watchlist is empty")
            return {}
        
        results = {}
        
        # Получаем данные по всем акциям
        data = await self.fetcher.fetch_multiple_stocks(
            self._watchlist, 
            period=period, 
            interval=interval
        )
        
        for symbol, df in data.items():
            if df.empty:
                continue
            
            # Рассчитываем индикаторы
            df_with_indicators = self.analyzer.calculate_indicators(df)
            
            # Генерируем сигналы
            signals = self.analyzer.generate_signals(df_with_indicators)
            
            # Преобразуем в котировки
            quotes = self.fetcher.normalize_to_quotes(df_with_indicators, symbol)
            
            results[symbol] = {
                'raw_data': df,
                'indicators': df_with_indicators,
                'signals': signals,
                'latest_quote': quotes[-1] if quotes else None,
                'quotes': quotes
            }
        
        logger.info(f"Updated watchlist: {len(results)} symbols processed")
        return results
    
    def get_plot_data(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Подготовить данные для отрисовки графика.
        
        Returns:
            Словарь с данными для Plotly
        """
        if df.empty:
            return {}
        
        df_copy = df.copy()
        df_copy.index = pd.to_datetime(df_copy.index)
        
        return {
            'symbol': symbol,
            'timestamps': df_copy.index.tolist(),
            'open': df_copy['Open'].tolist(),
            'high': df_copy['High'].tolist(),
            'low': df_copy['Low'].tolist(),
            'close': df_copy['Close'].tolist(),
            'volume': df_copy['Volume'].tolist(),
            'sma_20': df_copy.get('SMA_20', pd.Series()).tolist(),
            'sma_50': df_copy.get('SMA_50', pd.Series()).tolist(),
            'rsi': df_copy.get('RSI_14', pd.Series()).tolist()
        }
