"""
Local testing script for room detection
"""
import json
import requests
from pathlib import Path


def test_room_detection():
    """Test room detection endpoint locally"""
    
    # Sample wall data (from your existing detection)
    test_data = {
        "walls": [
            {"id": "wall_001", "bounding_box": [142, 353, 153, 513], "confidence": 0.80},
            {"id": "wall_002", "bounding_box": [282, 351, 294, 513], "confidence": 0.79},
            {"id": "wall_003", "bounding_box": [142, 353, 294, 363], "confidence": 0.75},
            {"id": "wall_004", "bounding_box": [142, 503, 294, 513], "confidence": 0.75},
        ],
        "image_dimensions": [609, 515],
        "min_room_area": 2000,
        "return_visualization": True
    }
    
    # Call local FastAPI server
    response = requests.post(
        "http://localhost:8000/api/detect-rooms",
        json=test_data
    )
    
    # Check response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    result = response.json()
    
    print(f"Success: {result['success']}")
    print(f"Rooms detected: {result['total_rooms']}")
    print(f"Processing time: {result['processing_time_ms']}ms")
    
    # Save visualization
    if result.get('visualization'):
        import base64
        viz_data = base64.b64decode(result['visualization'])
        
        output_path = Path("test_visualization.png")
        output_path.write_bytes(viz_data)
        print(f"Visualization saved to: {output_path}")
    
    # Save JSON
    output_json = Path("test_results.json")
    output_json.write_text(json.dumps(result, indent=2))
    print(f"Results saved to: {output_json}")
    
    return result


if __name__ == "__main__":
    # Run FastAPI first: uvicorn app.main:app --reload
    test_room_detection()

