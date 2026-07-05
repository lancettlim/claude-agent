#!/usr/bin/env python3
"""Animated ASCII fireworks for the terminal. No dependencies beyond curses.

Run:  python3 fireworks.py
Quit: q or Ctrl+C
"""
import curses
import random
import time
from dataclasses import dataclass, field

GRAVITY = 0.06
FRAME_DELAY = 0.03
TRAIL_CHARS = ".:*+#@"


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: int
    char: str = "*"

    def step(self, dt: float) -> None:
        self.vy += GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt


@dataclass
class Rocket:
    x: float
    y: float
    vy: float
    target_y: float
    color: int
    trail: list = field(default_factory=list)

    def step(self, dt: float) -> bool:
        """Advance; return True once it has reached apex and should explode."""
        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail.pop(0)
        self.y += self.vy * dt
        return self.y <= self.target_y


def make_rocket(width: int, height: int, color: int) -> Rocket:
    x = random.uniform(width * 0.1, width * 0.9)
    target_y = random.uniform(height * 0.1, height * 0.5)
    return Rocket(x=x, y=float(height - 1), vy=-random.uniform(18, 24), target_y=target_y, color=color)


def explode(rocket: Rocket, colors: list) -> list:
    n = random.randint(30, 60)
    particles = []
    speed_base = random.uniform(6, 11)
    shape = random.choice(["ring", "burst", "willow"])
    for i in range(n):
        angle = (2 * 3.14159265 * i / n) + random.uniform(-0.1, 0.1)
        speed = speed_base * (1.0 if shape != "burst" else random.uniform(0.4, 1.2))
        vx = speed * curses_cos(angle)
        vy = speed * curses_sin(angle) * (0.6 if shape == "willow" else 1.0)
        life = random.uniform(1.2, 2.2) if shape != "willow" else random.uniform(2.0, 3.2)
        color = rocket.color if random.random() > 0.15 else random.choice(colors)
        particles.append(Particle(x=rocket.x, y=rocket.y, vx=vx, vy=vy, life=life, color=color))
    return particles


def curses_cos(angle: float) -> float:
    import math
    return math.cos(angle)


def curses_sin(angle: float) -> float:
    import math
    return math.sin(angle)


def setup_colors() -> list:
    curses.start_color()
    curses.use_default_colors()
    palette = [
        curses.COLOR_RED, curses.COLOR_GREEN, curses.COLOR_YELLOW,
        curses.COLOR_BLUE, curses.COLOR_MAGENTA, curses.COLOR_CYAN, curses.COLOR_WHITE,
    ]
    for i, fg in enumerate(palette, start=1):
        curses.init_pair(i, fg, -1)
    return list(range(1, len(palette) + 1))


def main(stdscr) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(0)
    colors = setup_colors()

    height, width = stdscr.getmaxyx()
    rockets: list[Rocket] = []
    particles: list[Particle] = []
    last_launch = 0.0
    start = time.time()

    banner = "Happy belated 4th of July!"

    try:
        while True:
            ch = stdscr.getch()
            if ch in (ord("q"), ord("Q")):
                break

            new_h, new_w = stdscr.getmaxyx()
            if (new_h, new_w) != (height, width):
                height, width = new_h, new_w

            now = time.time()
            if now - last_launch > random.uniform(0.4, 1.1) and len(rockets) < 4:
                rockets.append(make_rocket(width, height, random.choice(colors)))
                last_launch = now

            stdscr.erase()

            still_flying = []
            for r in rockets:
                if r.step(1.0):
                    particles.extend(explode(r, colors))
                else:
                    still_flying.append(r)
                    for tx, ty in r.trail:
                        safe_addch(stdscr, int(ty), int(tx), height, width, "|", r.color)
                    safe_addch(stdscr, int(r.y), int(r.x), height, width, "^", r.color)
            rockets = still_flying

            still_alive = []
            for p in particles:
                p.step(1.0)
                if p.life > 0 and 0 <= p.y < height - 1:
                    idx = min(len(TRAIL_CHARS) - 1, int(p.life / 2.4 * len(TRAIL_CHARS)))
                    safe_addch(stdscr, int(p.y), int(p.x), height, width, TRAIL_CHARS[idx], p.color)
                    still_alive.append(p)
            particles = still_alive

            if int(now - start) % 2 == 0:
                col = max(0, (width - len(banner)) // 2)
                try:
                    stdscr.addstr(0, col, banner, curses.A_BOLD)
                except curses.error:
                    pass

            stdscr.refresh()
            time.sleep(FRAME_DELAY)
    except KeyboardInterrupt:
        pass


def safe_addch(stdscr, y: int, x: int, height: int, width: int, ch: str, color: int) -> None:
    if 0 <= y < height and 0 <= x < width:
        try:
            stdscr.addstr(y, x, ch, curses.color_pair(color))
        except curses.error:
            pass


if __name__ == "__main__":
    curses.wrapper(main)
