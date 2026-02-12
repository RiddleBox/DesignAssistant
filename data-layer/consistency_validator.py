"""
Data Consistency Validator

This module provides tools to validate data consistency across different
modules in the shared data layer.
"""

from typing import List, Dict, Any, Tuple
from data_access import (
    EmployeeDataAccess,
    ProjectDataAccess,
    TaskDataAccess,
    AssetDataAccess
)


class ConsistencyValidator:
    """Validator for data consistency checks"""
    
    def __init__(self):
        self.employee_access = EmployeeDataAccess()
        self.project_access = ProjectDataAccess()
        self.task_access = TaskDataAccess()
        self.asset_access = AssetDataAccess()
        self.issues = []
    
    def validate_all(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Run all consistency checks
        
        Returns:
            Tuple of (is_valid, issues_list)
        """
        self.issues = []
        
        self.validate_employee_project_consistency()
        self.validate_task_project_consistency()
        self.validate_asset_project_consistency()
        self.validate_reference_integrity()
        
        return len(self.issues) == 0, self.issues
    
    def validate_employee_project_consistency(self) -> None:
        """
        Validate employee-project consistency:
        - Employee's projects field matches project's members field
        """
        roster = self.employee_access.get_roster()
        project_index = self.project_access.get_project_index()
        
        # Build project members map
        project_members = {}
        for project in project_index.get('projects', []):
            project_id = project['id']
            members = [m['employeeId'] if isinstance(m, dict) else m 
                      for m in project.get('members', [])]
            project_members[project_id] = set(members)
        
        # Check each employee
        for employee in roster.get('employees', []):
            employee_id = employee['id']
            employee_projects = set(employee.get('projects', []))
            
            # Check if employee is listed in all their projects
            for project_id in employee_projects:
                if project_id not in project_members:
                    self.issues.append({
                        'type': 'employee_project_mismatch',
                        'severity': 'error',
                        'message': f"Employee {employee_id} references non-existent project {project_id}",
                        'employeeId': employee_id,
                        'projectId': project_id
                    })
                elif employee_id not in project_members[project_id]:
                    self.issues.append({
                        'type': 'employee_project_mismatch',
                        'severity': 'warning',
                        'message': f"Employee {employee_id} lists project {project_id} but is not in project members",
                        'employeeId': employee_id,
                        'projectId': project_id
                    })
            
            # Check if employee is in projects they don't list
            for project_id, members in project_members.items():
                if employee_id in members and project_id not in employee_projects:
                    self.issues.append({
                        'type': 'employee_project_mismatch',
                        'severity': 'warning',
                        'message': f"Employee {employee_id} is in project {project_id} members but doesn't list it",
                        'employeeId': employee_id,
                        'projectId': project_id
                    })
    
    def validate_task_project_consistency(self) -> None:
        """
        Validate task-project consistency:
        - Task's projectId exists in project index
        - Task's assignee is a project member
        """
        task_board = self.task_access.get_task_board()
        project_index = self.project_access.get_project_index()
        
        # Build project map
        projects = {p['id']: p for p in project_index.get('projects', [])}
        
        for task in task_board.get('tasks', []):
            task_id = task['id']
            project_id = task.get('projectId')
            assignee = task.get('assignee')
            
            # Check if project exists
            if project_id and project_id not in projects:
                self.issues.append({
                    'type': 'task_project_mismatch',
                    'severity': 'error',
                    'message': f"Task {task_id} references non-existent project {project_id}",
                    'taskId': task_id,
                    'projectId': project_id
                })
            
            # Check if assignee is project member
            if project_id and assignee and project_id in projects:
                project = projects[project_id]
                members = [m['employeeId'] if isinstance(m, dict) else m 
                          for m in project.get('members', [])]
                
                if assignee not in members:
                    self.issues.append({
                        'type': 'task_assignee_not_member',
                        'severity': 'warning',
                        'message': f"Task {task_id} assigned to {assignee} who is not a member of project {project_id}",
                        'taskId': task_id,
                        'assignee': assignee,
                        'projectId': project_id
                    })
    
    def validate_asset_project_consistency(self) -> None:
        """
        Validate asset-project consistency:
        - Asset's projectId exists in project index
        - Asset's creator is a project member
        """
        asset_metadata = self.asset_access.get_asset_metadata()
        project_index = self.project_access.get_project_index()
        
        # Build project map
        projects = {p['id']: p for p in project_index.get('projects', [])}
        
        for asset in asset_metadata.get('assets', []):
            asset_id = asset['id']
            project_id = asset.get('projectId')
            creator = asset.get('creator')
            
            # Check if project exists
            if project_id and project_id not in projects:
                self.issues.append({
                    'type': 'asset_project_mismatch',
                    'severity': 'error',
                    'message': f"Asset {asset_id} references non-existent project {project_id}",
                    'assetId': asset_id,
                    'projectId': project_id
                })
            
            # Check if creator is project member
            if project_id and creator and project_id in projects:
                project = projects[project_id]
                members = [m['employeeId'] if isinstance(m, dict) else m 
                          for m in project.get('members', [])]
                
                if creator not in members:
                    self.issues.append({
                        'type': 'asset_creator_not_member',
                        'severity': 'warning',
                        'message': f"Asset {asset_id} created by {creator} who is not a member of project {project_id}",
                        'assetId': asset_id,
                        'creator': creator,
                        'projectId': project_id
                    })
    
    def validate_reference_integrity(self) -> None:
        """
        Validate reference integrity:
        - Asset references exist
        - Task dependencies exist
        """
        # Validate asset references
        asset_metadata = self.asset_access.get_asset_metadata()
        asset_ids = {a['id'] for a in asset_metadata.get('assets', [])}
        
        for asset in asset_metadata.get('assets', []):
            asset_id = asset['id']
            references = asset.get('references', [])
            
            for ref_id in references:
                if ref_id not in asset_ids:
                    self.issues.append({
                        'type': 'broken_asset_reference',
                        'severity': 'error',
                        'message': f"Asset {asset_id} references non-existent asset {ref_id}",
                        'assetId': asset_id,
                        'referenceId': ref_id
                    })
        
        # Validate task dependencies
        task_board = self.task_access.get_task_board()
        task_ids = {t['id'] for t in task_board.get('tasks', [])}
        
        for task in task_board.get('tasks', []):
            task_id = task['id']
            dependencies = task.get('dependencies', [])
            
            for dep_id in dependencies:
                if dep_id not in task_ids:
                    self.issues.append({
                        'type': 'broken_task_dependency',
                        'severity': 'error',
                        'message': f"Task {task_id} depends on non-existent task {dep_id}",
                        'taskId': task_id,
                        'dependencyId': dep_id
                    })
    
    def get_report(self) -> str:
        """Generate a human-readable consistency report"""
        if not self.issues:
            return "✓ All consistency checks passed!"
        
        report = [f"Found {len(self.issues)} consistency issue(s):\n"]
        
        errors = [i for i in self.issues if i['severity'] == 'error']
        warnings = [i for i in self.issues if i['severity'] == 'warning']
        
        if errors:
            report.append(f"\n❌ Errors ({len(errors)}):")
            for issue in errors:
                report.append(f"  - {issue['message']}")
        
        if warnings:
            report.append(f"\n⚠️  Warnings ({len(warnings)}):")
            for issue in warnings:
                report.append(f"  - {issue['message']}")
        
        return "\n".join(report)


def validate_data_layer() -> None:
    """Run validation and print report"""
    validator = ConsistencyValidator()
    is_valid, issues = validator.validate_all()
    
    print(validator.get_report())
    
    if not is_valid:
        print("\n💡 Tip: Fix errors first, then address warnings.")


if __name__ == '__main__':
    validate_data_layer()
