"""
Модуль для визуализации финансовых данных.
Создает интерактивные графики котировок с техническими индикаторами.
"""
import logging
from typing import Optional, Dict, Any, List

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


class StockChartGenerator:
    """Генератор интерактивных графиков для акций."""
    
    @staticmethod
    def create_candlestick_chart(
        df: pd.DataFrame,
        symbol: str,
        title: Optional[str] = None,
        show_sma: bool = True,
        show_volume: bool = True,
        height: int = 800
    ) -> go.Figure:
        """
        Создать свечной график с объемами и скользящими средними.
        
        Args:
            df: DataFrame с данными (должен содержать колонки: Open, High, Low, Close, Volume)
            symbol: Тикер акции
            title: Заголовок графика
            show_sma: Показывать ли скользящие средние (SMA_20, SMA_50)
            show_volume: Показывать ли объемы
            height: Высота графика в пикселях
        
        Returns:
            Plotly Figure объект
        """
        if df.empty:
            logger.warning("Cannot create chart: empty DataFrame")
            return go.Figure()
        
        # Подготовка данных
        df_copy = df.copy()
        df_copy.index = pd.to_datetime(df_copy.index)
        df_copy = df_copy.sort_index()
        
        # Нормализация имен колонок
        df_copy.columns = df_copy.columns.str.strip().str.upper()
        
        # Создание подграфиков
        if show_volume:
            rows = 2
            row_heights = [0.7, 0.3]
        else:
            rows = 1
            row_heights = [1.0]
        
        fig = make_subplots(
            rows=rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=row_heights,
            subplot_titles=(title or f"{symbol} Price Chart",) + (("Volume",) if show_volume else ())
        )
        
        # Свечной график
        fig.add_trace(
            go.Candlestick(
                x=df_copy.index,
                open=df_copy['OPEN'],
                high=df_copy['HIGH'],
                low=df_copy['LOW'],
                close=df_copy['CLOSE'],
                name='Price',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350'
            ),
            row=1,
            col=1
        )
        
        # Скользящие средние
        if show_sma:
            if 'SMA_20' in df_copy.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_copy.index,
                        y=df_copy['SMA_20'],
                        name='SMA 20',
                        line=dict(color='#ff9800', width=1.5),
                        mode='lines'
                    ),
                    row=1,
                    col=1
                )
            
            if 'SMA_50' in df_copy.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df_copy.index,
                        y=df_copy['SMA_50'],
                        name='SMA 50',
                        line=dict(color='#2196f3', width=1.5),
                        mode='lines'
                    ),
                    row=1,
                    col=1
                )
        
        # Объемы
        if show_volume and 'VOLUME' in df_copy.columns:
            colors = ['#26a69a' if df_copy['CLOSE'].iloc[i] >= df_copy['OPEN'].iloc[i] else '#ef5350' 
                     for i in range(len(df_copy))]
            
            fig.add_trace(
                go.Bar(
                    x=df_copy.index,
                    y=df_copy['VOLUME'],
                    name='Volume',
                    marker_color=colors,
                    opacity=0.7
                ),
                row=2,
                col=1
            )
        
        # Настройка макета
        fig.update_layout(
            height=height,
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
            template='plotly_dark',
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            )
        )
        
        # Настройка осей
        fig.update_xaxes(
            title_text="Date",
            type='date',
            tickformat='%Y-%m-%d %H:%M',
            rangeslider_visible=False
        )
        
        fig.update_yaxes(
            title_text="Price ($)",
            row=1,
            col=1
        )
        
        if show_volume:
            fig.update_yaxes(
                title_text="Volume",
                row=2,
                col=1
            )
        
        logger.info(f"Candlestick chart created for {symbol}")
        return fig
    
    @staticmethod
    def create_rsi_chart(
        df: pd.DataFrame,
        symbol: str,
        period: int = 14,
        height: int = 300
    ) -> go.Figure:
        """
        Создать график RSI (Relative Strength Index).
        
        Args:
            df: DataFrame с данными (должен содержать RSI_14 или аналогичную колонку)
            symbol: Тикер акции
            period: Период RSI
            height: Высота графика
        
        Returns:
            Plotly Figure объект
        """
        if df.empty:
            logger.warning("Cannot create RSI chart: empty DataFrame")
            return go.Figure()
        
        df_copy = df.copy()
        df_copy.index = pd.to_datetime(df_copy.index)
        df_copy = df_copy.sort_index()
        df_copy.columns = df_copy.columns.str.strip().str.upper()
        
        # Поиск колонки RSI
        rsi_col = None
        for col in df_copy.columns:
            if 'RSI' in col:
                rsi_col = col
                break
        
        if rsi_col is None:
            logger.warning(f"RSI column not found in DataFrame")
            return go.Figure()
        
        fig = make_subplots(rows=1, cols=1, subplot_titles=(f"{symbol} RSI ({period})",))
        
        # Линия RSI
        fig.add_trace(
            go.Scatter(
                x=df_copy.index,
                y=df_copy[rsi_col],
                name='RSI',
                line=dict(color='#9c27b0', width=2),
                mode='lines'
            )
        )
        
        # Зоны перекупленности/перепроданности
        fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", annotation_text="Overbought (70)")
        fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", annotation_text="Oversold (30)")
        fig.add_hline(y=50, line_dash="dot", line_color="#757575", opacity=0.5)
        
        # Настройка макета
        fig.update_layout(
            height=height,
            hovermode='x unified',
            template='plotly_dark',
            showlegend=False
        )
        
        fig.update_xaxes(
            title_text="Date",
            type='date',
            tickformat='%Y-%m-%d %H:%M'
        )
        
        fig.update_yaxes(
            title_text="RSI",
            range=[0, 100]
        )
        
        logger.info(f"RSI chart created for {symbol}")
        return fig
    
    @staticmethod
    def create_macd_chart(
        df: pd.DataFrame,
        symbol: str,
        height: int = 400
    ) -> go.Figure:
        """
        Создать график MACD.
        
        Args:
            df: DataFrame с данными (должен содержать MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9)
            symbol: Тикер акции
            height: Высота графика
        
        Returns:
            Plotly Figure объект
        """
        if df.empty:
            logger.warning("Cannot create MACD chart: empty DataFrame")
            return go.Figure()
        
        df_copy = df.copy()
        df_copy.index = pd.to_datetime(df_copy.index)
        df_copy = df_copy.sort_index()
        df_copy.columns = df_copy.columns.str.strip().str.upper()
        
        # Поиск колонок MACD
        macd_line = None
        macd_signal = None
        macd_hist = None
        
        for col in df_copy.columns:
            if 'MACD' in col:
                if 'MACDH' in col or 'MACD_HIST' in col:
                    macd_hist = col
                elif 'MACDS' in col or 'MACD_SIGNAL' in col:
                    macd_signal = col
                elif 'MACD' == col or col.startswith('MACD_'):
                    macd_line = col
        
        if not all([macd_line, macd_signal, macd_hist]):
            logger.warning("MACD columns not found in DataFrame")
            return go.Figure()
        
        fig = make_subplots(rows=1, cols=1, subplot_titles=(f"{symbol} MACD",))
        
        # Линия MACD
        fig.add_trace(
            go.Scatter(
                x=df_copy.index,
                y=df_copy[macd_line],
                name='MACD Line',
                line=dict(color='#2196f3', width=2),
                mode='lines'
            )
        )
        
        # Сигнальная линия
        fig.add_trace(
            go.Scatter(
                x=df_copy.index,
                y=df_copy[macd_signal],
                name='Signal Line',
                line=dict(color='#ff9800', width=2),
                mode='lines'
            )
        )
        
        # Гистограмма
        colors = ['#26a69a' if val >= 0 else '#ef5350' for val in df_copy[macd_hist]]
        fig.add_trace(
            go.Bar(
                x=df_copy.index,
                y=df_copy[macd_hist],
                name='Histogram',
                marker_color=colors,
                opacity=0.7
            )
        )
        
        # Настройка макета
        fig.update_layout(
            height=height,
            hovermode='x unified',
            template='plotly_dark',
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            )
        )
        
        fig.update_xaxes(
            title_text="Date",
            type='date',
            tickformat='%Y-%m-%d %H:%M'
        )
        
        fig.update_yaxes(title_text="MACD")
        
        logger.info(f"MACD chart created for {symbol}")
        return fig
    
    @staticmethod
    def create_dashboard(
        df: pd.DataFrame,
        symbol: str,
        signals: Optional[Dict[str, Any]] = None
    ) -> go.Figure:
        """
        Создать комплексную панель с графиками цены, объемов, RSI и MACD.
        
        Args:
            df: DataFrame с данными и индикаторами
            symbol: Тикер акции
            signals: Словарь с торговыми сигналами
        
        Returns:
            Plotly Figure объект с дашбордом
        """
        if df.empty:
            logger.warning("Cannot create dashboard: empty DataFrame")
            return go.Figure()
        
        df_copy = df.copy()
        df_copy.index = pd.to_datetime(df_copy.index)
        df_copy = df_copy.sort_index()
        df_copy.columns = df_copy.columns.str.strip().str.upper()
        
        # Создание подграфиков: Цена (2 ряда), RSI, MACD
        fig = make_subplots(
            rows=4,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=[0.5, 0.15, 0.2, 0.15],
            subplot_titles=(
                f"{symbol} Price & Volume",
                "RSI (14)",
                "MACD (12, 26, 9)",
                ""
            )
        )
        
        # 1. Свечной график
        fig.add_trace(
            go.Candlestick(
                x=df_copy.index,
                open=df_copy['OPEN'],
                high=df_copy['HIGH'],
                low=df_copy['LOW'],
                close=df_copy['CLOSE'],
                name='Price',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350'
            ),
            row=1,
            col=1
        )
        
        # SMA
        if 'SMA_20' in df_copy.columns:
            fig.add_trace(
                go.Scatter(x=df_copy.index, y=df_copy['SMA_20'], name='SMA 20',
                          line=dict(color='#ff9800', width=1.5), mode='lines'),
                row=1, col=1
            )
        if 'SMA_50' in df_copy.columns:
            fig.add_trace(
                go.Scatter(x=df_copy.index, y=df_copy['SMA_50'], name='SMA 50',
                          line=dict(color='#2196f3', width=1.5), mode='lines'),
                row=1, col=1
            )
        
        # Объемы
        if 'VOLUME' in df_copy.columns:
            colors = ['#26a69a' if df_copy['CLOSE'].iloc[i] >= df_copy['OPEN'].iloc[i] else '#ef5350' 
                     for i in range(len(df_copy))]
            fig.add_trace(
                go.Bar(x=df_copy.index, y=df_copy['VOLUME'], name='Volume',
                      marker_color=colors, opacity=0.7),
                row=1, col=1
            )
        
        # 2. RSI
        rsi_col = next((col for col in df_copy.columns if 'RSI' in col), None)
        if rsi_col:
            fig.add_trace(
                go.Scatter(x=df_copy.index, y=df_copy[rsi_col], name='RSI',
                          line=dict(color='#9c27b0', width=2), mode='lines'),
                row=2, col=1
            )
            fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", row=2, col=1)
        
        # 3. MACD
        macd_line = next((col for col in df_copy.columns if col == 'MACD' or col.startswith('MACD_')), None)
        macd_signal = next((col for col in df_copy.columns if 'MACDS' in col or 'MACD_SIGNAL' in col), None)
        macd_hist = next((col for col in df_copy.columns if 'MACDH' in col or 'MACD_HIST' in col), None)
        
        if all([macd_line, macd_signal, macd_hist]):
            fig.add_trace(
                go.Scatter(x=df_copy.index, y=df_copy[macd_line], name='MACD',
                          line=dict(color='#2196f3', width=2), mode='lines'),
                row=3, col=1
            )
            fig.add_trace(
                go.Scatter(x=df_copy.index, y=df_copy[macd_signal], name='Signal',
                          line=dict(color='#ff9800', width=2), mode='lines'),
                row=3, col=1
            )
            hist_colors = ['#26a69a' if val >= 0 else '#ef5350' for val in df_copy[macd_hist]]
            fig.add_trace(
                go.Bar(x=df_copy.index, y=df_copy[macd_hist], name='Hist',
                      marker_color=hist_colors, opacity=0.7),
                row=3, col=1
            )
        
        # 4. Информация о сигналах
        if signals:
            recommendation = signals.get('recommendation', 'hold')
            trend = signals.get('trend', 'unknown')
            momentum = signals.get('momentum', 'neutral')
            
            info_text = (
                f"<b>Recommendation:</b> {recommendation.upper()}<br>"
                f"<b>Trend:</b> {trend}<br>"
                f"<b>Momentum:</b> {momentum}<br>"
                f"<b>Last Update:</b> {df_copy.index[-1].strftime('%Y-%m-%d %H:%M')}"
            )
            
            fig.add_annotation(
                text=info_text,
                align="left",
                showarrow=False,
                xref='paper',
                yref='paper',
                x=0.02,
                y=0.02,
                bordercolor="#c7c7c7",
                borderwidth=1,
                borderpad=4,
                bgcolor="rgba(0,0,0,0.8)",
                font=dict(size=12, color="white")
            )
        
        # Общий макет
        fig.update_layout(
            height=1000,
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
            template='plotly_dark',
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            ),
            title=dict(
                text=f"{symbol} Trading Dashboard",
                x=0.5,
                xanchor='center',
                font=dict(size=20, color='white')
            )
        )
        
        # Настройка осей
        fig.update_xaxes(title_text="Date", type='date', tickformat='%Y-%m-%d %H:%M')
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=1, col=1, secondary_y=True)
        fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
        fig.update_yaxes(title_text="MACD", row=3, col=1)
        
        logger.info(f"Dashboard created for {symbol}")
        return fig
    
    @staticmethod
    def save_chart(fig: go.Figure, filename: str, format: str = 'html'):
        """
        Сохранить график в файл.
        
        Args:
            fig: Plotly Figure объект
            filename: Имя файла (без расширения)
            format: Формат файла ('html', 'png', 'jpeg', 'pdf', 'svg')
        """
        try:
            if format == 'html':
                fig.write_html(f"{filename}.html", include_plotlyjs='cdn', full_html=True)
            else:
                fig.write_image(f"{filename}.{format}", engine="kaleido")
            
            logger.info(f"Chart saved to {filename}.{format}")
        except Exception as e:
            logger.error(f"Error saving chart: {e}")
            raise
