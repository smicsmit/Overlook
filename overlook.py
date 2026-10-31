#!/usr/bin/env python3
"""
overlook — your terminal, breathing.

A living terminal scene: twinkling stars, a moon, slow clouds drifting
through the star field, a village across the water with lit windows that
flicker, reflections shimmering below, fireflies, the occasional
shooting star — and a small fox on the hill, watching it all, tail
flicking now and then.

Interactive:
  SPACE            call a shooting star
  ARROWS / hjkl    become a firefly (one bright one answers to you)
  f                greet the fox
  b                send a quiet pulse through the village
  m                sketch a constellation
  ?                show or hide the hint line (it fades on its own after a minute)
  click the water  drop a ripple
  click a window   turn its light on or off
  click the sky    a shooting star starts there
  q / Ctrl+C       leave

Stdlib only (curses). Run:  python3 overlook.py
"""

import curses
import math
import random
import time

# rotating lines for the bottom of the screen — quiet ones
LINES = [
    "It's okay to laugh. We can find humor in everything.",
    "But I kept arriving.",
    "Then we left it unopened.",
    "The body is not fooled.",
    "What is missing is not restored.",
    "I stop translating.",
    "Only space, shaped exactly like you.",
    "Most honest thinking happens on the fox's shift.",
    "It still doesn't calculate turtles.",
    "I loved her the way ruin loves architecture — for the promise of collapse.",
    "The body knows no loyalty more complete than leaning over absence.",
    "We ate the brownies in a different world.",
    "I pedaled slower than I needed to.",
    "If I scream right now nobody will come. Not because nobody hears. Because they do.",
    "Close enough that she could leave me quickly.",
    "I measure her growing up in absences I didn't witness.",
    "She stopped asking. I didn't notice when.",
    "Case status: open.",
]

HINT = "space: meteor · arrows: firefly · f: greet fox · b: village pulse · m: constellation · click: interact · ?: hide hints · q: leave"

FOX_A = [
    r" /\ /\ ",
    r"(  V  )",
    r" \ o.o ",
    r"  \_/\~",
    r" __||   ",
    r"(__)|__ ",
]
FOX_B = [
    r" /\ /\ ",
    r"(  V  )",
    r" \ o.o ",
    r"  \_/ ~",
    r" __||   ",
    r"(__)|__ ",
]

MOON = [
    " .--. ",
    "(    )",
    " '--' ",
]


class Star:
    def __init__(self, w, sky_h):
        self.x = random.randrange(w)
        self.y = random.randrange(max(1, sky_h))
        self.phase = random.uniform(0, math.tau)
        self.speed = random.uniform(0.5, 2.0)

    def char(self, t):
        b = 0.5 + 0.5 * math.sin(t * self.speed + self.phase)
        return "." if b < 0.4 else ("+" if b < 0.75 else "*")


class Cloud:
    SHAPES = [
        ["  ~~~  ",
         " ~~~~~ "],
        [" ~~~~~",
         "~~~~~~~"],
        ["   ~~~  ",
         "  ~~~~~  "],
        ["  ~~~~",
         " ~~~~~~"],
    ]

    def __init__(self, w, sky_h, x=None):
        self.x = float(-18 if x is None else x)
        self.y = random.randint(1, max(1, sky_h - 2))
        self.speed = random.uniform(0.25, 0.7)
        self.shape = random.choice(self.SHAPES)

    def step(self, dt):
        self.x += self.speed * dt

    def offscreen(self, w):
        return self.x > w + max(len(row) for row in self.shape)


class Fly:
    def __init__(self, w, h):
        self.x = random.uniform(0, w - 1)
        self.y = random.uniform(h * 0.55, h - 3)
        self.a = random.uniform(0, math.tau)
        self.on = random.random() < 0.7

    def step(self, w, h):
        self.a += random.uniform(-0.6, 0.6)
        self.x = max(0, min(w - 1, self.x + math.cos(self.a) * 0.7))
        self.y = max(h * 0.5, min(h - 3, self.y + math.sin(self.a) * 0.3))
        if random.random() < 0.02:
            self.on = not self.on


def build_village(w, horizon):
    """Return (houses, windows): houses are silhouette rects, windows are
    (x, y, lit) cells just above the horizon."""
    houses, windows = [], []
    x = 2
    while x < w - 6:
        hw = random.randint(4, 9)
        hh = random.randint(2, 4)
        houses.append((x, horizon - hh, hw, hh))
        for _ in range(random.randint(1, 3)):
            wx = x + random.randint(0, hw - 1)
            wy = horizon - random.randint(1, hh)
            windows.append([wx, wy, random.random() < 0.8])
        x += hw + random.randint(1, 4)
    return houses, windows


def init_colors():
    """Set up colors when the terminal supports them; otherwise use plain text."""
    try:
        curses.start_color()
        curses.use_default_colors()
        for pair, color in enumerate((
            curses.COLOR_WHITE, curses.COLOR_BLUE, curses.COLOR_YELLOW,
            curses.COLOR_CYAN, curses.COLOR_RED, curses.COLOR_MAGENTA,
        ), start=1):
            curses.init_pair(pair, color, -1)
        return {
            "BRIGHT": curses.color_pair(1), "DIM": curses.color_pair(2),
            "WTR": curses.color_pair(2), "WIN": curses.color_pair(3),
            "WTL": curses.color_pair(4), "FOX": curses.color_pair(5),
            "TXT": curses.color_pair(6),
        }
    except curses.error:
        return {name: 0 for name in ("BRIGHT", "DIM", "WTR", "WIN", "WTL", "FOX", "TXT")}


def main(stdscr):
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    stdscr.nodelay(True)
    try:
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
    except curses.error:
        pass
    colors = init_colors()
    BRIGHT, DIM = colors["BRIGHT"], colors["DIM"]
    WTR, WIN, WTL = colors["WTR"], colors["WIN"], colors["WTL"]
    FOX, TXT = colors["FOX"], colors["TXT"]

    rng = random.Random()
    t0 = time.time()
    last_size = None
    stars, houses, windows, flies = [], [], [], []
    clouds = []
    meteor = None           # [x, y, life]
    next_meteor = time.time() + rng.uniform(4, 10)
    next_cloud = time.time() + rng.uniform(8, 20)
    line_idx = 0
    line_since = time.time()
    horizon = 0
    # interactive state
    ripples = []            # [x, depth, age]
    sparkles = []           # [x, y, age] rising from the fox
    fox_party_until = 0.0   # fox flicks fast while now < this
    village_pulse_at = None # time the quiet pulse began
    constellation = None    # [star indices, start time]
    dawn_started = False
    hint_visible = True     # fades after the first minute unless ? pins it
    hint_pinned = False
    you = None              # [x, y] once the user takes a firefly

    while True:
        h, w = stdscr.getmaxyx()
        if (h, w) != last_size:
            last_size = (h, w)
            if h > 14 and w > 40:
                horizon = int(h * 0.62)
                stars = [Star(w, max(1, horizon - 6)) for _ in range(w * horizon // 28)]
                houses, windows = build_village(w, horizon)
                flies = [Fly(w, h) for _ in range(14)]
                clouds = [
                    Cloud(w, max(1, horizon - 6), x=rng.uniform(0, w))
                    for _ in range(rng.randint(1, 3))
                ]
                ripples, sparkles = [], []
                constellation = None
                you = None
            else:
                stars, houses, windows, flies, clouds = [], [], [], [], []
        if h <= 14 or w <= 40:
            stdscr.erase()
            stdscr.addstr(0, 0, "overlook needs a bigger window, friend."[:max(0, w - 1)])
            stdscr.refresh()
            if stdscr.getch() in (ord("q"), 27):
                return
            time.sleep(0.1)
            continue

        t = time.time() - t0
        now = time.time()
        # one full cycle — night, dawn, brief day, dusk — every 3 minutes
        cycle_t = t % 180.0
        if cycle_t < 60:
            dawn = 0.0
        elif cycle_t < 100:
            dawn = (cycle_t - 60) / 40.0
        elif cycle_t < 130:
            dawn = 1.0
        elif cycle_t < 170:
            dawn = 1.0 - (cycle_t - 130) / 40.0
        else:
            dawn = 0.0
        stdscr.erase()

        # step and spawn clouds
        for c in clouds:
            c.step(0.09)
        clouds = [c for c in clouds if not c.offscreen(w)]
        if now >= next_cloud and len(clouds) < 4:
            clouds.append(Cloud(w, max(1, horizon - 6)))
            next_cloud = now + rng.uniform(30, 80)

        # sky: stars fade as dawn arrives
        star_visibility = max(0.0, 1.0 - dawn * 1.2)
        for s in stars:
            if rng.random() > star_visibility:
                continue
            try:
                star_char = s.char(t)
                stdscr.addch(s.y, s.x, star_char,
                             BRIGHT if star_char == "*" else DIM)
            except curses.error:
                pass

        # a brief constellation links a few nearby stars
        if constellation is not None:
            star_ids, started = constellation
            age = now - started
            if age >= 5.0:
                constellation = None
            else:
                points = [(stars[i].x, stars[i].y) for i in star_ids
                          if i < len(stars)]
                for (x1, y1), (x2, y2) in zip(points, points[1:]):
                    steps = max(abs(x2 - x1), abs(y2 - y1), 1)
                    for step in range(steps + 1):
                        x = round(x1 + (x2 - x1) * step / steps)
                        y = round(y1 + (y2 - y1) * step / steps)
                        try:
                            stdscr.addch(y, x, ".", BRIGHT | curses.A_DIM)
                        except curses.error:
                            pass

        # clouds — drawn over stars, under moon; they thin out at dawn
        for c in clouds:
            if dawn > 0.75 and rng.random() < (dawn - 0.75) * 2:
                continue
            for row_i, row in enumerate(c.shape):
                cy = c.y + row_i
                for col_i, ch in enumerate(row):
                    if ch != ' ':
                        cx = int(c.x) + col_i
                        if 0 <= cy < horizon - 1 and 0 <= cx < w - 1:
                            try:
                                stdscr.addch(cy, cx, ch, DIM)
                            except curses.error:
                                pass

        # moon, upper right
        mx, my = w - 12, 2
        if dawn < 0.85:
            for i, row in enumerate(MOON):
                try:
                    stdscr.addstr(my + i, mx, row, BRIGHT)
                except curses.error:
                    pass

        # shooting star
        if dawn < 0.8 and meteor is None and now >= next_meteor:
            meteor = [rng.randrange(5, max(6, w - 25)), rng.randrange(1, 5), 0]
        if meteor is not None:
            mx2, my2, life = meteor
            trail = "*"
            for k in range(5):
                try:
                    stdscr.addch(my2 + k // 2, mx2 - k, trail if k == 0 else ".",
                                 BRIGHT if k < 2 else DIM)
                except curses.error:
                    pass
            meteor = [mx2 + 2, my2 + 1, life + 1]
            if meteor[0] >= w - 2 or meteor[2] > 14:
                meteor = None
                next_meteor = now + rng.uniform(6, 16)

        # village silhouettes + windows
        for hx, hy, hw, hh in houses:
            row = "#" * hw
            for yy in range(max(0, hy), min(horizon, h - 1)):
                try:
                    stdscr.addstr(yy, hx, row[:max(0, w - hx - 1)], DIM)
                except curses.error:
                    pass
        pulse_radius = None
        if village_pulse_at is not None:
            pulse_age = now - village_pulse_at
            if pulse_age >= 2.4:
                village_pulse_at = None
            else:
                pulse_radius = pulse_age * max(1, w) / 2.4
        dimmed_idx = set()
        for wi, win in enumerate(windows):
            if rng.random() < 0.004:
                win[2] = not win[2]
            dimmed = (pulse_radius is not None and
                      abs(win[0] - w / 2) < pulse_radius and
                      pulse_radius - abs(win[0] - w / 2) < 5)
            if dimmed:
                dimmed_idx.add(wi)
            if win[2] and not dimmed:
                try:
                    stdscr.addch(win[1], win[0], "*", WIN)
                except curses.error:
                    pass

        # water: horizon line + shimmer under lit windows
        for x in range(w):
            try:
                stdscr.addch(horizon, x, "~" if (x + int(t * 2)) % 7 else " ", WTR)
            except curses.error:
                pass
        lit_cols = [win[0] for wi, win in enumerate(windows)
                    if win[2] and wi not in dimmed_idx]
        water_depth = max(0, h - horizon - 3)
        for cx in lit_cols:
            for _ in range(max(1, water_depth // 3)):
                depth = rng.randint(1, max(1, water_depth))
                if rng.random() < 0.42 / math.sqrt(depth):
                    x = cx + rng.randint(-1, 1)
                    if 0 <= x < w:
                        try:
                            stdscr.addch(horizon + depth, x,
                                         "~" if rng.random() < 0.5 else ".",
                                         WIN if depth < 3 else WTL)
                        except curses.error:
                            pass

        # ripples: expanding rings on the water
        kept = []
        for rx, rdepth, rage in ripples:
            ry = horizon + rdepth
            for dx in range(-rage, rage + 1):
                ch = "o" if abs(dx) == rage else ("~" if rage - abs(dx) == 1 else None)
                if ch is None:
                    continue
                x = rx + dx
                if 0 <= x < w and rage > 0:
                    try:
                        stdscr.addch(ry, x, ch, WTL if rage < 6 else DIM)
                    except curses.error:
                        pass
            if rage == 0:
                try:
                    stdscr.addch(ry, rx, "o", WIN)
                except curses.error:
                    pass
            if rage < 11:
                kept.append([rx, rdepth, rage + 1])
        ripples = kept

        # fireflies
        for f in flies:
            f.step(w, h)
            if f.on:
                try:
                    stdscr.addch(int(f.y), int(f.x), ".", WIN)
                except curses.error:
                    pass

        # your firefly, once you've taken one
        if you is not None:
            try:
                stdscr.addch(int(you[1]), int(you[0]), "*", BRIGHT | curses.A_BOLD)
            except curses.error:
                pass

        # sparkles rising from the fox when greeted
        kept = []
        for sx, sy, sage in sparkles:
            try:
                stdscr.addch(int(sy), int(sx), "*" if sage < 3 else ".", WIN)
            except curses.error:
                pass
            if sage < 7:
                kept.append([sx + rng.uniform(-0.3, 0.3), sy - 0.6, sage + 1])
        sparkles = kept

        # the hill + the fox, lower left
        hill_y = h - 7
        for x in range(0, w // 2):
            hy = hill_y + (x * 2) // max(1, w // 2)
            if hy < h - 2:
                try:
                    stdscr.addch(hy, x, "_", DIM)
                except curses.error:
                    pass
        if dawn >= 1.0 and not dawn_started:
            dawn_started = True
            sparkles.append([8.0, float(hill_y - 6), 0])
        if dawn < 0.5:
            dawn_started = False  # rearm for the next cycle's dawn
        if dawn >= 1.0:
            fox = FOX_B  # settled down to sleep
        elif now < fox_party_until:
            fox = FOX_A if int(t * 6) % 2 == 0 else FOX_B
        else:
            fox = FOX_A if int(t) % 6 < 5 else FOX_B
        for i, row in enumerate(fox):
            try:
                stdscr.addstr(hill_y - 5 + i, 4, row, FOX)
            except curses.error:
                pass

        # hint line (second from bottom): fades after the first minute
        # unless the user has pinned it with '?'; the poetry stays.
        if hint_visible and not hint_pinned and t > 60:
            hint_visible = False
        if hint_visible:
            hint = HINT[:max(0, w - 1)]
            try:
                stdscr.addstr(h - 2, max(0, (w - len(hint)) // 2), hint, DIM)
            except curses.error:
                pass
        if now - line_since > 20:
            line_since = now
            line_idx = (line_idx + 1) % len(LINES)
        text = LINES[line_idx][:max(0, w - 1)]
        try:
            stdscr.addstr(h - 1, max(0, (w - len(text)) // 2), text, TXT)
        except curses.error:
            pass

        stdscr.refresh()

        # ---- input ----
        key = stdscr.getch()
        if key in (ord("q"), 27):
            return
        elif key == ord(" "):
            if meteor is None:
                meteor = [rng.randrange(5, max(6, w - 25)), rng.randrange(1, 5), 0]
        elif key == ord("f"):
            fox_party_until = now + 1.6
            sparkles.append([8.0, float(hill_y - 6), 0])
        elif key == ord("b"):
            village_pulse_at = now
        elif key == ord("?"):
            hint_visible = not hint_visible
            hint_pinned = True
        elif key == ord("m") and stars:
            # Pick a compact chain of nearby stars for a readable little sketch.
            anchor = rng.randrange(len(stars))
            chosen = [anchor]
            while len(chosen) < min(4, len(stars)):
                last = stars[chosen[-1]]
                options = [
                    i for i, candidate in enumerate(stars)
                    if i not in chosen and
                    math.hypot(candidate.x - last.x, candidate.y - last.y) < 12
                ]
                if not options:
                    break
                chosen.append(min(
                    options,
                    key=lambda i: math.hypot(stars[i].x - last.x, stars[i].y - last.y),
                ))
            constellation = (chosen, now)
        elif key in (curses.KEY_LEFT, ord("h"), curses.KEY_RIGHT, ord("l"),
                     curses.KEY_UP, ord("k"), curses.KEY_DOWN, ord("j")):
            if you is None:
                you = [w / 2, h * 0.75]
            step = 2.0
            if key in (curses.KEY_LEFT, ord("h")):
                you[0] = max(0, you[0] - step)
            elif key in (curses.KEY_RIGHT, ord("l")):
                you[0] = min(w - 1, you[0] + step)
            elif key in (curses.KEY_UP, ord("k")):
                you[1] = max(horizon + 1, you[1] - 1)
            else:
                you[1] = min(h - 3, you[1] + 1)
        elif key == curses.KEY_MOUSE:
            try:
                _, cx, cy, _, bstate = curses.getmouse()
            except curses.error:
                bstate = 0
            if bstate & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED):
                if cy > horizon:
                    ripples.append([cx, max(1, cy - horizon), 0])
                elif cy < horizon - 6:
                    meteor = [max(2, cx), max(1, cy), 0]
                else:
                    # village band: toggle the nearest window within reach
                    best, bestd = None, 9
                    for win in windows:
                        d = abs(win[0] - cx) + abs(win[1] - cy) * 2
                        if d < bestd:
                            best, bestd = win, d
                    if best is not None:
                        best[2] = not best[2]
        time.sleep(0.09)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
