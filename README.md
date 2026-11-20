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

Режим можно переключать флагом или константой `PLAY_BEST`:

```powershell
uv run python dino.py          # финальный забег по best_dqn.pt
uv run python dino.py --train  # обучение
uv run python dino.py --play   # принудительно финальный забег
```

Если Chrome устанавливать не хочется, можно поставить Chromium для Playwright
и заменить в `dino.py` `channel="chrome"` на `channel=None`:

```powershell
uv run playwright install chromium
```

## Финальный забег

По умолчанию включён `PLAY_BEST = True`:

- одно окно Chrome (`WINDOWS = 1`);
- загружается `best_dqn.pt`, случайные действия отключены (`epsilon = 0`);
- обучение не идёт, буфер не пополняется;
- нет лимита времени на эпизод (`MAX_EPISODE_SECONDS = 0`), забег идёт
  до падения или `Ctrl+C`;
- результат пишется в `results.csv`; если он превысит рекорд,
  обновится `best_distance` в `best_dqn.pt`.

Чтобы снова обучать, поставьте `PLAY_BEST = False` в начале `dino.py`
или запустите с флагом `--train`.

## Управление и настройки

Все параметры — в начале `dino.py`:

- `WINDOWS` — число одновременных окон Chrome;
- `EPISODES` — лимит эпизодов на все окна;
- `TIME_LIMIT_MINUTES` — лимит времени;
- `HEADLESS = True` — без видимых окон (быстрее, но не видно процесса);
- `EPS_END` / `EPS_DECAY_DECISIONS` — исследование (сейчас до 0 за 1 млн решений).

Остановка — `Ctrl+C`; в режиме обучения модель сохраняется.

## Результаты

- `results.csv` — строка на каждый валидный эпизод (время, окно, эпизод,
  дистанция, шаги, награда, epsilon, этап, причина, лучшая дистанция).
- `dqn.pt` — последние веса, каждые `SAVE_EVERY` эпизодов и при выходе.
- `best_dqn.pt` — лучшие веса по максимальной дистанции за один эпизод;
  загружается при следующем запуске.
