# Project Brief: Room Boundary Detection System

**Version**: 1.0
**Last Updated**: 2025-11-09

## Project Overview

### What We're Building
An automated room boundary detection system that analyzes architectural blueprints using YOLO-based wall detection and geometric algorithms to identify and visualize room boundaries. The system provides a web interface for uploading blueprints and downloading detected room polygons with visualization.

### Core Problem
Manual room boundary extraction from architectural blueprints is time-consuming and error-prone. Architects, property managers, and real estate professionals need an automated way to quickly identify room layouts from blueprint images.

### Target Users
- Architects and architectural firms
- Property management companies
- Real estate professionals
- Construction planning teams
- Building inspectors and assessors

### Success Criteria
- Process blueprint images in <5 seconds end-to-end
- Detect 90%+ of clearly defined rooms accurately
- Provide downloadable room polygon coordinates and visualization
- Handle standard blueprint formats (PNG, JPG)
- Cost-effective serverless architecture (<$2/month for 10k requests)

---

## MVP Scope

### Must Have
- [x] YOLO-based wall detection from blueprint images
- [x] Geometric algorithm for wall-to-room boundary conversion
- [x] REST API endpoints (detect-walls, detect-rooms)
- [x] React web interface with drag-and-drop upload
- [x] Visualization generation with room boundaries
- [x] JSON export of room polygons and coordinates
- [x] AWS Lambda deployment (serverless)
- [x] API Gateway for REST API exposure

### Explicitly Out of Scope
- User authentication and accounts
- Blueprint storage and history
- Batch processing multiple blueprints
- 3D model generation
- Room type classification (bedroom, kitchen, etc.)
- Real-time collaborative editing
- Mobile native applications
- Custom ML model training interface

---

## Technical Constraints

### Performance Targets
- Wall detection: <2 seconds per blueprint
- Room conversion: <1 second per blueprint
- Total end-to-end: <5 seconds
- Cold start time: <5 seconds for Lambda
- Warm execution: <100ms per request

### Platform Requirements
- AWS Lambda (container images)
- Python 3.11 runtime
- React 18+ for frontend
- Modern browsers (Chrome, Firefox, Safari, Edge)
- HTTPS-only access

### Dependencies
- YOLO model (YOLOv8l) for wall detection
- OpenCV for image processing
- FastAPI for API framework
- AWS services: Lambda, ECR, API Gateway, S3, CloudFront

---

## Project Timeline

- **MVP Target**: 2025-11-20 (11 days from start)
- **Key Milestones**:
  - Phase 1 (Local Development): 2025-11-11
  - Phase 2 (Dockerization): 2025-11-12
  - Phase 3 (AWS Infrastructure): 2025-11-13
  - Phase 4 (Frontend Development): 2025-11-16
  - Phase 5 (Deployment): 2025-11-17
  - Phase 6 (CI/CD): 2025-11-18
  - Phase 7 (Testing & Launch): 2025-11-20
