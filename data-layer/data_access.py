"""
Data Layer Access Module

This module provides base classes and utilities for accessing and managing
the shared data layer across different Skills.

Data Access Rules:
- Each Skill can READ data from other Skills
- Each Skill can only WRITE to its own data domain
- All data changes must be logged
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class DataLayerConfig:
    """Configuration for data layer paths"""
    
    BASE_PATH = Path("data-layer")
    
    # Module paths
    EMPLOYEES_PATH = BASE_PATH / "employees"
    PROJECTS_PATH = BASE_PATH / "projects"
    TASKS_PATH = BASE_PATH / "tasks"
    ASSETS_PATH = BASE_PATH / "assets"
    LOGS_PATH = BASE_PATH / "logs"
    
    # Data files
    ROSTER_FILE = EMPLOYEES_PATH / "roster.json"
    PROJECT_INDEX_FILE = PROJECTS_PATH / "index.json"
    TASK_BOARD_FILE = TASKS_PATH / "board.json"
    MILESTONES_FILE = TASKS_PATH / "milestones.json"
    ASSET_METADATA_FILE = ASSETS_PATH / "metadata.json"
    WORK_LOGS_FILE = LOGS_PATH / "work_logs.json"


class DataAccessBase:
    """Base class for data access operations"""
    
    def __init__(self, config: DataLayerConfig = None):
        self.config = config or DataLayerConfig()
    
    def read_json(self, file_path: Path) -> Dict[str, Any]:
        """Read JSON file and return data"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
    
    def write_json(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Write data to JSON file"""
        # Update lastUpdated timestamp
        data['lastUpdated'] = datetime.utcnow().isoformat() + 'Z'
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write with pretty formatting
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def log_change(self, action: str, details: Dict[str, Any]) -> None:
        """Log data change to work logs"""
        logs = self.read_json(self.config.WORK_LOGS_FILE)
        
        if 'logs' not in logs:
            logs['logs'] = []
        
        log_entry = {
            'id': f"log_{len(logs['logs']) + 1:03d}",
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'action': action,
            'details': details
        }
        
        logs['logs'].append(log_entry)
        self.write_json(self.config.WORK_LOGS_FILE, logs)


class EmployeeDataAccess(DataAccessBase):
    """Data access for employee data (Skill 1)"""
    
    def get_roster(self) -> Dict[str, Any]:
        """Get employee roster"""
        return self.read_json(self.config.ROSTER_FILE)
    
    def update_roster(self, roster: Dict[str, Any]) -> None:
        """Update employee roster"""
        self.write_json(self.config.ROSTER_FILE, roster)
        self.log_change('roster_updated', {'count': len(roster.get('employees', []))})
    
    def add_employee(self, employee: Dict[str, Any]) -> None:
        """Add new employee to roster"""
        roster = self.get_roster()
        
        if 'employees' not in roster:
            roster['employees'] = []
        
        # Generate ID if not provided
        if 'id' not in employee:
            employee['id'] = f"emp_{len(roster['employees']) + 1:03d}"
        
        roster['employees'].append(employee)
        
        # Update statistics
        roster['statistics'] = {
            'total': len(roster['employees']),
            'active': sum(1 for e in roster['employees'] if e.get('status') == 'active'),
            'inactive': sum(1 for e in roster['employees'] if e.get('status') == 'inactive')
        }
        
        self.update_roster(roster)
        self.log_change('employee_added', {'employeeId': employee['id'], 'name': employee.get('name')})
    
    def update_employee_projects(self, employee_id: str, project_id: str, operation: str) -> None:
        """Update employee's project list (called by Skill 2)"""
        roster = self.get_roster()
        
        for employee in roster.get('employees', []):
            if employee['id'] == employee_id:
                if 'projects' not in employee:
                    employee['projects'] = []
                
                if operation == 'add' and project_id not in employee['projects']:
                    employee['projects'].append(project_id)
                elif operation == 'remove' and project_id in employee['projects']:
                    employee['projects'].remove(project_id)
                
                break
        
        self.update_roster(roster)
        self.log_change('employee_projects_updated', {
            'employeeId': employee_id,
            'projectId': project_id,
            'operation': operation
        })
    
    def query_employees_by_skills(self, skill_keywords: List[str]) -> List[Dict[str, Any]]:
        """Query employees by skill keywords (called by Skill 2)"""
        roster = self.get_roster()
        matched_employees = []
        
        for employee in roster.get('employees', []):
            employee_skills = employee.get('skills', [])
            if any(keyword.lower() in skill.lower() for keyword in skill_keywords for skill in employee_skills):
                matched_employees.append(employee)
        
        return matched_employees


class ProjectDataAccess(DataAccessBase):
    """Data access for project data (Skill 2)"""
    
    def get_project_index(self) -> Dict[str, Any]:
        """Get project index"""
        return self.read_json(self.config.PROJECT_INDEX_FILE)
    
    def update_project_index(self, index: Dict[str, Any]) -> None:
        """Update project index"""
        self.write_json(self.config.PROJECT_INDEX_FILE, index)
        self.log_change('project_index_updated', {'count': len(index.get('projects', []))})
    
    def add_project(self, project: Dict[str, Any]) -> None:
        """Add new project"""
        index = self.get_project_index()
        
        if 'projects' not in index:
            index['projects'] = []
        
        # Generate ID if not provided
        if 'id' not in project:
            project['id'] = f"proj_{len(index['projects']) + 1:03d}"
        
        index['projects'].append(project)
        
        # Update statistics
        index['statistics'] = {
            'total': len(index['projects']),
            'active': sum(1 for p in index['projects'] if p.get('status') == 'active'),
            'completed': sum(1 for p in index['projects'] if p.get('status') == 'completed'),
            'archived': sum(1 for p in index['projects'] if p.get('status') == 'archived')
        }
        
        self.update_project_index(index)
        self.log_change('project_added', {'projectId': project['id'], 'name': project.get('name')})


class TaskDataAccess(DataAccessBase):
    """Data access for task data (Skill 3)"""
    
    def get_task_board(self) -> Dict[str, Any]:
        """Get task board"""
        return self.read_json(self.config.TASK_BOARD_FILE)
    
    def update_task_board(self, board: Dict[str, Any]) -> None:
        """Update task board"""
        self.write_json(self.config.TASK_BOARD_FILE, board)
        self.log_change('task_board_updated', {'count': len(board.get('tasks', []))})
    
    def add_task(self, task: Dict[str, Any]) -> None:
        """Add new task"""
        board = self.get_task_board()
        
        if 'tasks' not in board:
            board['tasks'] = []
        
        # Generate ID if not provided
        if 'id' not in task:
            task['id'] = f"task_{len(board['tasks']) + 1:03d}"
        
        board['tasks'].append(task)
        
        # Update statistics
        board['statistics'] = {
            'total': len(board['tasks']),
            'todo': sum(1 for t in board['tasks'] if t.get('status') == 'todo'),
            'inProgress': sum(1 for t in board['tasks'] if t.get('status') == 'inProgress'),
            'completed': sum(1 for t in board['tasks'] if t.get('status') == 'completed'),
            'blocked': sum(1 for t in board['tasks'] if t.get('status') == 'blocked')
        }
        
        self.update_task_board(board)
        self.log_change('task_added', {'taskId': task['id'], 'name': task.get('name')})


class AssetDataAccess(DataAccessBase):
    """Data access for asset data (Skill 4)"""
    
    def get_asset_metadata(self) -> Dict[str, Any]:
        """Get asset metadata"""
        return self.read_json(self.config.ASSET_METADATA_FILE)
    
    def update_asset_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update asset metadata"""
        self.write_json(self.config.ASSET_METADATA_FILE, metadata)
        self.log_change('asset_metadata_updated', {'count': len(metadata.get('assets', []))})
    
    def add_asset(self, asset: Dict[str, Any]) -> None:
        """Add new asset"""
        metadata = self.get_asset_metadata()
        
        if 'assets' not in metadata:
            metadata['assets'] = []
        
        # Generate ID if not provided
        if 'id' not in asset:
            asset['id'] = f"asset_{len(metadata['assets']) + 1:03d}"
        
        metadata['assets'].append(asset)
        
        # Update statistics
        asset_type = asset.get('type', 'other')
        if 'statistics' not in metadata:
            metadata['statistics'] = {'total': 0, 'byType': {}}
        
        metadata['statistics']['total'] = len(metadata['assets'])
        metadata['statistics']['byType'][asset_type] = metadata['statistics']['byType'].get(asset_type, 0) + 1
        
        self.update_asset_metadata(metadata)
        self.log_change('asset_added', {'assetId': asset['id'], 'name': asset.get('name')})


# Export all access classes
__all__ = [
    'DataLayerConfig',
    'DataAccessBase',
    'EmployeeDataAccess',
    'ProjectDataAccess',
    'TaskDataAccess',
    'AssetDataAccess'
]
