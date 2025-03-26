"""
Core registry module for Cuebit prompt management.

This module provides the main PromptRegistry class that handles
storing, retrieving, and versioning prompt templates with full
version history and lineage tracking.
"""

import uuid
import json
import re
import os
import appdirs
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from collections import Counter, defaultdict
import copy

from sqlalchemy import (
    create_engine, Column, String, Integer, DateTime, 
    Text, JSON, ForeignKey, Boolean, Float, func, and_, or_
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref, Session
from sqlalchemy.orm.exc import DetachedInstanceError

# Get application data directory
APP_NAME = "cuebit"
APP_AUTHOR = "cuebit"

def get_default_db_path():
    """Get the default database path in the user's data directory."""
    user_data_dir = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)
    
    # Ensure the directory exists
    os.makedirs(user_data_dir, exist_ok=True)
    
    # Return database path
    return os.path.join(user_data_dir, "prompts.db")

Base = declarative_base()

class PromptORM(Base):
    """
    Database model for storing prompt templates with versioning support.
    
    Attributes:
        id (int): Auto-incrementing primary key
        prompt_id (str): Unique UUID for this prompt
        project (str): Project this prompt belongs to
        task (str): Task category/name for this prompt
        template (str): The actual prompt template text with {variable} placeholders
        version (int): Version number within project/task
        alias (str): Optional name to refer to this specific prompt version
        tags (str): JSON-encoded list of tags
        meta (dict): JSON metadata for this prompt
        parent_id (str): Reference to parent prompt version
        template_variables (list): List of variable names extracted from template
        is_deleted (bool): Soft delete flag
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
        updated_by (str): User who last updated this prompt
    """
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
    parent_id = Column(String, ForeignKey("prompts.prompt_id"), nullable=True)
    template_variables = Column(JSON, default=list)  # Store expected variables
    is_deleted = Column(Boolean, default=False)  # Soft delete support
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String, nullable=True)

    # Define relationship for version history
    children = relationship(
        "PromptORM", 
        backref=backref("parent", remote_side=[prompt_id]),
        foreign_keys=[parent_id]
    )

    def to_dict(self):
        """Convert ORM object to dictionary for serialization"""
        data = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # Handle special types
            if isinstance(value, datetime):
                value = value.isoformat()
                
            data[column.name] = value
            
        return data

# Junction table for many-to-many prompt-tag relationship
class PromptTagORM(Base):
    """
    Junction table for many-to-many relationship between prompts and tags.
    
    Attributes:
        id (int): Auto-incrementing primary key
        prompt_id (str): Reference to prompt
        tag_name (str): Tag name
    """
    __tablename__ = "prompt_tags"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(String, ForeignKey("prompts.prompt_id"), nullable=False)
    tag_name = Column(String, nullable=False)

# Example input/output
class ExampleORM(Base):
    """
    Stores example inputs and outputs for prompt templates.
    
    Attributes:
        id (int): Auto-incrementing primary key
        prompt_id (str): Reference to related prompt
        input_text (str): Example input text
        output_text (str): Example output text
        description (str): Optional description of this example
        created_at (datetime): Creation timestamp
    """
    __tablename__ = "examples"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(String, ForeignKey("prompts.prompt_id"), nullable=False)
    input_text = Column(Text, nullable=False)
    output_text = Column(Text, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert ORM object to dictionary for serialization"""
        return {
            "id": self.id,
            "prompt_id": self.prompt_id,
            "input": self.input_text,
            "output": self.output_text,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class PromptRegistry:
    """
    Main registry class for managing prompt templates, versions, and metadata.
    
    The PromptRegistry provides methods for storing, retrieving, and managing
    prompt templates with full versioning, metadata, tagging, and organization
    by project and task.
    """
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize the prompt registry with a database connection.
        
        Args:
            db_url (str, optional): SQLAlchemy database URL. If None, will be determined in this order:
                1. CUEBIT_DB_PATH environment variable
                2. Standard user data directory
                3. Local file "prompts.db" in current directory (legacy behavior)
        """
        if db_url is None:
            # Check environment variable first
            db_url = os.environ.get("CUEBIT_DB_PATH")
            
            if db_url is None:
                # Then try standard user data directory
                default_db = get_default_db_path()
                db_url = f"sqlite:///{default_db}"
                
        # Store the database URL for reference
        self.db_url = db_url
        
        # Initialize database connection
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def register_prompt(
            self,
            task: str,
            template: str,
            meta: dict = {},
            tags: List[str] = [],
            project: Optional[str] = None,
            updated_by: Optional[str] = None,
            examples: Optional[List[Dict[str, str]]] = None
        ) -> PromptORM:
        """
        Register a new prompt template with metadata.
        
        Args:
            task (str): Task category for this prompt
            template (str): The prompt template text with {variable} placeholders
            meta (dict): JSON metadata (model info, parameters, etc.)
            tags (List[str]): Tags for categorizing this prompt
            project (str, optional): Project name
            updated_by (str, optional): Username of person registering
            examples (List[Dict], optional): Example input/output pairs
            
        Returns:
            PromptORM: The newly created prompt object
            
        Example:
            >>> registry.register_prompt(
            ...     task="summarization",
            ...     template="Summarize this text: {input}",
            ...     meta={"model": "gpt-4", "temp": 0.7},
            ...     tags=["prod", "summarization"],
            ...     project="content-generator",
            ...     examples=[{
            ...         "input": "Long article text...",
            ...         "output": "Concise summary...",
            ...         "description": "News article summarization"
            ...     }]
            ... )
        """
        session = self.Session()
        try:
            prompt_id = str(uuid.uuid4())

            # Auto-increment version within project/task
            version = 1
            if project and task:
                latest_version = (
                    session.query(func.max(PromptORM.version))
                    .filter(
                        PromptORM.project == project,
                        PromptORM.task == task,
                        PromptORM.is_deleted == False
                    )
                    .scalar()
                )
                if latest_version:
                    version = latest_version + 1

            # Extract template variables
            template_vars = re.findall(r'\{([^{}]*)\}', template)
            
            new_prompt = PromptORM(
                prompt_id=prompt_id,
                project=project,
                task=task,
                template=template,
                version=version,
                alias=None,
                tags=json.dumps(tags),
                meta=meta,
                template_variables=template_vars,
                updated_by=updated_by,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(new_prompt)
            
            # Process tags
            for tag in tags:
                if tag:
                    prompt_tag = PromptTagORM(prompt_id=prompt_id, tag_name=tag)
                    session.add(prompt_tag)
            
            # Add examples if provided
            if examples:
                for ex in examples:
                    example = ExampleORM(
                        prompt_id=prompt_id,
                        input_text=ex.get("input", ""),
                        output_text=ex.get("output", ""),
                        description=ex.get("description")
                    )
                    session.add(example)
            
            session.commit()
            session.refresh(new_prompt)
            
            # Make a copy to avoid DetachedInstanceError after session close
            result = copy.deepcopy(new_prompt)
            return result
        finally:
            session.close()

    def get_prompt(self, prompt_id: str, include_deleted: bool = False) -> Optional[PromptORM]:
        """
        Retrieve a prompt by its ID.
        
        Args:
            prompt_id (str): The UUID of the prompt
            include_deleted (bool): Whether to include soft-deleted prompts
            
        Returns:
            Optional[PromptORM]: The prompt object if found, None otherwise
            
        Example:
            >>> prompt = registry.get_prompt("550e8400-e29b-41d4-a716-446655440000")
            >>> print(prompt.template)
            "Summarize this text: {input}"
        """
        session = self.Session()
        try:
            query = session.query(PromptORM).filter_by(prompt_id=prompt_id)
            
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
                
            prompt = query.first()
            
            # Handle SQLAlchemy detached instance issue
            if prompt:
                session.expunge(prompt)
                
            return prompt
        finally:
            session.close()

    def get_prompt_by_alias(self, alias: str) -> Optional[PromptORM]:
        """
        Retrieve a prompt by its alias.
        
        Args:
            alias (str): The alias to look up
            
        Returns:
            Optional[PromptORM]: The prompt object if found, None otherwise
            
        Example:
            >>> prompt = registry.get_prompt_by_alias("summarizer-prod")
            >>> print(prompt.template)
            "Summarize this text: {input}"
        """
        session = self.Session()
        try:
            prompt = session.query(PromptORM).filter_by(
                alias=alias,
                is_deleted=False
            ).first()
            
            # Handle SQLAlchemy detached instance issue
            if prompt:
                session.expunge(prompt)
                
            return prompt
        finally:
            session.close()

    def list_prompts(
        self, 
        include_deleted: bool = False,
        search_term: Optional[str] = None,
        tag_filter: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 100
    ) -> Tuple[List[PromptORM], int]:
        """
        List prompts with filtering and pagination.
        
        Args:
            include_deleted (bool): Whether to include soft-deleted prompts
            search_term (str, optional): Text to search in templates and metadata
            tag_filter (List[str], optional): Filter by tags
            page (int): Page number for pagination (starts at 1)
            page_size (int): Items per page
            
        Returns:
            Tuple[List[PromptORM], int]: List of prompts and total count
            
        Example:
            >>> prompts, total = registry.list_prompts(
            ...     search_term="summarize",
            ...     tag_filter=["prod"],
            ...     page=1,
            ...     page_size=20
            ... )
            >>> print(f"Found {total} prompts, showing {len(prompts)}")
            "Found 45 prompts, showing 20"
        """
        session = self.Session()
        try:
            query = session.query(PromptORM)
            
            # Apply filters
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
                
            if search_term:
                search_pattern = f"%{search_term}%"
                query = query.filter(
                    or_(
                        PromptORM.template.ilike(search_pattern),
                        PromptORM.task.ilike(search_pattern),
                        PromptORM.project.ilike(search_pattern)
                    )
                )
                
            if tag_filter:
                # This is more complex with proper tag schema - using simplified approach
                for tag in tag_filter:
                    tag_pattern = f"%\"{tag}\"%"  # Match in JSON array
                    query = query.filter(PromptORM.tags.ilike(tag_pattern))
                    
            # Count total for pagination
            total_count = query.count()
            
            # Apply pagination
            query = query.order_by(
                PromptORM.project, 
                PromptORM.task, 
                PromptORM.version.desc()
            )
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            prompts = query.all()
            
            # Handle SQLAlchemy detached instance issue
            for prompt in prompts:
                session.expunge(prompt)
                
            return prompts, total_count
        finally:
            session.close()

    def list_projects(self) -> List[str]:
        """
        List all projects in the registry.
        
        Returns:
            List[str]: List of project names
            
        Example:
            >>> projects = registry.list_projects()
            >>> print(projects)
            ["blog-generator", "customer-support", "marketing"]
        """
        session = self.Session()
        try:
            query = session.query(PromptORM.project).distinct()
            query = query.filter_by(is_deleted=False)
            
            projects = query.all()
            return [p[0] or "Unassigned" for p in projects]
        finally:
            session.close()

    def list_prompts_by_project(
        self, 
        project: str,
        include_deleted: bool = False
    ) -> List[PromptORM]:
        """
        List all prompts in a specific project.
        
        Args:
            project (str): Project name to filter
            include_deleted (bool): Whether to include soft-deleted prompts
            
        Returns:
            List[PromptORM]: List of prompts in the project
            
        Example:
            >>> prompts = registry.list_prompts_by_project("blog-generator")
            >>> for p in prompts:
            ...     print(f"{p.task} v{p.version}")
            "summarization v1"
            "summarization v2"
            "title-generator v1"
        """
        session = self.Session()
        try:
            query = session.query(PromptORM).filter_by(project=project)
            
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
                
            prompts = query.all()
            
            # Handle SQLAlchemy detached instance issue
            for prompt in prompts:
                session.expunge(prompt)
                
            return prompts
        finally:
            session.close()

    def get_tag_stats(self) -> Counter:
        """
        Get statistics on tag usage.
        
        Returns:
            Counter: Counter object with tag counts
            
        Example:
            >>> tag_stats = registry.get_tag_stats()
            >>> print(tag_stats.most_common(3))
            [("prod", 15), ("summarization", 10), ("qa", 7)]
        """
        session = self.Session()
        try:
            tag_counts = Counter()
            tag_entries = session.query(PromptTagORM.tag_name, func.count(PromptTagORM.id))\
                .join(PromptORM, PromptORM.prompt_id == PromptTagORM.prompt_id)\
                .filter(PromptORM.is_deleted == False)\
                .group_by(PromptTagORM.tag_name)\
                .all()
                
            for tag_name, count in tag_entries:
                tag_counts[tag_name] = count
                    
            return tag_counts
        finally:
            session.close()

    def add_alias(
        self, 
        prompt_id: str, 
        alias: str,
        overwrite: bool = True
    ) -> Optional[PromptORM]:
        """
        Add an alias to a prompt. Aliases can be used to refer to specific
        prompt versions (e.g., "summarizer-prod" → v3 of summarization prompt).
        
        Args:
            prompt_id (str): The prompt ID to alias
            alias (str): The alias name
            overwrite (bool): Whether to overwrite existing aliases
            
        Returns:
            Optional[PromptORM]: The updated prompt or None if not found
            
        Example:
            >>> prompt = registry.add_alias("550e8400-e29b-41d4-a716-446655440000", "summarizer-prod")
            >>> print(prompt.alias)
            "summarizer-prod"
        """
        session = self.Session()
        try:
            # Check if alias already exists
            if not overwrite:
                existing = session.query(PromptORM).filter_by(
                    alias=alias,
                    is_deleted=False
                ).first()
                
                if existing:
                    return None
            
            # Find the prompt and update it
            prompt = session.query(PromptORM).filter_by(
                prompt_id=prompt_id,
                is_deleted=False
            ).first()
            
            if prompt:
                # Remove this alias from any other prompts
                session.query(PromptORM).filter_by(
                    alias=alias,
                    is_deleted=False
                ).update({"alias": None})
                
                # Set the alias on the target prompt
                prompt.alias = alias
                session.commit()
                session.refresh(prompt)
                
                # Handle SQLAlchemy detached instance issue
                result = copy.deepcopy(prompt)
                session.expunge(prompt)
                return result
            
            return None
        finally:
            session.close()

    def update_prompt(
        self, 
        prompt_id: str, 
        new_template: str, 
        meta: Optional[dict] = None, 
        updated_by: Optional[str] = None,
        tags: Optional[List[str]] = None,
        examples: Optional[List[Dict[str, str]]] = None
    ) -> Optional[PromptORM]:
        """
        Update a prompt, creating a new version with lineage tracking.
        
        Args:
            prompt_id (str): ID of prompt to update
            new_template (str): New template text
            meta (dict, optional): New metadata (or None to keep existing)
            updated_by (str, optional): User making the update
            tags (List[str], optional): New tags (or None to keep existing)
            examples (List[Dict], optional): New examples to add
            
        Returns:
            Optional[PromptORM]: The new prompt version or None if not found
            
        Example:
            >>> new_prompt = registry.update_prompt(
            ...     "550e8400-e29b-41d4-a716-446655440000", 
            ...     "Summarize this article concisely: {input}",
            ...     meta={"model": "gpt-4", "notes": "Improved brevity"},
            ...     updated_by="alice"
            ... )
            >>> print(f"New version: {new_prompt.version}")
            "New version: 2"
        """
        session = self.Session()
        try:
            old_prompt = session.query(PromptORM).filter_by(
                prompt_id=prompt_id,
                is_deleted=False
            ).first()
            
            if not old_prompt:
                return None

            # Get the latest version for this project/task
            latest_version = (
                session.query(func.max(PromptORM.version))
                .filter_by(
                    project=old_prompt.project, 
                    task=old_prompt.task,
                    is_deleted=False
                )
                .scalar()
            )
            new_version = (latest_version or 0) + 1

            # Extract template variables
            template_vars = re.findall(r'\{([^{}]*)\}', new_template)
            
            # Use existing tags if not provided
            if tags is None:
                try:
                    tags = json.loads(old_prompt.tags or "[]")
                except:
                    tags = []
                    
            # Create new prompt version with parent-child relationship
            new_prompt = PromptORM(
                prompt_id=str(uuid.uuid4()),
                project=old_prompt.project,
                task=old_prompt.task,
                template=new_template,
                version=new_version,
                alias=None,  # Don't automatically transfer alias
                tags=json.dumps(tags),
                meta=meta or old_prompt.meta,
                parent_id=old_prompt.prompt_id,  # Set parent reference
                template_variables=template_vars,
                updated_by=updated_by,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(new_prompt)
            
            # Process tags
            for tag in tags:
                if tag:
                    prompt_tag = PromptTagORM(prompt_id=new_prompt.prompt_id, tag_name=tag)
                    session.add(prompt_tag)
                    
            # Add examples if provided
            if examples:
                for ex in examples:
                    example = ExampleORM(
                        prompt_id=new_prompt.prompt_id,
                        input_text=ex.get("input", ""),
                        output_text=ex.get("output", ""),
                        description=ex.get("description")
                    )
                    session.add(example)
                
            session.commit()
            session.refresh(new_prompt)
            
            # Handle SQLAlchemy detached instance issue
            result = copy.deepcopy(new_prompt)
            session.expunge(new_prompt)
            return result
        finally:
            session.close()

    def get_version_history(
        self, 
        project: str, 
        task: str,
        include_deleted: bool = False
    ) -> List[PromptORM]:
        """
        Get complete version history for a project/task.
        
        Args:
            project (str): Project name
            task (str): Task name
            include_deleted (bool): Whether to include soft-deleted prompts
            
        Returns:
            List[PromptORM]: Ordered list of prompt versions
            
        Example:
            >>> history = registry.get_version_history("blog-generator", "summarization")
            >>> for p in history:
            ...     print(f"v{p.version} by {p.updated_by} on {p.updated_at.date()}")
            "v1 by bob on 2023-01-15"
            "v2 by alice on 2023-01-20"
            "v3 by bob on 2023-02-05"
        """
        session = self.Session()
        try:
            query = session.query(PromptORM).filter_by(
                project=project,
                task=task
            )
            
            if not include_deleted:
                query = query.filter_by(is_deleted=False)
                
            # Get all versions ordered by version number
            versions = query.order_by(PromptORM.version).all()
            
            # Handle SQLAlchemy detached instance issue
            for version in versions:
                session.expunge(version)
                
            return versions
        finally:
            session.close()

    def get_prompt_lineage(
        self, 
        prompt_id: str,
        include_deleted: bool = False
    ) -> Dict[str, Any]:
        """
        Get full lineage (ancestors and descendants) of a prompt.
        
        Args:
            prompt_id (str): Prompt ID to find lineage for
            include_deleted (bool): Whether to include soft-deleted prompts
            
        Returns:
            Dict[str, Any]: Dict with ancestors, current prompt, and descendants
            
        Example:
            >>> lineage = registry.get_prompt_lineage("550e8400-e29b-41d4-a716-446655440000")
            >>> print(f"Ancestors: {len(lineage['ancestors'])}, Descendants: {len(lineage['descendants'])}")
            "Ancestors: 2, Descendants: 1"
        """
        session = self.Session()
        try:
            result = {
                "ancestors": [],
                "current": None,
                "descendants": []
            }
            
            # Get the current prompt
            current = session.query(PromptORM).filter_by(prompt_id=prompt_id).first()
            if not current:
                return result
                
            # Handle SQLAlchemy detached instance issue
            result["current"] = copy.deepcopy(current)
            
            # Get ancestors (follow parent_id recursively)
            ancestor = current
            while ancestor.parent_id:
                parent_query = session.query(PromptORM).filter_by(prompt_id=ancestor.parent_id)
                if not include_deleted:
                    parent_query = parent_query.filter_by(is_deleted=False)
                    
                parent = parent_query.first()
                if parent:
                    # Handle SQLAlchemy detached instance issue
                    result["ancestors"].append(copy.deepcopy(parent))
                    ancestor = parent
                else:
                    break
                    
            # Reverse so oldest is first
            result["ancestors"].reverse()
            
            # Get descendants (follow children recursively)
            def get_children(parent_id):
                children_query = session.query(PromptORM).filter_by(parent_id=parent_id)
                if not include_deleted:
                    children_query = children_query.filter_by(is_deleted=False)
                    
                return children_query.all()
                
            descendants = []
            to_process = get_children(prompt_id)
            
            while to_process:
                child = to_process.pop(0)
                # Handle SQLAlchemy detached instance issue
                descendants.append(copy.deepcopy(child))
                to_process.extend(get_children(child.prompt_id))
                
            result["descendants"] = descendants
            
            return result
        finally:
            session.close()

    def compare_versions(
        self, 
        prompt_id_1: str, 
        prompt_id_2: str
    ) -> Dict[str, Any]:
        """
        Compare two prompt versions and return differences.
        
        Args:
            prompt_id_1 (str): First prompt ID to compare
            prompt_id_2 (str): Second prompt ID to compare
            
        Returns:
            Dict[str, Any]: Differences in template, metadata, tags, variables
            
        Example:
            >>> diff = registry.compare_versions(
            ...     "550e8400-e29b-41d4-a716-446655440000", 
            ...     "661f9500-f30a-52e5-b827-557766551111"
            ... )
            >>> print(f"Template changes: {len(diff['template_diff'])}")
            "Template changes: 3"
        """
        import difflib
        
        session = self.Session()
        try:
            prompt1 = session.query(PromptORM).filter_by(prompt_id=prompt_id_1).first()
            prompt2 = session.query(PromptORM).filter_by(prompt_id=prompt_id_2).first()
            
            if not prompt1 or not prompt2:
                return {"error": "One or both prompts not found"}
                
            # Compare templates
            template_diff = list(difflib.ndiff(
                prompt1.template.splitlines(),
                prompt2.template.splitlines()
            ))
            
            # Compare metadata
            meta1 = prompt1.meta or {}
            meta2 = prompt2.meta or {}
            
            meta_changes = {
                "added": {},
                "removed": {},
                "changed": {}
            }
            
            all_keys = set(meta1.keys()) | set(meta2.keys())
            for key in all_keys:
                if key not in meta1:
                    meta_changes["added"][key] = meta2[key]
                elif key not in meta2:
                    meta_changes["removed"][key] = meta1[key]
                elif meta1[key] != meta2[key]:
                    meta_changes["changed"][key] = {
                        "from": meta1[key],
                        "to": meta2[key]
                    }
                    
            # Compare tags
            tags1 = set(json.loads(prompt1.tags or "[]"))
            tags2 = set(json.loads(prompt2.tags or "[]"))
            
            tags_added = list(tags2 - tags1)
            tags_removed = list(tags1 - tags2)
            
            # Compare variables
            vars1 = set(prompt1.template_variables or [])
            vars2 = set(prompt2.template_variables or [])
            
            vars_added = list(vars2 - vars1)
            vars_removed = list(vars1 - vars2)
            
            # Prepare prompts for output (avoid serialization issues)
            prompt1_dict = {
                "prompt_id": prompt1.prompt_id,
                "version": prompt1.version,
                "updated_by": prompt1.updated_by,
                "updated_at": prompt1.updated_at.isoformat() if prompt1.updated_at else None
            }
            
            prompt2_dict = {
                "prompt_id": prompt2.prompt_id,
                "version": prompt2.version,
                "updated_by": prompt2.updated_by,
                "updated_at": prompt2.updated_at.isoformat() if prompt2.updated_at else None
            }
            
            return {
                "template_diff": template_diff,
                "meta_changes": meta_changes,
                "tags_changes": {
                    "added": tags_added,
                    "removed": tags_removed
                },
                "variables_changes": {
                    "added": vars_added,
                    "removed": vars_removed
                },
                "prompts": {
                    "first": prompt1_dict,
                    "second": prompt2_dict
                }
            }
        finally:
            session.close()

    def rollback_to_version(
        self, 
        prompt_id: str, 
        updated_by: Optional[str] = None
    ) -> Optional[PromptORM]:
        """
        Create a new version by copying an old version (rollback).
        
        Args:
            prompt_id (str): Prompt ID to rollback to
            updated_by (str, optional): User performing the rollback
            
        Returns:
            Optional[PromptORM]: The new prompt version or None if not found
            
        Example:
            >>> new_prompt = registry.rollback_to_version(
            ...     "550e8400-e29b-41d4-a716-446655440000",
            ...     updated_by="alice"
            ... )
            >>> print(f"Rolled back to create v{new_prompt.version}")
            "Rolled back to create v4"
        """
        session = self.Session()
        try:
            old_prompt = session.query(PromptORM).filter_by(
                prompt_id=prompt_id,
                is_deleted=False
            ).first()
            
            if not old_prompt:
                return None
                
            # Get latest version
            latest_version = (
                session.query(func.max(PromptORM.version))
                .filter_by(
                    project=old_prompt.project, 
                    task=old_prompt.task,
                    is_deleted=False
                )
                .scalar() or 0
            )
            
            # Create new version based on old one
            new_prompt = PromptORM(
                prompt_id=str(uuid.uuid4()),
                project=old_prompt.project,
                task=old_prompt.task,
                template=old_prompt.template,  # Copy the old template
                version=latest_version + 1,
                alias=None,  # Don't transfer alias
                tags=old_prompt.tags,
                meta=old_prompt.meta.copy() if old_prompt.meta else {},
                parent_id=old_prompt.prompt_id,  # Link to source
                template_variables=old_prompt.template_variables,
                updated_by=updated_by,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Add metadata about rollback
            if new_prompt.meta is None:
                new_prompt.meta = {}
                
            new_prompt.meta["rollback"] = {
                "from_version": old_prompt.version,
                "from_id": old_prompt.prompt_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            session.add(new_prompt)
            
            # Copy tags
            try:
                tags = json.loads(old_prompt.tags or "[]")
                for tag in tags:
                    if tag:
                        prompt_tag = PromptTagORM(prompt_id=new_prompt.prompt_id, tag_name=tag)
                        session.add(prompt_tag)
            except:
                pass
            
            session.commit()
            session.refresh(new_prompt)
            
            # Handle SQLAlchemy detached instance issue
            result = copy.deepcopy(new_prompt)
            session.expunge(new_prompt)
            return result
        finally:
            session.close()

    def soft_delete_prompt(
        self, 
        prompt_id: str, 
        deleted_by: Optional[str] = None
    ) -> bool:
        """
        Soft delete a prompt (mark as deleted).
        
        Args:
            prompt_id (str): Prompt ID to soft delete
            deleted_by (str, optional): User performing the deletion
            
        Returns:
            bool: True if deleted, False if not found
            
        Example:
            >>> success = registry.soft_delete_prompt(
            ...     "550e8400-e29b-41d4-a716-446655440000",
            ...     deleted_by="bob"
            ... )
            >>> print(f"Deleted: {success}")
            "Deleted: True"
        """
        session = self.Session()
        try:
            prompt = session.query(PromptORM).filter_by(prompt_id=prompt_id).first()
            
            if not prompt:
                return False
                
            # Mark as deleted
            prompt.is_deleted = True
            
            # Record who deleted
            if prompt.meta is None:
                prompt.meta = {}
                
            prompt.meta["deleted"] = {
                "by": deleted_by,
                "at": datetime.utcnow().isoformat()
            }
            
            # Remove any aliases
            if prompt.alias:
                prompt.alias = None
                
            session.commit()
            return True
        finally:
            session.close()

    def restore_prompt(self, prompt_id: str) -> bool:
        """
        Restore a soft-deleted prompt.
        
        Args:
            prompt_id (str): Prompt ID to restore
            
        Returns:
            bool: True if restored, False if not found or not deleted
            
        Example:
            >>> success = registry.restore_prompt("550e8400-e29b-41d4-a716-446655440000")
            >>> print(f"Restored: {success}")
            "Restored: True"
        """
        session = self.Session()
        try:
            prompt = session.query(PromptORM).filter_by(
                prompt_id=prompt_id,
                is_deleted=True
            ).first()
            
            if not prompt:
                return False
                
            prompt.is_deleted = False
            
            # Record restoration
            if prompt.meta is None:
                prompt.meta = {}
                
            prompt.meta["restored"] = {
                "at": datetime.utcnow().isoformat()
            }
            
            session.commit()
            return True
        finally:
            session.close()

    def delete_prompt_by_id(self, prompt_id: str) -> bool:
        """
        Hard delete a prompt (use with caution).
        
        Args:
            prompt_id (str): Prompt ID to delete
            
        Returns:
            bool: True if deleted, False if not found
            
        Example:
            >>> success = registry.delete_prompt_by_id("550e8400-e29b-41d4-a716-446655440000")
            >>> print(f"Deleted: {success}")
            "Deleted: True"
        """
        session = self.Session()
        try:
            prompt = session.query(PromptORM).filter_by(prompt_id=prompt_id).first()
            
            if prompt:
                session.delete(prompt)
                session.commit()
                return True
                
            return False
        finally:
            session.close()

    def delete_project(self, project: str, use_soft_delete: bool = True) -> int:
        """
        Delete all prompts in a project.
        
        Args:
            project (str): Project name to delete
            use_soft_delete (bool): Whether to use soft delete or hard delete
            
        Returns:
            int: Number of prompts deleted
            
        Example:
            >>> deleted = registry.delete_project("old-experiments", use_soft_delete=True)
            >>> print(f"Deleted {deleted} prompts")
            "Deleted 15 prompts"
        """
        session = self.Session()
        try:
            if use_soft_delete:
                # Soft delete - mark prompts as deleted
                count = session.query(PromptORM).filter_by(
                    project=project,
                    is_deleted=False
                ).update({
                    "is_deleted": True,
                    "alias": None  # Remove aliases
                })
            else:
                # Hard delete - remove from database
                count = session.query(PromptORM).filter_by(project=project).delete()
                
            session.commit()
            return count
        finally:
            session.close()

    def delete_prompts_by_project_task(
        self, 
        project: str, 
        task: str,
        use_soft_delete: bool = True
    ) -> int:
        """
        Delete all prompts for a task in a project.
        
        Args:
            project (str): Project name
            task (str): Task name
            use_soft_delete (bool): Whether to use soft delete or hard delete
            
        Returns:
            int: Number of prompts deleted
            
        Example:
            >>> deleted = registry.delete_prompts_by_project_task(
            ...     "content-generator", 
            ...     "translation",
            ...     use_soft_delete=True
            ... )
            >>> print(f"Deleted {deleted} prompts")
            "Deleted 7 prompts"
        """
        session = self.Session()
        try:
            if use_soft_delete:
                # Soft delete - mark prompts as deleted
                count = session.query(PromptORM).filter_by(
                    project=project,
                    task=task,
                    is_deleted=False
                ).update({
                    "is_deleted": True,
                    "alias": None  # Remove aliases
                })
            else:
                # Hard delete - remove from database
                count = session.query(PromptORM).filter_by(
                    project=project,
                    task=task
                ).delete()
                
            session.commit()
            return count
        finally:
            session.close()

    def search_prompts(
        self, 
        query: str,
        project: Optional[str] = None,
        tags: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[PromptORM], int]:
        """
        Search prompts with filtering and pagination.
        
        Args:
            query (str): Search text
            project (str, optional): Limit to specific project
            tags (List[str], optional): Filter by tags
            page (int): Page number (starts at 1)
            page_size (int): Items per page
            
        Returns:
            Tuple[List[PromptORM], int]: List of prompts and total count
            
        Example:
            >>> prompts, total = registry.search_prompts(
            ...     query="summarize",
            ...     project="blog-generator",
            ...     tags=["prod"],
            ...     page=1,
            ...     page_size=20
            ... )
            >>> print(f"Found {total} matching prompts")
            "Found 12 matching prompts"
        """
        session = self.Session()
        try:
            # Base query
            search = session.query(PromptORM).filter_by(is_deleted=False)
            
            # Apply project filter if provided
            if project:
                search = search.filter_by(project=project)
                
            # Apply tag filters if provided
            if tags:
                for tag in tags:
                    # This would be more efficient with proper tag schema
                    tag_pattern = f"%\"{tag}\"%"  # Match in JSON array
                    search = search.filter(PromptORM.tags.ilike(tag_pattern))
                
            # Apply text search
            search_pattern = f"%{query}%"
            search = search.filter(
                or_(
                    PromptORM.template.ilike(search_pattern),
                    PromptORM.task.ilike(search_pattern),
                    PromptORM.project.ilike(search_pattern),
                    PromptORM.prompt_id.ilike(search_pattern)
                )
            )
            
            # Get total count for pagination
            total_count = search.count()
            
            # Apply pagination
            search = search.order_by(
                PromptORM.project,
                PromptORM.task,
                PromptORM.version.desc()
            )
            search = search.offset((page - 1) * page_size).limit(page_size)
            
            results = search.all()
            
            # Handle SQLAlchemy detached instance issue
            for result in results:
                session.expunge(result)
                
            return results, total_count
        finally:
            session.close()

    def bulk_tag_prompts(
        self, 
        prompt_ids: List[str], 
        tags: List[str],
        operation: str = "add"  # "add", "remove", "set"
    ) -> int:
        """
        Bulk tag operation on multiple prompts.
        
        Args:
            prompt_ids (List[str]): List of prompt IDs to modify
            tags (List[str]): Tags to add/remove/set
            operation (str): "add", "remove", or "set"
            
        Returns:
            int: Number of prompts modified
            
        Example:
            >>> modified = registry.bulk_tag_prompts(
            ...     prompt_ids=["id1", "id2", "id3"],
            ...     tags=["prod"],
            ...     operation="add"
            ... )
            >>> print(f"Modified {modified} prompts")
            "Modified 3 prompts"
        """
        session = self.Session()
        try:
            count = 0
            
            for prompt_id in prompt_ids:
                prompt = session.query(PromptORM).filter_by(
                    prompt_id=prompt_id,
                    is_deleted=False
                ).first()
                
                if not prompt:
                    continue
                    
                try:
                    current_tags = set(json.loads(prompt.tags or "[]"))
                    
                    if operation == "add":
                        # Add new tags
                        new_tags = list(current_tags | set(tags))
                    elif operation == "remove":
                        # Remove specified tags
                        new_tags = list(current_tags - set(tags))
                    elif operation == "set":
                        # Replace with new tags
                        new_tags = tags
                    else:
                        raise ValueError(f"Unknown operation: {operation}")
                        
                    prompt.tags = json.dumps(new_tags)
                    
                    # Update prompt_tags table
                    # First delete existing
                    session.query(PromptTagORM).filter_by(prompt_id=prompt_id).delete()
                    
                    # Add new tags
                    for tag in new_tags:
                        if tag:
                            prompt_tag = PromptTagORM(prompt_id=prompt_id, tag_name=tag)
                            session.add(prompt_tag)
                    
                    count += 1
                except Exception as e:
                    print(f"Error updating tags for {prompt_id}: {str(e)}")
                    continue
                    
            session.commit()
            return count
        finally:
            session.close()

    def render_prompt(
        self, 
        prompt_id: str, 
        variables: Dict[str, str]
    ) -> Optional[str]:
        """
        Render a prompt template with provided variables.
        
        Args:
            prompt_id (str): Prompt ID to render
            variables (Dict[str, str]): Variables to substitute
            
        Returns:
            Optional[str]: Rendered prompt or None if not found
            
        Example:
            >>> rendered = registry.render_prompt(
            ...     "550e8400-e29b-41d4-a716-446655440000",
            ...     {"input": "Climate change is a global challenge..."}
            ... )
            >>> print(rendered)
            "Summarize this text: Climate change is a global challenge..."
        """
        session = self.Session()
        try:
            prompt = session.query(PromptORM).filter_by(
                prompt_id=prompt_id,
                is_deleted=False
            ).first()
            
            if not prompt:
                return None
                
            # Start with the template
            rendered = prompt.template
            
            # Replace all variables
            for key, value in variables.items():
                rendered = rendered.replace(f"{{{key}}}", str(value))
                
            return rendered
        finally:
            session.close()

    def validate_template(self, template: str) -> Dict[str, Any]:
        """
        Validate a prompt template and extract variables.
        
        Args:
            template (str): Template text to validate
            
        Returns:
            Dict[str, Any]: Validation results with variables and warnings
            
        Example:
            >>> validation = registry.validate_template("Summarize: {input} with style {style}")
            >>> print(f"Variables: {validation['variables']}")
            "Variables: ['input', 'style']"
        """
        # Extract variables
        variables = re.findall(r'\{([^{}]*)\}', template)
        unique_vars = set(variables)
        
        # Check for unclosed brackets
        unclosed_count = template.count("{") - template.count("}")
        
        # Basic validation rules
        warnings = []
        if len(template) < 10:
            warnings.append("Template is very short")
            
        if len(unique_vars) == 0:
            warnings.append("No variables found in template")
            
        if unclosed_count != 0:
            warnings.append("Unclosed brackets detected - template may be malformed")
            
        return {
            "is_valid": unclosed_count == 0,
            "variables": list(unique_vars),
            "warnings": warnings
        }

    def get_examples(self, prompt_id: str) -> List[Dict[str, Any]]:
        """
        Get examples associated with a prompt.
        
        Args:
            prompt_id (str): Prompt ID to get examples for
            
        Returns:
            List[Dict[str, Any]]: List of examples
            
        Example:
            >>> examples = registry.get_examples("550e8400-e29b-41d4-a716-446655440000")
            >>> print(f"Found {len(examples)} examples")
            "Found 3 examples"
        """
        session = self.Session()
        try:
            examples = session.query(ExampleORM).filter_by(prompt_id=prompt_id).all()
            
            result = []
            for ex in examples:
                result.append({
                    "id": ex.id,
                    "input": ex.input_text,
                    "output": ex.output_text,
                    "description": ex.description,
                    "created_at": ex.created_at.isoformat() if ex.created_at else None
                })
                
            return result
        finally:
            session.close()

    def add_example(
        self, 
        prompt_id: str, 
        input_text: str, 
        output_text: str, 
        description: Optional[str] = None
    ) -> Optional[ExampleORM]:
        """
        Add an example input/output to a prompt.
        
        Args:
            prompt_id (str): Prompt ID to add example to
            input_text (str): Example input
            output_text (str): Example output
            description (str, optional): Description of this example
            
        Returns:
            Optional[ExampleORM]: The created example or None if prompt not found
            
        Example:
            >>> example = registry.add_example(
            ...     "550e8400-e29b-41d4-a716-446655440000",
            ...     "The quick brown fox jumps over the lazy dog.",
            ...     "A fox jumps over a dog.",
            ...     "Basic summarization example"
            ... )
            >>> print(f"Example added with ID: {example.id}")
            "Example added with ID: 42"
        """
        session = self.Session()
        try:
            prompt = session.query(PromptORM).filter_by(
                prompt_id=prompt_id,
                is_deleted=False
            ).first()
            
            if not prompt:
                return None
                
            example = ExampleORM(
                prompt_id=prompt_id,
                input_text=input_text,
                output_text=output_text,
                description=description
            )
            
            session.add(example)
            session.commit()
            session.refresh(example)
            
            # Handle SQLAlchemy detached instance issue
            result = copy.deepcopy(example)
            session.expunge(example)
            return result
        finally:
            session.close()

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get database usage statistics.
        
        Returns:
            Dict[str, Any]: Various statistics about the registry
            
        Example:
            >>> stats = registry.get_usage_stats()
            >>> print(f"Total prompts: {stats['total_prompts']}")
            "Total prompts: 157"
        """
        session = self.Session()
        try:
            stats = {
                "total_prompts": session.query(PromptORM).count(),
                "active_prompts": session.query(PromptORM).filter_by(is_deleted=False).count(),
                "deleted_prompts": session.query(PromptORM).filter_by(is_deleted=True).count(),
                "total_projects": len(set([p[0] for p in session.query(PromptORM.project).distinct() if p[0]])),
                "total_tasks": len(set([p[0] for p in session.query(PromptORM.task).distinct() if p[0]])),
                "prompts_with_aliases": session.query(PromptORM).filter(
                    PromptORM.alias.isnot(None),
                    PromptORM.is_deleted == False
                ).count(),
                "average_template_length": session.query(func.avg(func.length(PromptORM.template))).scalar(),
                "total_examples": session.query(ExampleORM).count()
            }
            
            # Get most active projects
            project_counts = Counter()
            for p in session.query(PromptORM.project).all():
                if p[0]:
                    project_counts[p[0]] += 1
                    
            stats["most_active_projects"] = project_counts.most_common(5)
            
            # Get tag stats
            tag_stats = self.get_tag_stats()
            stats["top_tags"] = tag_stats.most_common(10)
            
            return stats
        finally:
            session.close()

    def export_prompts(
        self, 
        project: Optional[str] = None,
        format: str = "json"
    ) -> str:
        """
        Export prompts to a portable format (JSON/YAML).
        
        Args:
            project (str, optional): Limit to specific project
            format (str): "json" or "yaml"
            
        Returns:
            str: Exported data in selected format
            
        Example:
            >>> exported = registry.export_prompts(project="blog-generator", format="json")
            >>> print(f"Exported data length: {len(exported)} bytes")
            "Exported data length: 24560 bytes"
        """
        session = self.Session()
        try:
            # Build query
            query = session.query(PromptORM).filter_by(is_deleted=False)
            if project:
                query = query.filter_by(project=project)
                
            prompts = query.all()
            
            # Convert to serializable format
            export_data = []
            for p in prompts:
                try:
                    # Get examples for this prompt
                    examples = []
                    for ex in session.query(ExampleORM).filter_by(prompt_id=p.prompt_id).all():
                        examples.append({
                            "input": ex.input_text,
                            "output": ex.output_text,
                            "description": ex.description
                        })
                    
                    # Convert datetime objects to strings
                    created_at = p.created_at.isoformat() if p.created_at else None
                    updated_at = p.updated_at.isoformat() if p.updated_at else None
                    
                    # Ensure tags are properly parsed
                    try:
                        tags = json.loads(p.tags or "[]")
                    except:
                        tags = []
                    
                    prompt_data = {
                        "prompt_id": p.prompt_id,
                        "project": p.project,
                        "task": p.task,
                        "template": p.template,
                        "version": p.version,
                        "alias": p.alias,
                        "tags": tags,
                        "meta": p.meta or {},
                        "parent_id": p.parent_id,
                        "template_variables": p.template_variables or [],
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "updated_by": p.updated_by,
                        "examples": examples
                    }
                    export_data.append(prompt_data)
                except Exception as e:
                    print(f"Error exporting prompt {p.prompt_id}: {str(e)}")
                    
            # Format the output
            if format.lower() == "json":
                return json.dumps(export_data, indent=2)
            elif format.lower() == "yaml":
                import yaml
                return yaml.dump(export_data, default_flow_style=False)
            else:
                raise ValueError(f"Unsupported export format: {format}")
        finally:
            session.close()

    def import_prompts(
        self, 
        data: str,
        format: str = "json",
        skip_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Import prompts from JSON/YAML format.
        
        Args:
            data (str): Data to import
            format (str): "json" or "yaml"
            skip_existing (bool): Whether to skip existing prompts
            
        Returns:
            Dict[str, Any]: Import results statistics
            
        Example:
            >>> results = registry.import_prompts(json_data, format="json")
            >>> print(f"Imported: {results['imported']}, Skipped: {results['skipped']}")
            "Imported: 25, Skipped: 3"
        """
        # Parse the input
        if format.lower() == "json":
            try:
                prompts_data = json.loads(data)
                # Handle empty array
                if not prompts_data:
                    prompts_data = []
            except Exception as e:
                return {"error": f"Invalid JSON: {str(e)}"}
        elif format.lower() == "yaml":
            try:
                import yaml
                prompts_data = yaml.safe_load(data)
                # Handle empty YAML document
                if not prompts_data:
                    prompts_data = []
            except Exception as e:
                return {"error": f"Invalid YAML: {str(e)}"}
        else:
            return {"error": f"Unsupported import format: {format}"}
            
        # Handle case where data isn't a list
        if not isinstance(prompts_data, list):
            return {
                "error": f"Expected a list of prompts, got {type(prompts_data).__name__}",
                "total": 0,
                "imported": 0,
                "skipped": 0,
                "errors": 1,
                "error_details": [f"Expected a list of prompts, got {type(prompts_data).__name__}"]
            }
            
        # Stats for import results
        stats = {
            "total": len(prompts_data),
            "imported": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": []
        }
        
        # Return early if there's nothing to import
        if not prompts_data:
            return stats
            
        session = self.Session()
        try:
            for prompt_data in prompts_data:
                try:
                    prompt_id = prompt_data.get("prompt_id")
                    
                    # Check if prompt already exists
                    if skip_existing and prompt_id:
                        existing = session.query(PromptORM).filter_by(prompt_id=prompt_id).first()
                        if existing:
                            stats["skipped"] += 1
                            continue
                            
                    # Create a new prompt with imported data
                    new_prompt = PromptORM(
                        prompt_id=prompt_id or str(uuid.uuid4()),
                        project=prompt_data.get("project"),
                        task=prompt_data.get("task", "imported"),
                        template=prompt_data.get("template", ""),
                        version=prompt_data.get("version", 1),
                        alias=prompt_data.get("alias"),
                        tags=json.dumps(prompt_data.get("tags", [])),
                        meta=prompt_data.get("meta", {}),
                        parent_id=prompt_data.get("parent_id"),
                        template_variables=prompt_data.get("template_variables", []),
                        is_deleted=False,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        updated_by=prompt_data.get("updated_by", "import")
                    )
                    
                    session.add(new_prompt)
                    
                    # Process tags
                    for tag in prompt_data.get("tags", []):
                        if tag:
                            prompt_tag = PromptTagORM(prompt_id=new_prompt.prompt_id, tag_name=tag)
                            session.add(prompt_tag)
                            
                    # Process examples
                    for ex in prompt_data.get("examples", []):
                        example = ExampleORM(
                            prompt_id=new_prompt.prompt_id,
                            input_text=ex.get("input", ""),
                            output_text=ex.get("output", ""),
                            description=ex.get("description")
                        )
                        session.add(example)
                    
                    stats["imported"] += 1
                    
                except Exception as e:
                    stats["errors"] += 1
                    stats["error_details"].append(str(e))
                    
            session.commit()
            return stats
        except Exception as e:
            session.rollback()
            stats["errors"] += 1
            stats["error_details"].append(f"Database error: {str(e)}")
            return stats
        finally:
            session.close()