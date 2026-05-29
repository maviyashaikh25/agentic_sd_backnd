import os
import uuid
import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional

from app.utils.db import get_db
from app.models import Project

router = APIRouter()

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    tech_stack: Optional[List[str]] = []

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    tech_stack: List[str]
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True
        from_attributes = True

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all generated or ongoing software projects."""
    result = await db.execute(select(Project))
    projects = result.scalars().all()
    return projects

@router.post("/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """Create a new project workspace."""
    project_id = f"proj_{uuid.uuid4().hex[:8]}"
    
    # Initialize physical workspace directory
    workspace_dir = os.path.join("projects_generated", project_id)
    os.makedirs(workspace_dir, exist_ok=True)

    db_project = Project(
        id=project_id,
        name=project.name,
        description=project.description,
        tech_stack=project.tech_stack,
        status="initialized"
    )
    
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    
    return db_project

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get details and metadata about a specific project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    db_project = result.scalar_one_or_none()
    
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    return db_project

@router.delete("/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a project workspace."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    db_project = result.scalar_one_or_none()
    
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    await db.delete(db_project)
    await db.commit()
    
    # Optionally clean up directory
    workspace_dir = os.path.join("projects_generated", project_id)
    if os.path.exists(workspace_dir):
        try:
            import shutil
            shutil.rmtree(workspace_dir)
        except Exception as e:
            print(f"Error cleaning up workspace folder: {e}")
            
    return {"message": f"Project {project_id} and its workspace deleted successfully."}
