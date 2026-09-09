# Инструкция по сборке EXE-файла

## Готовый EXE-файл
Собранный исполняемый файл находится в папке `dist/MarketMonitor`.

**Размер:** ~80 MB  
**Платформа:** Linux x64 (для Windows/Mac требуется сборка на соответствующей ОС)

## Запуск
```bash
# В Linux
./dist/MarketMonitor

# Файл создаст лог-файл в папке logs/monitor.log
# Работает в фоновом режиме с системным треем (если доступен GUI)
```

## Повторная сборка

### Требования
```bash
pip install pyinstaller pystray Pillow
```

### Команды для сборки

#### Для Windows (создаст .exe файл):
```bash
pyinstaller --onefile --windowed --name "MarketMonitor" launcher.py
```

#### Для Mac:
```bash
pyinstaller --onefile --windowed --name "MarketMonitor" launcher.py
```

#### Для Linux:
```bash
pyinstaller --onefile --windowed --name "MarketMonitor" launcher.py
```

### Опции PyInstaller:
- `--onefile` — упаковать всё в один исполняемый файл
- `--windowed` — скрыть консольное окно (для GUI приложения)
- `--name` — имя выходного файла

## Структура после сборки
```
workspace/
├── launcher.py          # Исходный код лаунчера
├── dist/
│   └── MarketMonitor    # Готовый EXE-файл
├── build/               # Временные файлы сборки
└── logs/                # Логи работы приложения
    └── monitor.log
```

## Особенности работы

### С GUI (Windows/Mac с рабочим столом):
- Приложение запускается в системном трее
- Доступно контекстное меню: Start/Stop/Exit
- Уведомления о событиях мониторинга

### Без GUI (Linux сервер, Docker):
- Работает в консольном режиме
- Логирование в файл `logs/monitor.log`
- Остановка по Ctrl+C

## Настройка
Перед запуском убедитесь, что файлы конфигурации находятся рядом с EXE:
- `data/settings.json` — настройки эндпоинтов
- `.env` или переменные окружения — секреты и параметры

При первом запуске приложение создаст папку `data/` и `logs/` рядом с исполняемым файлом.
