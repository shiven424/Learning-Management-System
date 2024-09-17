from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime
from uuid import uuid4

@dataclass
class User:
    username: str
    password: str
    role: str
    name: str

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class Assignment:
    student_name: str
    teacher_name: str
    filename: str
    file_path: str
    file_id: uuid4
    submission_date: datetime
    grade: Optional[str] = None
    feedback: Optional[str] = None

    def to_dict(self) -> dict:
        # Convert datetime to string for MongoDB compatibility
        assignment_dict = asdict(self)
        assignment_dict["submission_date"] = self.submission_date.isoformat()
        return assignment_dict

@dataclass
class Feedback:
    feedback_text: str
    submission_date: datetime
    student_name: Optional[str] = None
    teacher_name: Optional[str] = None


    def to_dict(self) -> dict:
        # Convert datetime to string for MongoDB compatibility
        feedback_dict = asdict(self)
        feedback_dict["date"] = self.date.isoformat()
        return feedback_dict

@dataclass
class CourseMaterial:
    course_name: str
    filename: str
    file_path: str
    file_id: uuid4
    teacher_name: str
    upload_date: datetime

    def to_dict(self) -> dict:
        return asdict(self)
