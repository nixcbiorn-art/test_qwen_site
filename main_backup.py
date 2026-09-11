"""Entry point."""

from monitor import run_monitoring

if __name__ == "__main__":
    print("=" * 60)
    print("Парсер и монитор данных")
    print("=" * 60)
    print("\nПеред запуском:")
    print("1. pip install -r requirements.txt")
    print("2. playwright install")
    print("3. Отредактируй config.py")
    print("4. Адаптируй селекторы в auth.py")
    print("=" * 60)
    input("\nНажми Enter для запуска...")
    run_monitoring()
