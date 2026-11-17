from datetime import datetime, date
from sqlalchemy import (
    create_engine, Column, Integer, String, Date, DateTime,
    Boolean, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from config import DB_URL

Base = declarative_base()


class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    students = relationship("Student", back_populates="group")


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"))
    group = relationship("Group", back_populates="students")


class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    subject = Column(String(100), nullable=False)
    lesson_date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)
    marks = relationship("Attendance", back_populates="lesson")


class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    present = Column(Boolean, default=False)
    marked_at = Column(DateTime, default=datetime.utcnow)
    lesson = relationship("Lesson", back_populates="marks")
    student = relationship("Student")

    __table_args__ = (UniqueConstraint("lesson_id", "student_id"),)


engine = create_engine(DB_URL, echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
