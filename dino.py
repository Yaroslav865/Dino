import os
import random
import threading
import time

import numpy as np
from playwright.sync_api import sync_playwright

GAME_URL = "https://wayou.github.io/t-rex-runner/"

# ---------------- параметры обучения ----------------
WINDOWS = 4              # сколько окон Chrome обучаются одновременно
HEADLESS = False         # True - без окон
EPISODES = 400           # всего эпизодов на все окна
ALPHA = 0.15             # скорость обучения
GAMMA = 0.97             # дисконт
EPSILON = 0.10           # случайные действия в начале
EPSILON_MIN = 0.02       # случайные действия в конце
STEP_DELAY = 0.02        # пауза между решениями, сек
MAX_STEPS = 0            # 0 = без лимита, эпизод до падения
MAX_EPISODE_SECONDS = 300
SAVE_EVERY = 10
MODEL_FILE = "q_table.npy"

# Действия: 0 = бежать, 1 = прыгать, 2 = присесть
ACTIONS = 3
ACTION_NAMES = ["НЕ ПРЫГАТЬ", "ПРЫГАТЬ", "ПРИСЕСТЬ"]

# Классы препятствий
NO_OBSTACLE = 0
CACTUS_SMALL = 1
CACTUS_LARGE = 2
BIRD_LOW = 3      # у земли - надо прыгать
BIRD_MID = 4      # средняя высота - надо присесть
BIRD_HIGH = 5     # высокая - можно бежать
CLASS_NAMES = {
    NO_OBSTACLE: "нет препятствия",
    CACTUS_SMALL: "кактус малый",
    CACTUS_LARGE: "кактус большой",
    BIRD_LOW: "птица низко (прыжок)",
    BIRD_MID: "птица средне (присед)",
    BIRD_HIGH: "птица высоко (пропуск)",
}

q_table = {}
q_lock = threading.Lock()
episode_lock = threading.Lock()
episodes_started = 0
stop_event = threading.Event()

STATE_JS = """
() => {
    const runner = window.Runner && window.Runner.instance_;
    if (!runner) return {status: "NO_RUNNER"};
    if (runner.crashed) return {status: "DEAD"};
    if (!runner.playing) return {status: "NOT_PLAYING"};

    const dino = runner.tRex;
    const list = runner.horizon.obstacles || [];
    const obstacles = [];
    for (let i = 0; i < list.length && obstacles.length < 2; i++) {
        const o = list[i];
        if (o.xPos + o.width <= dino.xPos - 20) continue;
        obstacles.push({x: o.xPos, w: o.width, y: o.yPos, t: o.typeConfig.type});
    }

    return {
        status: "OK",
        x: dino.xPos,
        y: dino.yPos,
        speed: runner.currentSpeed,
        jumping: dino.jumping,
        ducking: dino.ducking,
        dist: runner.distanceRan,
        obstacles: obstacles
    };
}
"""


def load_q_table():
    global q_table
    if os.path.exists(MODEL_FILE):
        q_table = np.load(MODEL_FILE, allow_pickle=True).item()
        print(f"Загружена сохранённая Q-таблица: {len(q_table)} состояний.")
    else:
        q_table = {}
        print("Q-таблица создана с нуля.")


def save_q_table():
    with q_lock:
        data = dict(q_table)
    np.save(MODEL_FILE, data)
    print(f"Q-таблица сохранена в файл {MODEL_FILE} ({len(data)} состояний)")


def next_episode():
    global episodes_started
    with episode_lock:
        if episodes_started >= EPISODES:
            return None
        episodes_started += 1
        return episodes_started


def read_game(page):
    try:
        return page.evaluate(STATE_JS)
    except Exception as error:
        return {"status": "ERROR", "error": str(error)}


def obstacle_class(obstacle):
    if obstacle["t"] == "PTERODACTYL":
        y = obstacle["y"]
        if y <= 60:
            return BIRD_HIGH
        if y <= 92:
            return BIRD_MID
        return BIRD_LOW
    if obstacle["t"] == "CACTUS_SMALL":
        return CACTUS_SMALL
    return CACTUS_LARGE


def distance_bucket(dt):
    if dt <= 4:
        return 0
    if dt <= 8:
        return 1
    if dt <= 12:
        return 2
    if dt <= 17:
        return 3
    if dt <= 24:
        return 4
    return 5


def speed_bucket(speed):
    if speed < 8.0:
        return 0
    if speed < 10.5:
        return 1
    return 2


def get_state(raw):
    """Состояние: (класс, dt в кадрах, скорость, второе препятствие, приседает)."""
    if raw["status"] != "OK":
        return None, raw["status"]

    speed = max(float(raw["speed"]), 6.0)
    obstacles = raw["obstacles"]
    ducking = int(raw["ducking"])

    if not obstacles:
        return (NO_OBSTACLE, 5, speed_bucket(speed), 0, ducking), "чисто"

    obstacle = obstacles[0]
    dt = (obstacle["x"] - (raw["x"] + 40)) / speed
    cls = obstacle_class(obstacle)

    # Второе препятствие близко - нельзя приземляться между ними.
    second = 0
    if len(obstacles) > 1:
        gap = (obstacles[1]["x"] - (obstacle["x"] + obstacle["w"])) / speed
        if gap <= 25:
            second = 1

    state = (cls, distance_bucket(dt), speed_bucket(speed), second, ducking)
    info = f"{CLASS_NAMES[cls]} dt={dt:.1f} speed={raw['speed']:.1f}"
    return state, info


def choose_action(state, epsilon):
    if random.random() < epsilon:
        return random.randrange(ACTIONS)
    with q_lock:
        values = q_table.setdefault(state, [0.0, 0.0, 0.0])
        return int(np.argmax(values))


def update_q_table(state, action, reward, next_state):
    with q_lock:
        values = q_table.setdefault(state, [0.0, 0.0, 0.0])
        if next_state is None:
            best_next = 0.0
        else:
            best_next = max(q_table.setdefault(next_state, [0.0, 0.0, 0.0]))
        values[action] += ALPHA * (reward + GAMMA * best_next - values[action])


def start_game(page):
    deadline = time.time() + 10.0
    while time.time() < deadline:
        raw = read_game(page)
        if raw["status"] == "OK":
            return True
        try:
            page.keyboard.press("Space")
        except Exception:
            pass
        time.sleep(0.3)
    return False


def epsilon_for(episode):
    progress = min(1.0, episode / max(1, EPISODES * 0.6))
    return EPSILON + (EPSILON_MIN - EPSILON) * progress


def play_episode(page, episode, epsilon):
    if not start_game(page):
        print(f"окно {episode % WINDOWS}: игра не запустилась")
        return

    raw = read_game(page)
    state, info = get_state(raw)
    if state is None:
        return

    duck_held = False
    total_reward = 0
    started = time.time()
    step = 0

    while True:
        if stop_event.is_set():
            break
        if MAX_STEPS and step >= MAX_STEPS:
            break
        if MAX_EPISODE_SECONDS and time.time() - started > MAX_EPISODE_SECONDS:
            break

        action = choose_action(state, epsilon)

        # Применяем действие
        try:
            if action == 1:
                if duck_held:
                    page.keyboard.up("ArrowDown")
                    duck_held = False
                if not raw["jumping"]:
                    page.keyboard.press("Space")
            elif action == 2:
                if not duck_held:
                    page.keyboard.down("ArrowDown")
                    duck_held = True
            else:
                if duck_held:
                    page.keyboard.up("ArrowDown")
                    duck_held = False
        except Exception:
            break

        time.sleep(STEP_DELAY)

        next_raw = read_game(page)
        next_state, next_info = get_state(next_raw)
        step += 1

        if next_state is None:
            reward = -100
            update_q_table(state, action, reward, None)
            total_reward += reward
            print(
                f"эпизод {episode:4d} | упал на шаге {step:4d} | "
                f"{info} | награда {total_reward} | eps {epsilon:.2f}"
            )
            if duck_held:
                page.keyboard.up("ArrowDown")
            return

        reward = 1
        update_q_table(state, action, reward, next_state)
        total_reward += reward
        state = next_state
        raw = next_raw

    if duck_held:
        page.keyboard.up("ArrowDown")
    print(
        f"эпизод {episode:4d} | шагов {step:4d} | "
        f"дистанция {int(raw.get('dist', 0))} | награда {total_reward} | eps {epsilon:.2f}"
    )


def window_worker(window_id):
    print(f"окно {window_id}: запуск Chrome")
    position = f"--window-position={(window_id % 2) * 720},{(window_id // 2) * 340}"
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=HEADLESS,
            args=[
                "--mute-audio",
                position,
                "--window-size=700,320",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=CalculateNativeWinOcclusion",
            ],
        )
        page = browser.new_page(viewport={"width": 700, "height": 260})
        page.goto(GAME_URL, wait_until="domcontentloaded")
        time.sleep(1.5)
        # Игра встаёт на паузу при потере фокуса - для параллельных окон это смертельно.
        page.evaluate("() => { Runner.instance_.onVisibilityChange = function () {}; }")

        while not stop_event.is_set():
            episode = next_episode()
            if episode is None:
                break
            play_episode(page, episode, epsilon_for(episode))
            if episode % SAVE_EVERY == 0:
                save_q_table()

        browser.close()
    print(f"окно {window_id}: завершено")


def print_q_table():
    print("\nИтоговая Q-таблица:")
    print("Действия: 0=бежать, 1=прыгать, 2=присесть")
    print("dt: 0-4, 4-8, 8-12, 12-17, 17-24, 24+ кадров")

    with q_lock:
        data = dict(q_table)

    for cls in (CACTUS_SMALL, CACTUS_LARGE, BIRD_LOW, BIRD_MID, BIRD_HIGH):
        print(f"\n{CLASS_NAMES[cls]}:")
        for spb in range(3):
            actions = []
            for db in range(6):
                votes = [0, 0, 0]
                for second in (0, 1):
                    for ducking in (0, 1):
                        values = data.get((cls, db, spb, second, ducking))
                        if values is not None:
                            votes[int(np.argmax(values))] += 1
                actions.append(int(np.argmax(votes)))
            print(
                f"  скорость {spb} | действия {actions} | "
                f"лучшее в корзине dt"
            )


def main():
    print("Запускаем программу...")
    load_q_table()

    threads = []
    for window_id in range(WINDOWS):
        thread = threading.Thread(target=window_worker, args=(window_id,), daemon=True)
        thread.start()
        threads.append(thread)
        time.sleep(1.0)

    try:
        while any(thread.is_alive() for thread in threads):
            for thread in threads:
                thread.join(timeout=0.5)
    except KeyboardInterrupt:
        print("\nОстановка по Ctrl+C...")
        stop_event.set()
        for thread in threads:
            thread.join(timeout=10)

    save_q_table()
    print_q_table()
    print("\nОБУЧЕНИЕ ЗАВЕРШЕНО!")


if __name__ == "__main__":
    main()