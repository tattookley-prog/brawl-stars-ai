"""Простая логика по правилам: идти к ближайшему врагу, стрелять в радиусе атаки."""
import math


def center(box):
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2, (y1 + y2) / 2


def decide(dets, cfg):
    """dets: список (class_name, conf, (x1,y1,x2,y2)). Возвращает действия."""
    me = [d for d in dets if d[0] == "me"]
    enemies = [d for d in dets if d[0] == "enemy"]
    if not me:
        return {"move": None, "attack": None}
    mx, my = center(me[0][2])
    if not enemies:
        gems = [d for d in dets if d[0] == "gem"]
        if gems:
            gx, gy = center(gems[0][2])
            return {"move": math.atan2(gy - my, gx - mx), "attack": None}
        return {"move": None, "attack": None}
    ex, ey = min((center(e[2]) for e in enemies),
                 key=lambda c: (c[0] - mx) ** 2 + (c[1] - my) ** 2)
    angle = math.atan2(ey - my, ex - mx)
    dist = math.hypot(ex - mx, ey - my)
    rng = cfg["attack_range"]
    if dist > rng:
        return {"move": angle, "attack": None}
    if dist < rng * 0.5:  # слишком близко - отступаем и стреляем
        return {"move": angle + math.pi, "attack": angle}
    return {"move": None, "attack": angle}
