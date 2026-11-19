# Dino RL

Обучение динозавра из Chrome T-Rex Runner методом Double DQN.
Состояние — 12 признаков, действия — бег / прыжок / присед, несколько окон
Chrome одновременно (число задаётся в `WINDOWS`).

## Требования

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Google Chrome (код запускает `channel="chrome"`)

## Установка на другом устройстве

```powershell
# 1. Поставить uv (Windows)
winget install --id=astral-sh.uv -e

# 2. Поставить Google Chrome, если его нет
winget install --id=Google.Chrome -e

# 3. В папке проекта
uv sync
uv run python dino.py
```

Если Chrome устанавливать не хочется, можно поставить Chromium для Playwright
и заменить в `dino.py` `channel="chrome"` на `channel=None`:

```powershell
uv run playwright install chromium
```

## Управление и настройки

Все параметры — в начале `dino.py`:

- `WINDOWS` — число одновременных окон Chrome;
- `EPISODES` — лимит эпизодов на все окна;
- `TIME_LIMIT_MINUTES` — лимит времени;
- `HEADLESS = True` — без видимых окон (быстрее, но не видно процесса);
- `EPS_END` / `EPS_DECAY_DECISIONS` — исследование (сейчас до 0 за 1 млн решений).

Остановка — `Ctrl+C`; модель сохраняется.

## Результаты

- `results.csv` — строка на каждый валидный эпизод (время, окно, эпизод,
  дистанция, шаги, награда, epsilon, этап, причина, лучшая средняя).
- `dqn.pt` — последние веса, каждые `SAVE_EVERY` эпизодов и при выходе.
- `best_dqn.pt` — лучшие веса по средней дистанции за 50 эпизодов;
  загружается при следующем запуске.

В репозитории лежат `dqn.pt`, `best_dqn.pt` и `results.csv` с прошлого запуска.
Чтобы начать обучение с нуля, удалите эти три файла.

Окна нельзя сворачивать: скрытые окна ставятся на паузу и не пишут результаты.
