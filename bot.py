import logging
from datetime import datetime

from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id

from config import VK_TOKEN, GROUP_ID, ADMIN_IDS
import database as db
from keyboards import (
    main_menu, make_keyboard, btn, btn_callback
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# --- Инициализация ---
vk_session = VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

# Состояния пользователей (ожидание ввода названия предмета)
STATE = {}  # vk_id -> dict


def send(peer_id, text, keyboard=None):
    vk.messages.send(
        peer_id=peer_id,
        message=text,
        keyboard=keyboard,
        random_id=get_random_id(),
    )


def edit(peer_id, message_id, text, keyboard=None):
    """Редактирование сообщения (для inline-кнопок)"""
    try:
        vk.messages.edit(
            peer_id=peer_id,
            message_id=message_id,
            message=text,
            keyboard=keyboard,
        )
    except Exception as e:
        log.warning(f"edit failed: {e}")


# ---------- Логика меню ----------

def handle_message(message, event):
    peer_id = message.peer_id
    user_id = message.from_id
    text = (message.text or "").strip()

    is_admin = user_id in ADMIN_IDS

    # --- Регистрация ---
    user_info = vk.users.get(user_ids=user_id, fields="first_name,last_name")[0]
    full_name = f"{user_info['last_name']} {user_info['first_name']}"
    db.get_or_create_student(user_id, full_name)

    # --- Ожидание ввода предмета ---
    if STATE.get(user_id, {}).get("state") == "await_subject":
        subject = text
        STATE.pop(user_id, None)
        student_id, group_name = db.get_or_create_student(user_id, full_name)
        from models import Session, Group
        s = Session()
        group = s.query(Group).filter_by(name=group_name).first()
        group_id = group.id
        s.close()
        db.create_lesson(group_id, subject)
        send(peer_id, f"✅ Пара «{subject}» создана. Отмечайте посещаемость.",
             main_menu(is_admin))
        return

    # --- /start и приветствие ---
    if text.lower() in ("начать", "start", "/start", "привет"):
        send(peer_id,
             f"👋 Привет, {user_info['first_name']}!\n"
             f"Это электронный дневник посещаемости.\n\n"
             f"Выбери действие в меню ниже.",
             main_menu(is_admin))
        return

    # --- Отметить посещаемость ---
    if "Отметить посещаемость" in text:
        student_id, group_name = db.get_or_create_student(user_id, full_name)
        from models import Session, Group
        s = Session()
        group = s.query(Group).filter_by(name=group_name).first()
        group_id = group.id
        s.close()

        lesson = db.get_last_lesson(group_id)
        if not lesson:
            send(peer_id,
                 "❌ Пока нет ни одной пары. Преподаватель должен создать её.",
                 main_menu(is_admin))
            return

        students = db.get_students_by_group(group_id)
        if not students:
            send(peer_id, "❌ В группе нет студентов.", main_menu(is_admin))
            return

        # Генерируем inline-клавиатуру со студентами
        buttons = []
        row = []
        for st in students:
            mark = "✅" if db.is_present(lesson.id, st.id) else "❌"
            row.append(btn_callback(
                f"{mark} {st.full_name}",
                {"act": "toggle", "lesson": lesson.id, "student": st.id},
                color="positive" if mark == "✅" else "negative"
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([btn_callback("🔄 Обновить", {"act": "refresh", "lesson": lesson.id})])

        send(peer_id,
             f"📚 Пара: <b>{lesson.subject}</b> ({lesson.lesson_date})\n"
             f"Нажмите на студента, чтобы переключить отметку.",
             make_keyboard(buttons, inline=True))
        return

    # --- Моя посещаемость ---
    if "Моя посещаемость" in text:
        student_id, _ = db.get_or_create_student(user_id, full_name)
        present, total = db.get_attendance_stats(student_id)
        percent = (present / total * 100) if total else 0
        send(peer_id,
             f"📊 Ваша посещаемость:\n"
             f"Посещено: {present} из {total} пар\n"
             f"Процент: {percent:.1f}%",
             main_menu(is_admin))
        return

    # --- Создать пару (админ) ---
    if "Создать пару" in text and is_admin:
        STATE[user_id] = {"state": "await_subject"}
        send(peer_id, "✏️ Введите название предмета (например, «Математика»):")
        return

    # --- Список группы ---
    if "Список группы" in text:
        student_id, group_name = db.get_or_create_student(user_id, full_name)
        from models import Session, Group
        s = Session()
        group = s.query(Group).filter_by(name=group_name).first()
        students = db.get_students_by_group(group.id)
        s.close()
        names = "\n".join(f"• {st.full_name}" for st in students) or "— пусто —"
        send(peer_id, f"👥 Группа {group_name}:\n{names}", main_menu(is_admin))
        return

    # --- Fallback ---
    send(peer_id, "🤔 Не понял. Используйте меню.", main_menu(is_admin))


def handle_callback(event):
    """Обработка нажатий на inline-кнопки"""
    user_id = event.object.user_id
    peer_id = event.object.peer_id
    message_id = event.object.conversation_message_id
    payload = event.object.payload

    if payload.get("act") == "toggle":
        lesson_id = payload["lesson"]
        student_id = payload["student"]
        new_state = db.toggle_attendance(lesson_id, student_id)
        log.info(f"toggle lesson={lesson_id} student={student_id} -> {new_state}")

    # Перерисовываем клавиатуру
    from models import Session, Lesson
    s = Session()
    lesson = s.query(Lesson).get(payload["lesson"])
    if lesson:
        students = db.get_students_by_group(lesson.group_id)
        buttons = []
        row = []
        for st in students:
            mark = "✅" if db.is_present(lesson.id, st.id) else "❌"
            row.append(btn_callback(
                f"{mark} {st.full_name}",
                {"act": "toggle", "lesson": lesson.id, "student": st.id},
                color="positive" if mark == "✅" else "negative"
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([btn_callback("🔄 Обновить", {"act": "refresh", "lesson": lesson.id})])

        text = (f"📚 Пара: <b>{lesson.subject}</b> ({lesson.lesson_date})\n"
                f"Нажмите на студента, чтобы переключить отметку.")
        edit(peer_id, message_id, text, make_keyboard(buttons, inline=True))
    s.close()


# ---------- Запуск ----------

def main():
    log.info("Бот запущен")
    for event in longpoll.listen():
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                handle_message(event.object.message, event)
            elif event.type == VkBotEventType.MESSAGE_EVENT:
                handle_callback(event)
        except Exception as e:
            log.exception(f"Ошибка обработки: {e}")


if __name__ == "__main__":
    main()
