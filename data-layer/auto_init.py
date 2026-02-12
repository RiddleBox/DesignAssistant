"""
Auto-initialization script for data layer

This script automatically creates the complete data layer structure
when run for the first time or when data layer is missing.

Usage:
    python auto_init.py [--force]

Options:
    --force    Force re-initialization even if data layer exists
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone


class DataLayerInitializer:
    """Automatically initialize data layer structure"""
    
    def __init__(self, base_path=None, force=False):
        """
        Initialize the data layer initializer
        
        Args:
            base_path: Base path for data layer (default: current directory)
            force: Force re-initialization even if exists
        """
        self.base_path = Path(base_path) if base_path else Path(__file__).parent
        self.force = force
        
        # Define directory structure
        self.directories = [
            'employees',
            'projects',
            'tasks',
            'assets',
            'assets/knowledge',
            'assets/knowledge/technical',
            'assets/knowledge/business',
            'assets/knowledge/trends',
            'assets/knowledge/practices',
            'logs',
        ]
        
        # Define JSON file templates
        self.json_templates = {
            'employees/roster.json': {
                'version': '1.0.0',
                'lastUpdated': self._get_timestamp(),
                'employees': [],
                'statistics': {
                    'total': 0,
                    'active': 0,
                    'inactive': 0
                }
            },
            'projects/index.json': {
                'version': '1.0.0',
                'lastUpdated': self._get_timestamp(),
                'projects': [],
                'statistics': {
                    'total': 0,
                    'active': 0,
                    'completed': 0,
                    'archived': 0
                }
            },
            'tasks/board.json': {
                'version': '1.0.0',
                'lastUpdated': self._get_timestamp(),
                'tasks': [],
                'statistics': {
                    'total': 0,
                    'todo': 0,
                    'inProgress': 0,
                    'completed': 0,
                    'blocked': 0
                }
            },
            'tasks/milestones.json': {
                'version': '1.0.0',
                'lastUpdated': self._get_timestamp(),
                'milestones': []
            },
            'assets/metadata.json': {
                'version': '1.0.0',
                'lastUpdated': self._get_timestamp(),
                'assets': [],
                'statistics': {
                    'total': 0,
                    'byType': {}
                }
            },
            'logs/work_logs.json': {
                'version': '1.0.0',
                'lastUpdated': self._get_timestamp(),
                'logs': []
            }
        }
    
    def _get_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    def check_exists(self):
        """Check if data layer already exists"""
        # Check if key directories exist
        key_dirs = ['employees', 'projects', 'tasks']
        exists = all((self.base_path / d).exists() for d in key_dirs)
        
        # Check if key JSON files exist
        key_files = ['employees/roster.json', 'projects/index.json']
        exists = exists and all((self.base_path / f).exists() for f in key_files)
        
        return exists
    
    def create_directories(self):
        """Create all required directories"""
        print("[+] Creating directory structure...")
        
        created = 0
        for directory in self.directories:
            dir_path = self.base_path / directory
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"    [OK] Created: {directory}/")
                created += 1
            else:
                print(f"    [--] Exists: {directory}/")
        
        return created
    
    def create_json_files(self):
        """Create all JSON files with initial data"""
        print("\n[+] Creating JSON files...")
        
        created = 0
        for file_path, template in self.json_templates.items():
            full_path = self.base_path / file_path
            
            if not full_path.exists() or self.force:
                # Update timestamp
                template['lastUpdated'] = self._get_timestamp()
                
                # Write JSON file
                with open(full_path, 'w', encoding='utf-8') as f:
                    json.dump(template, f, ensure_ascii=False, indent=2)
                
                action = "Created" if not full_path.exists() else "Overwritten"
                print(f"    [OK] {action}: {file_path}")
                created += 1
            else:
                print(f"    [--] Exists: {file_path}")
        
        return created
    
    def create_readme(self):
        """Create README.md if not exists"""
        readme_path = self.base_path / 'README.md'
        
        if readme_path.exists() and not self.force:
            print("\n[+] README.md already exists, skipping...")
            return False
        
        readme_content = """# 数字员工协作系统 - 数据层

本目录包含数字员工协作系统的核心数据层。

## 目录结构

```
data-layer/
├── employees/          # 员工数据
│   └── roster.json    # 员工花名册
├── projects/          # 项目数据
│   └── index.json     # 项目索引
├── tasks/             # 任务数据
│   ├── board.json     # 任务看板
│   └── milestones.json # 里程碑
├── assets/            # 资产数据
│   ├── metadata.json  # 资产元数据
│   └── knowledge/     # 知识库
│       ├── technical/ # 技术知识
│       ├── business/  # 业务知识
│       ├── trends/    # 行业趋势
│       └── practices/ # 最佳实践
└── logs/              # 日志数据
    └── work_logs.json # 工作日志

```

## 使用说明

1. **首次使用**：运行 `python auto_init.py` 自动初始化数据层
2. **数据访问**：使用 `data_access.py` 中的类进行数据操作
3. **一致性校验**：运行 `python consistency_validator.py` 检查数据一致性

## 文档

- `DATA_SCHEMA.md` - 数据格式规范
- `SKILL1_API.md` - 跨Skill接口文档
- `TESTING_GUIDE.md` - 测试指南

---

*此数据层由 auto_init.py 自动生成*
"""
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print("\n[+] Created: README.md")
        return True
    
    def initialize(self):
        """Execute full initialization"""
        print("=" * 60)
        print("Data Layer Auto-Initialization")
        print("=" * 60)
        print(f"Base path: {self.base_path.absolute()}")
        
        # Check if already exists
        if self.check_exists() and not self.force:
            print("\n[!] Data layer already exists!")
            print("    Use --force to re-initialize")
            return False
        
        if self.force:
            print("\n[!] Force mode enabled - will overwrite existing files")
        
        print()
        
        # Create directories
        dirs_created = self.create_directories()
        
        # Create JSON files
        files_created = self.create_json_files()
        
        # Create README
        readme_created = self.create_readme()
        
        # Summary
        print("\n" + "=" * 60)
        print("[SUCCESS] Initialization Complete!")
        print("=" * 60)
        print(f"Directories created: {dirs_created}")
        print(f"JSON files created: {files_created}")
        print(f"README created: {'Yes' if readme_created else 'No'}")
        print("\nData layer is ready to use!")
        print("\nNext steps:")
        print("  1. Run tests: python test_phase1.py")
        print("  2. Check consistency: python consistency_validator.py")
        print("  3. Start using Skills!")
        
        return True


def main():
    """Main entry point"""
    # Parse arguments
    force = '--force' in sys.argv
    
    # Initialize
    initializer = DataLayerInitializer(force=force)
    success = initializer.initialize()
    
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
