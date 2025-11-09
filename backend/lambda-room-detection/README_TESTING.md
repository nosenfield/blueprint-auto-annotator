# Testing Guide - Room Detection Lambda

This guide explains how to test the room detection Lambda function locally.

## Prerequisites

### Install Dependencies

```bash
cd backend/lambda-room-detection
pip install -r requirements.txt
```

**Required packages:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `opencv-python-headless` - Image processing
- `numpy` - Numerical operations
- `pydantic` - Data validation
- `pillow` - Image manipulation
- `pytest` - Testing framework
- `requests` - HTTP client for testing

**Note:** If you encounter issues installing `opencv-python-headless` on macOS, you may need to use Docker or a virtual environment. The tests will run in Docker/CI environments where all dependencies are available.

## Running Tests

### 1. Unit Tests

Run unit tests for individual components:

```bash
# Run all unit tests
pytest tests/ -v

# Run specific test file
pytest tests/test_models.py -v
pytest tests/test_geometric.py -v
pytest tests/test_visualization.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

**Expected Results:**
- `test_models.py`: 9 tests, all passing ✅
- `test_geometric.py`: Requires opencv (will run in Docker)
- `test_visualization.py`: Requires opencv (will run in Docker)

### 2. Integration Tests

Run integration tests for the full pipeline:

```bash
# Run integration tests
pytest tests/test_integration.py -v
```

**Test Scenarios:**
- Simple 2-room layout
- Complex multi-room layout
- Single wall edge case
- No walls error case
- Invalid wall coordinates
- Response format validation
- Visualization generation
- Performance target (<1s)

### 3. Local API Testing

#### Start FastAPI Server

```bash
# In terminal 1: Start the server
cd backend/lambda-room-detection
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

#### Run Test Script

```bash
# In terminal 2: Run tests
cd backend/lambda-room-detection

# Run default test (realistic_blueprint.json)
python test_local.py

# Run specific test data file
python test_local.py --test-data simple_2_room.json

# Run all test scenarios
python test_local.py --all

# Run with health check first
python test_local.py --health-check

# Use custom API URL
python test_local.py --api-url http://localhost:8000
```

## Test Data Files

Test data files are located in `test_data/` directory:

### `simple_2_room.json`
- **Description:** Simple 2-room layout with 4 walls
- **Walls:** 2 walls forming 2 rooms
- **Expected rooms:** 2
- **Use case:** Basic functionality testing

### `complex_multi_room.json`
- **Description:** Complex multi-room layout
- **Walls:** 4 walls forming 9 rooms
- **Expected rooms:** 9
- **Use case:** Complex scenario testing

### `realistic_blueprint.json`
- **Description:** Realistic blueprint layout based on POC data
- **Walls:** 6 walls forming 2 rooms
- **Image dimensions:** 609x515 (realistic size)
- **Expected rooms:** 2
- **Use case:** Production-like testing

## Expected Results

### Successful Response

```json
{
  "success": true,
  "rooms": [
    {
      "id": "room_001",
      "polygon_vertices": [[x1, y1], [x2, y2], ...],
      "bounding_box": {"x_min": 10, "y_min": 10, "x_max": 50, "y_max": 50},
      "area_pixels": 1600,
      "centroid": [30, 30],
      "confidence": 0.85,
      "shape_type": "rectangle",
      "num_vertices": 4
    }
  ],
  "visualization": "base64_encoded_image",
  "total_rooms": 2,
  "processing_time_ms": 45.2,
  "metadata": {
    "image_dimensions": [100, 100],
    "walls_processed": 2,
    "min_room_area": 100
  }
}
```

### Performance Targets

- **Processing time:** <1 second for typical blueprints
- **Room detection:** Should detect all clearly defined rooms
- **Visualization:** Should generate valid PNG image
- **Response format:** Should match Pydantic model structure

## Troubleshooting

### Issue: "Could not connect to http://localhost:8000"

**Solution:** Make sure FastAPI server is running:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Issue: "ModuleNotFoundError: No module named 'cv2'"

**Solution:** Install opencv-python-headless:
```bash
pip install opencv-python-headless
```

Or use Docker (recommended for consistent environment).

### Issue: "ImportError: No module named 'app'"

**Solution:** Make sure you're in the correct directory:
```bash
cd backend/lambda-room-detection
```

### Issue: Tests fail with geometric/visualization tests

**Solution:** These tests require opencv-python-headless. They will run in Docker/CI environments. Model tests should pass locally.

### Issue: "Request timed out"

**Solution:** 
- Check if server is running
- Increase timeout in test script
- Check for infinite loops in algorithm

### Issue: No rooms detected

**Possible causes:**
- Walls don't form closed rooms
- `min_room_area` too high
- Wall coordinates incorrect
- Algorithm needs tuning

**Solution:**
- Check wall coordinates
- Lower `min_room_area` parameter
- Verify wall data format
- Review algorithm parameters

## Manual Testing

### Test Health Check Endpoint

```bash
curl http://localhost:8000/
```

**Expected response:**
```json
{
  "service": "room-boundary-detection",
  "status": "healthy",
  "version": "1.0.0"
}
```

### Test Room Detection Endpoint

```bash
curl -X POST http://localhost:8000/api/detect-rooms \
  -H "Content-Type: application/json" \
  -d @test_data/realistic_blueprint.json
```

### Test with Custom Data

Create your own test data file:

```json
{
  "walls": [
    {"id": "wall_001", "bounding_box": [10, 10, 20, 90], "confidence": 0.85}
  ],
  "image_dimensions": [100, 100],
  "min_room_area": 100,
  "return_visualization": true
}
```

Then test:
```bash
python test_local.py --test-data your_test.json
```

## Next Steps

After successful local testing:

1. **Docker Testing:** Test in Docker container (Task 2.1)
2. **Lambda Testing:** Test with Lambda runtime interface emulator
3. **Integration Testing:** Test with wall detection Lambda
4. **Performance Testing:** Test with larger blueprints
5. **Error Testing:** Test error handling and edge cases

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [Architecture Documentation](../../_docs/architecture-v2.md)
- [Task List](../../_docs/task-list-v2.md)

