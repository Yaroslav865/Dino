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

## Управление и настройки

Все параметры — в начале `dino.py`:

- `WINDOWS` — число одновременных окон Chrome;
- `EPISODES` — лимит эпизодов на все окна;
- `TIME_LIMIT_MINUTES` — лимит времени;
- `RECORD_EVERY` — раз в сколько эпизодов проверять рекорд без исследования;
- `RECORD_ATTEMPT_SECONDS` — лимит проверочного забега;
- `HEADLESS = True` — без видимых окон (быстрее, но не видно процесса);
- `EPS_END` / `EPS_DECAY_DECISIONS` — исследование (сейчас до 0 за 1 млн решений).

Остановка — `Ctrl+C`; в режиме обучения модель сохраняется.

## Результаты

- `results.csv` — строка на каждый валидный эпизод (время, окно, эпизод,
  дистанция, шаги, награда, epsilon, этап, причина, лучшая дистанция).
- `dqn.pt` — последние веса, каждые `SAVE_EVERY` эпизодов и при выходе.
- `best_dqn.pt` — лучшие веса по максимальной дистанции за один эпизод;
  загружается при следующем запуске.

Во время обучения каждые `RECORD_EVERY` эпизодов запускается проверочный
забег на копии текущих весов: `epsilon = 0`, без обучения, до падения или
`RECORD_ATTEMPT_SECONDS`. Если он прошёл дальше рекорда, `best_dqn.pt`
обновляется. В `results.csv` такие строки помечены `EVAL_DEAD` / `EVAL_TIME`.
