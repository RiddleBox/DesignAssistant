# Digital Employee Management System

## What It Does

A lightweight system that manages digital employees (AI agents) through natural language conversations. Instead of using traditional software interfaces, you simply chat with AI to manage your workforce.

## How It Works

```
8 Markdown Files (SKILL prompts)
        ↓
    AI Model (GPT/Claude/Gemini)
        ↓
Auto-Generated Data Layer (JSON files)
```

1. **Copy** the 8 SKILL files to your AI chat
2. **Talk** naturally: *"Create a team for mobile game development"*
3. **AI executes** operations automatically
4. **Data saved** to local JSON files

## 8 Core Functions

1. **Team Builder** - Create and organize teams
2. **Employee Manager** - Add/remove/update employees
3. **Team Advisor** - Provide strategic guidance
4. **Knowledge Sharing** - Share and track information
5. **Work Logger** - Record daily activities
6. **Project Planner** - Design project structures
7. **Skill Matcher** - Match employees to tasks
8. **Project Summarizer** - Generate comprehensive reports

## Quick Example

**You:** *"I need a planning team to design a Halloween event for our extraction shooter game."*

**AI:**
- Recruits specialists (game designer, event planner, analyst)
- Forms a team with assigned roles
- Generates complete event proposal with mechanics, monetization, and metrics
- Saves everything automatically

**You:** *"Tell me more about the fog mechanic."*

**AI:** Continues refining the proposal based on your feedback.

## Technical Details

**Components:**
- 8 Markdown prompt files (~200KB)
- Any AI model (GPT-4, Claude, Gemini, etc.)
- Auto-generated storage layer

**Data Storage:**
- `employees.json` - Employee records
- `teams.json` - Team information
- `projects.json` - Project data
- `work_logs.json` - Activity logs
- `knowledge_base.json` - Shared knowledge

**First Run:**
- AI detects missing data layer
- Automatically creates folders and files
- Ready in ~3 seconds

## Getting Started

1. Clone this repository
2. Copy the 8 SKILL*.md files to your AI chat
3. Start chatting!

## Requirements

- Access to an AI model (GPT-4, Claude, Gemini, etc.)
- No database or server needed
- No installation required

## Use Cases

- **Rapid team formation** for new projects
- **Skills inventory** and gap analysis
- **Project planning** and resource allocation
- **Knowledge management** across teams
- **Activity tracking** and reporting

## Limitations

- Single-user system (no concurrent access)
- Basic JSON storage (not production-grade)
- Requires AI model access
- No authentication system

## License

MIT License - Feel free to use and modify

---

**Note:** This is a practice project exploring AI-native application architecture.
