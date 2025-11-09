# Room Boundary Detection System

Automated room boundary detection from architectural blueprints using YOLO-based wall detection and geometric algorithms.

## What is This?

A serverless room detection system that:
- ✅ Analyzes architectural blueprint images using YOLO models
- ✅ Detects walls and converts them to room polygons
- ✅ Provides REST API endpoints for detection
- ✅ React web interface for uploading blueprints
- ✅ AWS Lambda deployment (serverless architecture)

## Quick Start

### Project Structure

```
room-reader/
├── backend/
│   ├── shared/                          # Shared models and utilities
│   ├── lambda-wall-detection-v1/       # Wall detection Lambda (v1)
│   ├── lambda-geometric-conversion-v1/  # Wall-to-room conversion (v1)
│   ├── lambda-room-detection-v2/       # Direct room detection (v2 - Phase 2)
│   └── lambda-room-refinement-v2/      # Room refinement (v2 - Phase 2)
├── frontend/                            # React web interface
├── infrastructure/                      # Terraform and deployment configs
└── memory-bank/                         # Project context and documentation
```

### Development Workflow

1. **Start Development Session**: Use `/begin-development` command in Cursor
2. **Start Task**: Use `/start-task [id]` to get implementation plan
3. **Implement**: Use `/implement` to execute approved plan
4. **Update Memory Bank**: After completing tasks, update context files

### Starting Development Session

**Use the `/begin-development` command in Cursor** to automatically:
```
1. Read memory-bank/activeContext.md
2. Read memory-bank/progress.md
3. Confirm current phase and next tasks
4. Display recent changes and active decisions
```

Or manually prompt AI assistant:
```
Read @memory-bank/activeContext.md and @memory-bank/progress.md.
Confirm current phase and next task.
```

### After Development Session

```bash
# Update documentation
./scripts/update-docs.sh

# Verify context health
./scripts/verify-context.sh
```

## Directory Structure

```
backend/                ← Lambda functions (Python/FastAPI)
  ├── shared/           ← Shared models and utilities
  ├── lambda-wall-detection-v1/      ← Wall detection (YOLO)
  ├── lambda-geometric-conversion-v1/ ← Wall-to-room conversion
  ├── lambda-room-detection-v2/      ← Direct room detection (Phase 2)
  └── lambda-room-refinement-v2/     ← Room refinement (Phase 2)
frontend/               ← React web interface
infrastructure/         ← Terraform and AWS configs
memory-bank/            ← Project context and documentation
_docs/                  ← Architecture and task documentation
```

## Key Files

### Always Read (Every Session)
- `memory-bank/activeContext.md` - Current focus
- `memory-bank/progress.md` - Status and next steps

### Memory Bank Management
- **`.cursor/rules/memory-bank-management.mdc`** - Complete Memory Bank procedures
- **`memory-bank/README.md`** - Structure overview and quick reference
- **`memory-bank/activeContext.md`** - Current work focus (read every session)
- **`memory-bank/progress.md`** - Task status (read every session)

**Critical**: Memory Bank is the MOST IMPORTANT component. AI reads this every session to understand project context. Without current Memory Bank files, AI effectiveness drops dramatically.

### Reference When Needed
- `_docs/architecture-v2.md` - System design (revised architecture)
- `_docs/guides/multi-agent-workflow.md` - Multi-agent workflows
- `_docs/guides/test-first-workflow.md` - Test-first development

## Cursor Slash Commands

Available commands (use with `/` in Cursor):
- `/begin-development` - Start session: read Memory Bank, confirm current state (use this FIRST every session)
- `/start-task [id]` - Read context, produce implementation plan
- `/implement [id]` - Execute approved plan with test-first workflow
- `/fix-tests` - Self-correcting loop to fix failing tests
- `/update-memory-bank` - Review and update all memory bank files
- `/summarize` - Create context summary for session

## Best Practices

### For Developers
1. **Start every session with `/begin-development`** to load context automatically
2. Update memory bank after completing features
3. Run verify-context.sh weekly
4. Keep documentation in sync with code

### For AI Assistants
1. Read Memory Bank FIRST every session (see `.cursor/rules/memory-bank-management.mdc` for procedures)
2. Ask clarifying questions when uncertain
3. Check in after completing tasks
4. Never auto-commit without approval
5. Suggest context summary after complex work

## Maintenance

### Daily
- Update activeContext.md with work focus
- Update progress.md after completing tasks

### Weekly
- Run `./scripts/verify-context.sh`
- Review and update memory bank
- Archive old context if needed

### Monthly
- Review .cursor/rules/ for improvements
- Update test patterns
- Refine automation scripts

## Features

### Room Detection
- **Wall Detection (v1)**: YOLO-based wall detection from blueprints
- **Geometric Conversion (v1)**: Converts wall detections to room polygons
- **Direct Room Detection (v2)**: YOLO-based room detection (Phase 2)
- **Visualization**: Generates annotated images with room boundaries
- **REST API**: FastAPI endpoints for detection services
- **Web Interface**: React app for uploading blueprints and viewing results

### Architecture
- **Serverless**: AWS Lambda functions (container images)
- **Independent Deployment**: v1 and v2 models can be deployed separately
- **Modular Design**: Shared components for consistency
- **Test-First Development**: Comprehensive test coverage

## Support

For questions or improvements, see:
- [Multi-Agent Workflow Guide](_docs/guides/multi-agent-workflow.md)
- [Test-First Workflow Guide](_docs/guides/test-first-workflow.md)
- [Memory Bank README](memory-bank/README.md)

## Project Status

**Current Phase**: Phase 1 - Local Development (40% complete)
**Target MVP**: 2025-11-20

### Completed
- ✅ Project structure setup
- ✅ Room detection Lambda implementation
- ✅ Local testing infrastructure

### In Progress
- ⏳ Project structure reorganization (Task 1.1)
- ⏳ Shared components creation (Task 1.2)

### Next Steps
- Wall detection Lambda v1
- Geometric conversion Lambda v1
- Docker containerization
- AWS infrastructure setup

---

**Version**: 1.0
**Last Updated**: 2025-11-09
**Project**: Room Boundary Detection System
