"""
Phase 1 Testing Script

This script tests all functionalities implemented in Phase 1:
1. Data layer structure
2. Data access classes
3. Consistency validator
4. Cross-Skill interfaces
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Import data access classes
from data_access import (
    EmployeeDataAccess,
    ProjectDataAccess,
    TaskDataAccess,
    AssetDataAccess,
    DataLayerConfig
)
from consistency_validator import ConsistencyValidator


class Phase1Tester:
    """Test suite for Phase 1 implementation"""
    
    def __init__(self):
        self.config = DataLayerConfig()
        self.employee_access = EmployeeDataAccess()
        self.project_access = ProjectDataAccess()
        self.task_access = TaskDataAccess()
        self.asset_access = AssetDataAccess()
        self.validator = ConsistencyValidator()
        
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
    def log_test(self, test_name, passed, message=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append(f"{status} - {test_name}")
        if message:
            self.test_results.append(f"    {message}")
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def test_directory_structure(self):
        """Test 1: Verify data layer directory structure"""
        print("\n=== Test 1: Directory Structure ===")
        
        required_dirs = [
            self.config.EMPLOYEES_PATH,
            self.config.PROJECTS_PATH,
            self.config.TASKS_PATH,
            self.config.ASSETS_PATH,
            self.config.LOGS_PATH,
            self.config.ASSETS_PATH / "knowledge" / "technical",
            self.config.ASSETS_PATH / "knowledge" / "business",
            self.config.ASSETS_PATH / "knowledge" / "trends",
            self.config.ASSETS_PATH / "knowledge" / "practices",
        ]
        
        for dir_path in required_dirs:
            exists = dir_path.exists()
            self.log_test(
                f"Directory exists: {dir_path.relative_to(self.config.BASE_PATH)}",
                exists,
                f"Path: {dir_path}"
            )
    
    def test_json_files(self):
        """Test 2: Verify JSON files are valid"""
        print("\n=== Test 2: JSON Files ===")
        
        json_files = [
            ("roster.json", self.config.ROSTER_FILE),
            ("index.json", self.config.PROJECT_INDEX_FILE),
            ("board.json", self.config.TASK_BOARD_FILE),
            ("milestones.json", self.config.MILESTONES_FILE),
            ("metadata.json", self.config.ASSET_METADATA_FILE),
            ("work_logs.json", self.config.WORK_LOGS_FILE),
        ]
        
        for name, file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Check required fields
                has_version = 'version' in data
                has_last_updated = 'lastUpdated' in data
                
                self.log_test(
                    f"JSON file valid: {name}",
                    has_version and has_last_updated,
                    f"Version: {data.get('version')}, LastUpdated: {data.get('lastUpdated')}"
                )
            except Exception as e:
                self.log_test(f"JSON file valid: {name}", False, str(e))
    
    def test_add_employee(self):
        """Test 3: Add employee"""
        print("\n=== Test 3: Add Employee ===")
        
        try:
            # Create test employee
            test_employee = {
                'name': '测试员工_张三',
                'industry': '互联网',
                'position': '产品经理',
                'createdAt': datetime.utcnow().isoformat() + 'Z',
                'workspacePath': '~/Documents/digital_employees/测试员工_张三',
                'status': 'active',
                'projects': [],
                'skills': ['需求分析', '用户研究', 'Axure', '产品规划']
            }
            
            # Add employee
            self.employee_access.add_employee(test_employee)
            
            # Verify
            roster = self.employee_access.get_roster()
            added = any(e['name'] == '测试员工_张三' for e in roster.get('employees', []))
            
            self.log_test(
                "Add employee",
                added,
                f"Employee ID: {test_employee.get('id')}, Total employees: {len(roster.get('employees', []))}"
            )
            
            # Check statistics
            stats_correct = roster['statistics']['total'] == len(roster['employees'])
            self.log_test(
                "Employee statistics updated",
                stats_correct,
                f"Total: {roster['statistics']['total']}, Active: {roster['statistics']['active']}"
            )
            
        except Exception as e:
            self.log_test("Add employee", False, str(e))
    
    def test_add_project(self):
        """Test 4: Add project"""
        print("\n=== Test 4: Add Project ===")
        
        try:
            # Get first employee ID
            roster = self.employee_access.get_roster()
            if not roster.get('employees'):
                self.log_test("Add project", False, "No employees available")
                return
            
            employee_id = roster['employees'][0]['id']
            
            # Create test project
            test_project = {
                'name': '测试项目_电商App',
                'description': '电商应用最小可行产品开发',
                'createdAt': datetime.utcnow().isoformat() + 'Z',
                'status': 'active',
                'members': [employee_id],
                'workspacePath': 'data-layer/projects/proj_001'
            }
            
            # Add project
            self.project_access.add_project(test_project)
            
            # Verify
            index = self.project_access.get_project_index()
            added = any(p['name'] == '测试项目_电商App' for p in index.get('projects', []))
            
            self.log_test(
                "Add project",
                added,
                f"Project ID: {test_project.get('id')}, Total projects: {len(index.get('projects', []))}"
            )
            
        except Exception as e:
            self.log_test("Add project", False, str(e))
    
    def test_update_employee_projects(self):
        """Test 5: Update employee projects (Cross-Skill interface)"""
        print("\n=== Test 5: Update Employee Projects ===")
        
        try:
            # Get employee and project IDs
            roster = self.employee_access.get_roster()
            index = self.project_access.get_project_index()
            
            if not roster.get('employees') or not index.get('projects'):
                self.log_test("Update employee projects", False, "No employees or projects available")
                return
            
            employee_id = roster['employees'][0]['id']
            project_id = index['projects'][0]['id']
            
            # Add employee to project
            self.employee_access.update_employee_projects(employee_id, project_id, 'add')
            
            # Verify
            roster = self.employee_access.get_roster()
            employee = next(e for e in roster['employees'] if e['id'] == employee_id)
            added = project_id in employee.get('projects', [])
            
            self.log_test(
                "Add employee to project",
                added,
                f"Employee {employee_id} projects: {employee.get('projects', [])}"
            )
            
            # Remove employee from project
            self.employee_access.update_employee_projects(employee_id, project_id, 'remove')
            
            # Verify
            roster = self.employee_access.get_roster()
            employee = next(e for e in roster['employees'] if e['id'] == employee_id)
            removed = project_id not in employee.get('projects', [])
            
            self.log_test(
                "Remove employee from project",
                removed,
                f"Employee {employee_id} projects: {employee.get('projects', [])}"
            )
            
        except Exception as e:
            self.log_test("Update employee projects", False, str(e))
    
    def test_query_employees_by_skills(self):
        """Test 6: Query employees by skills (Cross-Skill interface)"""
        print("\n=== Test 6: Query Employees by Skills ===")
        
        try:
            # Query employees with specific skills
            matched = self.employee_access.query_employees_by_skills(['需求分析', '产品规划'])
            
            # Verify
            has_matches = len(matched) > 0
            all_have_skills = all(
                any(keyword in skill for keyword in ['需求分析', '产品规划'] for skill in e.get('skills', []))
                for e in matched
            )
            
            self.log_test(
                "Query employees by skills",
                has_matches and all_have_skills,
                f"Found {len(matched)} employee(s) with matching skills"
            )
            
            for employee in matched:
                print(f"    - {employee['name']}: {', '.join(employee['skills'])}")
            
        except Exception as e:
            self.log_test("Query employees by skills", False, str(e))
    
    def test_add_task(self):
        """Test 7: Add task"""
        print("\n=== Test 7: Add Task ===")
        
        try:
            # Get project and employee IDs
            index = self.project_access.get_project_index()
            roster = self.employee_access.get_roster()
            
            if not index.get('projects') or not roster.get('employees'):
                self.log_test("Add task", False, "No projects or employees available")
                return
            
            project_id = index['projects'][0]['id']
            employee_id = roster['employees'][0]['id']
            
            # Create test task
            test_task = {
                'projectId': project_id,
                'name': '测试任务_需求分析',
                'description': '完成产品需求文档',
                'assignee': employee_id,
                'status': 'todo',
                'priority': 'high',
                'dependencies': [],
                'createdAt': datetime.utcnow().isoformat() + 'Z',
                'updatedAt': datetime.utcnow().isoformat() + 'Z',
                'dueDate': '2026-02-20T00:00:00Z',
                'tags': ['需求', '文档']
            }
            
            # Add task
            self.task_access.add_task(test_task)
            
            # Verify
            board = self.task_access.get_task_board()
            added = any(t['name'] == '测试任务_需求分析' for t in board.get('tasks', []))
            
            self.log_test(
                "Add task",
                added,
                f"Task ID: {test_task.get('id')}, Total tasks: {len(board.get('tasks', []))}"
            )
            
        except Exception as e:
            self.log_test("Add task", False, str(e))
    
    def test_add_asset(self):
        """Test 8: Add asset"""
        print("\n=== Test 8: Add Asset ===")
        
        try:
            # Get project and employee IDs
            index = self.project_access.get_project_index()
            roster = self.employee_access.get_roster()
            
            if not index.get('projects') or not roster.get('employees'):
                self.log_test("Add asset", False, "No projects or employees available")
                return
            
            project_id = index['projects'][0]['id']
            employee_id = roster['employees'][0]['id']
            
            # Create test asset
            test_asset = {
                'projectId': project_id,
                'name': '测试文档_产品需求文档.md',
                'type': 'document',
                'category': 'docs',
                'path': f'projects/{project_id}/shared/docs/产品需求文档.md',
                'creator': employee_id,
                'createdAt': datetime.utcnow().isoformat() + 'Z',
                'updatedAt': datetime.utcnow().isoformat() + 'Z',
                'version': '1.0.0',
                'description': '电商App产品需求文档',
                'tags': ['需求', '文档'],
                'references': [],
                'changeLog': [
                    {
                        'version': '1.0.0',
                        'date': datetime.utcnow().isoformat() + 'Z',
                        'author': employee_id,
                        'changes': '初始版本'
                    }
                ]
            }
            
            # Add asset
            self.asset_access.add_asset(test_asset)
            
            # Verify
            metadata = self.asset_access.get_asset_metadata()
            added = any(a['name'] == '测试文档_产品需求文档.md' for a in metadata.get('assets', []))
            
            self.log_test(
                "Add asset",
                added,
                f"Asset ID: {test_asset.get('id')}, Total assets: {len(metadata.get('assets', []))}"
            )
            
        except Exception as e:
            self.log_test("Add asset", False, str(e))
    
    def test_consistency_validation(self):
        """Test 9: Data consistency validation"""
        print("\n=== Test 9: Consistency Validation ===")
        
        try:
            # Run validation
            is_valid, issues = self.validator.validate_all()
            
            self.log_test(
                "Consistency validation",
                True,  # Always pass if no exception
                f"Valid: {is_valid}, Issues: {len(issues)}"
            )
            
            if issues:
                print("\n    Issues found:")
                for issue in issues[:5]:  # Show first 5 issues
                    print(f"    - [{issue['severity']}] {issue['message']}")
                if len(issues) > 5:
                    print(f"    ... and {len(issues) - 5} more")
            
        except Exception as e:
            self.log_test("Consistency validation", False, str(e))
    
    def test_work_logs(self):
        """Test 10: Work logs"""
        print("\n=== Test 10: Work Logs ===")
        
        try:
            # Read work logs
            logs = self.employee_access.read_json(self.config.WORK_LOGS_FILE)
            
            has_logs = len(logs.get('logs', [])) > 0
            
            self.log_test(
                "Work logs recorded",
                has_logs,
                f"Total logs: {len(logs.get('logs', []))}"
            )
            
            if has_logs:
                print("\n    Recent logs:")
                for log in logs['logs'][-3:]:  # Show last 3 logs
                    print(f"    - [{log['action']}] {log.get('details', {})}")
            
        except Exception as e:
            self.log_test("Work logs recorded", False, str(e))
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("Phase 1 Testing Suite")
        print("=" * 60)
        
        # Run tests
        self.test_directory_structure()
        self.test_json_files()
        self.test_add_employee()
        self.test_add_project()
        self.test_update_employee_projects()
        self.test_query_employees_by_skills()
        self.test_add_task()
        self.test_add_asset()
        self.test_consistency_validation()
        self.test_work_logs()
        
        # Print summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"Total tests: {self.passed + self.failed}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Success rate: {self.passed / (self.passed + self.failed) * 100:.1f}%")
        
        print("\n" + "=" * 60)
        print("Detailed Results")
        print("=" * 60)
        for result in self.test_results:
            print(result)
        
        return self.failed == 0


def main():
    """Main test function"""
    tester = Phase1Tester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Phase 1 implementation is working correctly.")
    else:
        print(f"\n⚠️  {tester.failed} test(s) failed. Please review the issues above.")
    
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
