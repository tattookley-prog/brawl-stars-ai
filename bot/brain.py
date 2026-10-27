"""Логика для Броулбола. Классы модели: me, ally, enemy, ball."""
import math
import time

_carry_since = None  # когда начали вести мяч


def center(box):
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2, (y1 + y2) / 2


def nearest(objs, mx, my):
    if not objs:
        return None, None
    c = min((center(o[2]) for o in objs), key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)
    return c, math.hypot(c[0] - mx, c[1] - my)


def decide(dets, cfg):
    """dets: список (class_name, conf, (x1,y1,x2,y2)). Возвращает {'move': угол|None, 'attack': угол|None}."""
    global _carry_since
    me = [d for d in dets if d[0] == "me"]
    if not me:
        return {"move": None, "attack": None}
    mx, my = center(max(me, key=lambda d: d[1])[2])

    goal = math.radians(cfg.get("goal_dir", -90))
    rng = cfg["attack_range"]
    ball, bdist = nearest([d for d in dets if d[0] == "ball"], mx, my)
    enemy, edist = nearest([d for d in dets if d[0] == "enemy"], mx, my)

    # 1) Мяч у нас -> ведём к воротам, бьём при опасности или по таймеру
    if bdist is not None and bdist < cfg.get("have_ball_dist", 120):
        if _carry_since is None:
            _carry_since = time.time()
        enemy_close = edist is not None and edist < rng * 0.6
        if enemy_close or time.time() - _carry_since > cfg.get("carry_time", 2.5):
            _carry_since = None
            return {"move": goal, "attack": goal}  # удар мячом к воротам
        move = goal
        if enemy is not None and edist < rng:  # обходим врага сбоку
            side = 1 if enemy[0] < mx else -1
            move = goal + side * math.radians(35)
        return {"move": move, "attack": None}

    _carry_since = None

    # 2) Мяч виден -> бежим к нему, стреляем по врагу в радиусе
    if ball is not None:
        move = math.atan2(ball[1] - my, ball[0] - mx)
        atk = math.atan2(enemy[1] - my, enemy[0] - mx) if enemy is not None and edist < rng else None
        return {"move": move, "attack": atk}

    # 3) Мяча не видно -> бой с ближайшим врагом
    if enemy is not None:
        angle = math.atan2(enemy[1] - my, enemy[0] - mx)
        if edist > rng:
            return {"move": angle, "attack": None}
        if edist < rng * 0.5:
            return {"move": angle + math.pi, "attack": angle}
        return {"move": None, "attack": angle}

    # 4) Никого нет -> идём к воротам врага
    return {"move": goal, "attack": None}
