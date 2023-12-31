from pathlib import Path
from datetime import datetime
from typing import Optional, List
from enum import Enum

from pipeline.helpers import db


class InterviewType(Enum):
    """
    Enumerates the types of interviews.
    """

    ONSITE = "onsite"
    OFFSITE = "offsite"

    @staticmethod
    def init_table_query() -> List[str]:
        """
        Return the SQL query to create the 'interview_types' table.
        """
        create_sql_query = """
        CREATE TABLE IF NOT EXISTS interview_types (
            id SERIAL PRIMARY KEY,
            interview_type TEXT NOT NULL UNIQUE
        );
        """

        populate_sql_query = """
        INSERT INTO interview_types (interview_type)
        VALUES ('onsite'), ('offsite');
        """

        sql_queries: List[str] = [create_sql_query, populate_sql_query]

        return sql_queries

    @staticmethod
    def drop_table_query() -> str:
        """
        Return the SQL query to drop the 'interview_types' table.
        """
        sql_query = """
        DROP TABLE IF EXISTS interview_types;
        """

        return sql_query


class Interview:
    def __init__(
        self,
        interview_name: str,
        interview_path: Path,
        interview_type: InterviewType,
        interview_datetime: datetime,
        subject_id: str,
        study_id: str,
        id: Optional[int] = None,
    ):
        self.id = id
        self.interview_name = interview_name
        self.interview_path = interview_path
        self.interview_type = interview_type
        self.interview_datetime = interview_datetime
        self.subject_id = subject_id
        self.study_id = study_id

    def __str__(self):
        return f"Interview({self.subject_id}, {self.study_id}, {self.interview_name})"

    def __repr__(self):
        return self.__str__()

    @staticmethod
    def init_table_query() -> str:
        """
        Return the SQL query to create the 'interviews' table.
        """
        sql_query = """
        CREATE TABLE IF NOT EXISTS interviews (
            id SERIAL PRIMARY KEY,
            interview_name TEXT NOT NULL,
            interview_path TEXT NOT NULL UNIQUE,
            interview_type TEXT NOT NULL REFERENCES interview_types (interview_type),
            interview_date TIMESTAMP NOT NULL,
            subject_id TEXT NOT NULL,
            study_id TEXT NOT NULL,
            FOREIGN KEY (subject_id, study_id) REFERENCES subjects (subject_id, study_id)
        );
        """

        return sql_query

    @staticmethod
    def drop_table_query() -> str:
        """
        Return the SQL query to drop the 'interviews' table.
        """
        sql_query = """
        DROP TABLE IF EXISTS interviews;
        """

        return sql_query

    def to_sql(self):
        """
        Return the SQL query to insert the Interview object into the 'interviews' table.
        """
        i_name = db.santize_string(self.interview_name)
        i_path = db.santize_string(str(self.interview_path))
        i_type = db.santize_string(self.interview_type.value)
        i_date = db.santize_string(str(self.interview_datetime))
        s_id = db.santize_string(self.subject_id)
        st_id = db.santize_string(self.study_id)

        sql_query = f"""
        INSERT INTO interviews (interview_name, interview_path, interview_type, interview_date, subject_id, study_id)
        VALUES ('{i_name}', '{i_path}', '{i_type}', '{i_date}', '{s_id}', '{st_id}');
        """

        return sql_query