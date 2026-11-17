from datetime import date
from models import Session, Group, Student, Lesson, Attendance


# ---------- Студенты ----------

def get_or_create_student(vk_id: int, full_name: str, group_name: str = "ИС-21"):
    s = Session()
    try:
        student = s.query(Student).filter_by(vk_id=vk_id).first()
        if not student:
            group = s.query(Group).filter_by(name=group_name).first()
            if not group:
                group = Group(name=group_name)
                s.add(group)
                s.flush()
            student = Student(vk_id=vk_id, full_name=full_name, group_id=group.id)
            s.add(student)
            s.commit()
        return student.id, student.group.name
    finally:
        s.close()


def get_students_by_group(group_id: int):
    s = Session()
    try:
        return s.query(Student).filter_by(group_id=group_id).all()
    finally:
        s.close()


# ---------- Пары ----------

def create_lesson(group_id: int, subject: str) -> int:
    s = Session()
    try:
        lesson = Lesson(group_id=group_id, subject=subject, lesson_date=date.today())
        s.add(lesson)
        s.commit()
        return lesson.id
    finally:
        s.close()


def get_last_lesson(group_id: int):
    s = Session()
    try:
        return (
            s.query(Lesson)
            .filter_by(group_id=group_id)
            .order_by(Lesson.id.desc())
            .first()
        )
    finally:
        s.close()


# ---------- Посещаемость ----------

def toggle_attendance(lesson_id: int, student_id: int):
    """Переключает статус: был -> не был -> был ..."""
    s = Session()
    try:
        rec = (
            s.query(Attendance)
            .filter_by(lesson_id=lesson_id, student_id=student_id)
            .first()
        )
        if not rec:
            rec = Attendance(lesson_id=lesson_id, student_id=student_id, present=True)
            s.add(rec)
        else:
            rec.present = not rec.present
        s.commit()
        return rec.present
    finally:
        s.close()


def is_present(lesson_id: int, student_id: int) -> bool:
    s = Session()
    try:
        rec = (
            s.query(Attendance)
            .filter_by(lesson_id=lesson_id, student_id=student_id)
            .first()
        )
        return bool(rec and rec.present)
    finally:
        s.close()


def get_attendance_stats(student_id: int):
    s = Session()
    try:
        student = s.query(Student).get(student_id)
        total = s.query(Lesson).filter_by(group_id=student.group_id).count()
        present = (
            s.query(Attendance)
            .filter_by(student_id=student_id, present=True)
            .count()
        )
        return present, total
    finally:
        s.close()
