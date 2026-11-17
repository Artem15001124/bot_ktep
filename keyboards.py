import json


def make_keyboard(buttons, one_time=False, inline=False):
    """Универсальный конструктор клавиатуры VK"""
    if inline:
        return json.dumps({
            "inline": True,
            "buttons": buttons
        }, ensure_ascii=False)
    return json.dumps({
        "one_time": one_time,
        "buttons": buttons
    }, ensure_ascii=False)


def btn(text, payload=None, color="secondary"):
    """Обычная кнопка"""
    return {
        "action": {
            "type": "text",
            "label": text,
            "payload": json.dumps(payload or {}, ensure_ascii=False)
        },
        "color": color
    }


def btn_callback(text, payload, color="primary"):
    """Callback-кнопка (inline)"""
    return {
        "action": {
            "type": "callback",
            "label": text,
            "payload": json.dumps(payload, ensure_ascii=False)
        },
        "color": color
    }


def main_menu(is_admin=False):
    rows = [
        [btn("📅 Отметить посещаемость", color="primary")],
        [btn("📊 Моя посещаемость")],
    ]
    if is_admin:
        rows.append([btn("👥 Список группы"), btn("➕ Создать пару")])
    return make_keyboard(rows)
