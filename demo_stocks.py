"""
Пример использования модулей для работы с акциями.
Демонстрирует получение данных, расчет индикаторов и отрисовку графиков.
"""
import asyncio
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from stock_monitor import StockMonitor, StockDataFetcher, TechnicalAnalyzer
from stock_visualizer import StockChartGenerator


async def main():
    """Основная функция демонстрации."""
    
    # Список акций для анализа
    watchlist = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
    
    print("=" * 60)
    print("DEMO: Stock Market Analysis Tools")
    print("=" * 60)
    
    # 1. Инициализация монитора
    monitor = StockMonitor()
    
    # Добавление акций в список наблюдения
    print("\n[1] Добавление акций в список наблюдения...")
    for symbol in watchlist:
        monitor.add_to_watchlist(symbol)
        print(f"  ✓ Добавлен {symbol}")
    
    # 2. Получение данных и расчет индикаторов
    print("\n[2] Получение данных и расчет технических индикаторов...")
    results = await monitor.update_watchlist(period="3mo", interval="1d")
    
    if not results:
        print("  ✗ Не удалось получить данные")
        return
    
    print(f"  ✓ Обработано {len(results)} акций")
    
    # 3. Вывод сигналов по каждой акции
    print("\n[3] Торговые сигналы:")
    print("-" * 60)
    for symbol, data in results.items():
        signals = data['signals']
        latest_quote = data['latest_quote']
        
        if latest_quote:
            print(f"\n{symbol}:")
            print(f"  Цена: ${latest_quote.close:.2f}")
            print(f"  Тренд: {signals.get('trend', 'unknown')}")
            print(f"  Моментум: {signals.get('momentum', 'neutral')}")
            print(f"  Волатильность: {signals.get('volatility', 'unknown')}")
            print(f"  Рекомендация: {signals.get('recommendation', 'hold').upper()}")
    
    # 4. Отрисовка графиков
    print("\n[4] Генерация графиков...")
    
    # Выбираем первую акцию для демонстрации
    demo_symbol = watchlist[0]
    demo_data = results[demo_symbol]
    df = demo_data['indicators']
    signals = demo_data['signals']
    
    generator = StockChartGenerator()
    
    # Свечной график
    print(f"  → Создание свечного графика для {demo_symbol}...")
    candlestick_fig = generator.create_candlestick_chart(
        df, 
        symbol=demo_symbol,
        title=f"{demo_symbol} Candlestick Chart",
        show_sma=True,
        show_volume=True
    )
    generator.save_chart(candlestick_fig, f"{demo_symbol}_candlestick", format='html')
    print(f"  ✓ Сохранено: {demo_symbol}_candlestick.html")
    
    # RSI график
    print(f"  → Создание графика RSI для {demo_symbol}...")
    rsi_fig = generator.create_rsi_chart(df, symbol=demo_symbol)
    generator.save_chart(rsi_fig, f"{demo_symbol}_rsi", format='html')
    print(f"  ✓ Сохранено: {demo_symbol}_rsi.html")
    
    # MACD график
    print(f"  → Создание графика MACD для {demo_symbol}...")
    macd_fig = generator.create_macd_chart(df, symbol=demo_symbol)
    generator.save_chart(macd_fig, f"{demo_symbol}_macd", format='html')
    print(f"  ✓ Сохранено: {demo_symbol}_macd.html")
    
    # Комплексный дашборд
    print(f"  → Создание торгового дашборда для {demo_symbol}...")
    dashboard_fig = generator.create_dashboard(df, symbol=demo_symbol, signals=signals)
    generator.save_chart(dashboard_fig, f"{demo_symbol}_dashboard", format='html')
    print(f"  ✓ Сохранено: {demo_symbol}_dashboard.html")
    
    # 5. Экспорт данных в CSV
    print("\n[5] Экспорт данных в CSV...")
    df.to_csv(f"{demo_symbol}_data.csv")
    print(f"  ✓ Сохранено: {demo_symbol}_data.csv")
    
    print("\n" + "=" * 60)
    print("DEMO завершена успешно!")
    print(f"Графики сохранены в текущей директории.")
    print("=" * 60)
    
    # Пример получения данных в реальном времени (для частоты обновления)
    print("\n[БОНУС] Обновление данных в реальном времени...")
    print("Мониторинг продолжается... (нажмите Ctrl+C для остановки)")
    
    try:
        iteration = 0
        while iteration < 3:  # 3 итерации для демонстрации
            await asyncio.sleep(5)  # Пауза 5 секунд
            iteration += 1
            
            # Быстрое обновление (используем кэш)
            quick_results = await monitor.update_watchlist(period="1d", interval="1m")
            
            if quick_results:
                print(f"\n[Обновление {iteration}] Данные обновлены:")
                for symbol, data in quick_results.items():
                    if data['latest_quote']:
                        price = data['latest_quote'].close
                        change = ((price - data['quotes'][0].close) / data['quotes'][0].close * 100) if len(data['quotes']) > 1 else 0
                        print(f"  {symbol}: ${price:.2f} ({change:+.2f}%)")
    except KeyboardInterrupt:
        print("\nМониторинг остановлен пользователем.")


if __name__ == "__main__":
    asyncio.run(main())
