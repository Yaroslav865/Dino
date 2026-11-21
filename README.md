# Dino RL

Обучение динозавра из Chrome T-Rex Runner методом Double DQN.
Состояние — 12 признаков, действия — бег / прыжок / присед, несколько окон
Chrome одновременно (число задаётся в `WINDOWS`).

## Требования

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Chrome или Chromium для Playwright (код запускает `BROWSER_CHANNEL`)

## Установка на другом устройстве

### 1. uv

Windows:

```powershell
winget install --id=astral-sh.uv -e

# или, если есть Python:
python -m pip install uv
```

Linux и macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

# macOS с Homebrew:
brew install uv

# универсальный вариант через pip:
python3 -m pip install uv
```

### 2. Зависимости

```bash
uv sync
```

### 3. Браузер — достаточно одного варианта

**Chrome for Testing (одинаково на Windows, Linux и macOS):**

```bash
uv run playwright install chrome

# Linux: доставить системные библиотеки
uv run playwright install --with-deps chrome
```

В `dino.py`:

```python
BROWSER_CHANNEL = "chrome"
```

**Chromium:**

```bash
uv run playwright install chromium

# Linux: доставить системные библиотеки
uv run playwright install --with-deps chromium
```

В `dino.py`:

```python
BROWSER_CHANNEL = None
```

**Системный Google Chrome** (если он уже стоит):

- Windows: `winget install --id=Google.Chrome -e` или установщик с google.com/chrome;
- macOS: `brew install --cask google-chrome`;
- Debian/Ubuntu:
  ```bash
  wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo apt install ./google-chrome-stable_current_amd64.deb
  ```
- Fedora:
  ```bash
  sudo dnf install https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
  ```

Для системного Chrome оставьте `BROWSER_CHANNEL = "chrome"`.

### 4. Запуск

```bash
uv run dino.py
```

Режим можно переключать флагом или константой `PLAY_BEST`:

```bash
uv run dino.py          # финальный забег по best_dqn.pt
uv run dino.py --train  # обучение
uv run dino.py --play   # принудительно финальный забег
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

## Обучение

```bash
uv run dino.py --train
```

Режим обучения работает как финальный забег, но в нескольких окнах:

- `WINDOWS = 5` — количество окон сохраняется;
- загружаются веса из `best_dqn.pt` (если нет — из `dqn.pt`);
- `TRAIN_GREEDY = True` — эпизоды играются без случайных действий (`epsilon = 0`);
- обучение при этом продолжается: буфер пополняется, веса обновляются;
- лимита на один эпизод нет (`MAX_EPISODE_SECONDS = 0`), общий лимит
  `TIME_LIMIT_MINUTES = 240`;
- каждый эпизод, который прошёл дальше рекорда, сразу сохраняется
  в `best_dqn.pt`.

Если нужно обучение с исследованием, поставьте `TRAIN_GREEDY = False`:
тогда `epsilon` начинается с 0.30 (или 0.05 при загрузке лучшей модели),
эпизод ограничен 300 секундами, а рекорд проверяется отдельными забегами
каждые `RECORD_EVERY` эпизодов.

## Управление и настройки

Все параметры — в начале `dino.py`:

- `WINDOWS` — число одновременных окон Chrome;
- `EPISODES` — лимит эпизодов на все окна;
- `TIME_LIMIT_MINUTES` — лимит времени;
- `TRAIN_GREEDY = True` — обучение без случайных действий;
- `RECORD_EVERY` — проверка рекорда каждые N эпизодов (при `TRAIN_GREEDY = False`);
- `RECORD_ATTEMPT_SECONDS` — лимит проверочного забега (при `TRAIN_GREEDY = False`);
- `RESUME_EPS_START` — старт исследования при загрузке `best_dqn.pt` (0 при `TRAIN_GREEDY = True`, иначе 0.05);
- `HEADLESS = True` — без видимых окон (быстрее, но не видно процесса);
- `EPS_END` / `EPS_DECAY_DECISIONS` — исследование (только при `TRAIN_GREEDY = False`).

Остановка — `Ctrl+C`; в режиме обучения модель сохраняется.

## Результаты

- `results.csv` — строка на каждый валидный эпизод (время, окно, эпизод,
  дистанция, шаги, награда, epsilon, этап, причина, лучшая дистанция).
- `dqn.pt` — последние веса, каждые `SAVE_EVERY` эпизодов и при выходе.
- `best_dqn.pt` — лучшие веса по максимальной дистанции за один эпизод;
  загружается при следующем запуске.

При `TRAIN_GREEDY = True` каждый эпизод играется без случайности, поэтому
новый рекорд сохраняется сразу, а проверочные забеги не нужны.

При `TRAIN_GREEDY = False` каждые `RECORD_EVERY` эпизодов запускается
проверочный забег на копии текущих весов: `epsilon = 0`, без обучения,
до падения или `RECORD_ATTEMPT_SECONDS`. Если он прошёл дальше рекорда,
`best_dqn.pt` обновляется. Обычные обучающие эпизоды с исследованием рекорд
не обновляют. В `results.csv` такие строки помечены `EVAL_DEAD` / `EVAL_TIME`.

При запуске обучения `best_dqn.pt` загружается всегда, если существует.
При `TRAIN_GREEDY = True` исследование не включается; при
`TRAIN_GREEDY = False` оно начинается с `RESUME_EPS_START` и падает до 0.
