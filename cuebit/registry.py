# cuebit/registry.py
import uuid
import json
from datetime import datetime
from typing import List, Optional
from collections import Counter

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class PromptORM(Base):
    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(String, unique=True, nullable=False)
    project = Column(String, nullable=True)
    task = Column(String, nullable=False)
    template = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    alias = Column(String, nullable=True)
    tags = Column(Text)
    meta = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String, nullable=True)

class PromptRegistry:
    def __init__(self, db_url: str = "sqlite:///prompts.db"):
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def register_prompt(
        self,
        task: str,
        template: str,
        meta: dict,
        tags: List[str] = [],
        project: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> PromptORM:
        session = self.Session()
        prompt_id = str(uuid.uuid4())

        version = 1
        if project and task:
            latest_version = (
                session.query(func.max(PromptORM.version))
                .filter_by(project=project, task=task)
                .scalar()
            )
            if latest_version:
                version = latest_version + 1

        new_prompt = PromptORM(
            prompt_id=prompt_id,
            project=project,
            task=task,
            template=template,
            version=version,
            alias=None,
            tags=json.dumps(tags),
            meta=meta,
            updated_by=updated_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(new_prompt)
        session.commit()
        session.refresh(new_prompt)
        session.close()
        return new_prompt

    def get_prompt(self, prompt_id: str) -> Optional[PromptORM]:
        session = self.Session()
        prompt = session.query(PromptORM).filter_by(prompt_id=prompt_id).first()
        session.close()
        return prompt

    def get_prompt_by_alias(self, alias: str) -> Optional[PromptORM]:
        session = self.Session()
        prompt = session.query(PromptORM).filter_by(alias=alias).first()
        session.close()
        return prompt

    def list_prompts(self) -> List[PromptORM]:
        session = self.Session()
        prompts = session.query(PromptORM).all()
        session.close()
        return prompts

    def list_projects(self) -> List[str]:
        session = self.Session()
        projects = session.query(PromptORM.project).distinct().all()
        session.close()
        return [p[0] or "Unassigned" for p in projects]

    def list_prompts_by_project(self, project: str) -> List[PromptORM]:
        session = self.Session()
        prompts = session.query(PromptORM).filter_by(project=project).all()
        session.close()
        return prompts

    def get_tag_stats(self) -> Counter:
        prompts = self.list_prompts()
        counter = Counter()
        for p in prompts:
            try:
                tag_list = json.loads(p.tags or "[]")
                counter.update(tag_list)
            except Exception:
                pass
        return counter

    def add_alias(self, prompt_id: str, alias: str) -> Optional[PromptORM]:
        session = self.Session()
        prompt = session.query(PromptORM).filter_by(prompt_id=prompt_id).first()
        if prompt:
            prompt.alias = alias
            session.commit()
        session.close()
        return prompt

    def update_prompt(self, prompt_id: str, new_template: str, meta: Optional[dict] = None, updated_by: Optional[str] = None) -> Optional[PromptORM]:
        session = self.Session()
        old_prompt = session.query(PromptORM).filter_by(prompt_id=prompt_id).first()
        if not old_prompt:
            session.close()
            return None

        latest_version = (
            session.query(func.max(PromptORM.version))
            .filter_by(project=old_prompt.project, task=old_prompt.task)
            .scalar()
        )
        new_version = (latest_version or 0) + 1

        new_prompt = PromptORM(
            prompt_id=str(uuid.uuid4()),
            project=old_prompt.project,
            task=old_prompt.task,
            template=new_template,
            version=new_version,
            alias=None,
            tags=old_prompt.tags,
            meta=meta or old_prompt.meta,
            updated_by=updated_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(new_prompt)
        session.commit()
        session.refresh(new_prompt)
        session.close()
        return new_prompt

    def delete_prompt_by_id(self, prompt_id: str) -> bool:
        session = self.Session()
        prompt = session.query(PromptORM).filter_by(prompt_id=prompt_id).first()
        if prompt:
            session.delete(prompt)
            session.commit()
            session.close()
            return True
        session.close()
        return False

    def delete_project(self, project: str) -> int:
        session = self.Session()
        deleted = session.query(PromptORM).filter_by(project=project).delete()
        session.commit()
        session.close()
        return deleted

    def delete_prompts_by_project_task(self, project: str, task: str) -> int:
        session = self.Session()
        deleted = session.query(PromptORM).filter_by(project=project, task=task).delete()
        session.commit()
        session.close()
        return deleted