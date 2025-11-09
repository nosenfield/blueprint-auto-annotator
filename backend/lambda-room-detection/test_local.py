"""
Local testing script for room detection
Supports multiple test scenarios and command-line arguments
"""
import json
import requests
import sys
import argparse
from pathlib import Path
from typing import Dict, Any


def load_test_data(test_file: str) -> Dict[str, Any]:
    """Load test data from JSON file"""
    test_data_path = Path(__file__).parent / "test_data" / test_file
    if not test_data_path.exists():
        raise FileNotFoundError(f"Test data file not found: {test_data_path}")
    
    with open(test_data_path, 'r') as f:
        return json.load(f)


def test_room_detection(test_data: Dict[str, Any], api_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Test room detection endpoint locally"""
    
    print(f"\n{'='*60}")
    print(f"Testing Room Detection API")
    print(f"{'='*60}")
    print(f"API URL: {api_url}")
    print(f"Walls: {len(test_data['walls'])}")
    print(f"Image dimensions: {test_data['image_dimensions']}")
    print(f"Min room area: {test_data.get('min_room_area', 2000)}")
    print()
    
    try:
        # Call local FastAPI server
        response = requests.post(
            f"{api_url}/api/detect-rooms",
            json=test_data,
            timeout=30
        )
        
        # Check response
        if response.status_code != 200:
            print(f"❌ Error: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
        result = response.json()
        
        # Validate response structure
        assert result.get('success') == True, "Response success should be True"
        assert 'rooms' in result, "Response should contain 'rooms'"
        assert 'total_rooms' in result, "Response should contain 'total_rooms'"
        assert 'processing_time_ms' in result, "Response should contain 'processing_time_ms'"
        
        # Print results
        print(f"✅ Success: {result['success']}")
        print(f"📊 Rooms detected: {result['total_rooms']}")
        print(f"⏱️  Processing time: {result['processing_time_ms']:.2f}ms")
        
        # Check performance target
        if result['processing_time_ms'] < 1000:
            print(f"✅ Performance: Meets target (<1s)")
        else:
            print(f"⚠️  Performance: Exceeds target ({result['processing_time_ms']/1000:.2f}s)")
        
        # Print room details
        if result['rooms']:
            print(f"\n📋 Room Details:")
            for room in result['rooms'][:5]:  # Show first 5 rooms
                print(f"  - {room['id']}: {room['shape_type']}, "
                      f"area={room['area_pixels']}px², "
                      f"confidence={room['confidence']:.2f}")
            if len(result['rooms']) > 5:
                print(f"  ... and {len(result['rooms']) - 5} more rooms")
        
        # Save visualization
        if result.get('visualization'):
            import base64
            viz_data = base64.b64decode(result['visualization'])
            
            output_path = Path("test_visualization.png")
            output_path.write_bytes(viz_data)
            print(f"\n💾 Visualization saved to: {output_path}")
        
        # Save JSON
        output_json = Path("test_results.json")
        output_json.write_text(json.dumps(result, indent=2))
        print(f"💾 Results saved to: {output_json}")
        
        # Compare with expected results if available
        if 'expected_rooms' in test_data:
            expected = test_data['expected_rooms']
            actual = result['total_rooms']
            if actual == expected:
                print(f"✅ Expected {expected} rooms, detected {actual} rooms")
            else:
                print(f"⚠️  Expected {expected} rooms, detected {actual} rooms")
        
        return result
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Could not connect to {api_url}")
        print(f"   Make sure FastAPI server is running:")
        print(f"   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return None
    except requests.exceptions.Timeout:
        print(f"❌ Error: Request timed out")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_health_check(api_url: str = "http://localhost:8000") -> bool:
    """Test health check endpoint"""
    try:
        response = requests.get(f"{api_url}/", timeout=5)
        if response.status_code == 200:
            print(f"✅ Health check passed: {response.json()}")
            return True
        else:
            print(f"⚠️  Health check returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False


def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description="Test room detection API locally")
    parser.add_argument(
        "--test-data",
        type=str,
        default="realistic_blueprint.json",
        help="Test data file name (default: realistic_blueprint.json)"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="API URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Run health check first"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all test scenarios"
    )
    
    args = parser.parse_args()
    
    # Health check
    if args.health_check:
        print("\n🔍 Running health check...")
        if not test_health_check(args.api_url):
            print("\n❌ Health check failed. Exiting.")
            sys.exit(1)
    
    # Run all tests
    if args.all:
        test_files = [
            "simple_2_room.json",
            "complex_multi_room.json",
            "realistic_blueprint.json"
        ]
        
        results = []
        for test_file in test_files:
            try:
                test_data = load_test_data(test_file)
                print(f"\n{'='*60}")
                print(f"Running test: {test_file}")
                print(f"{'='*60}")
                result = test_room_detection(test_data, args.api_url)
                if result:
                    results.append((test_file, result))
            except FileNotFoundError:
                print(f"⚠️  Skipping {test_file}: File not found")
            except Exception as e:
                print(f"❌ Error running {test_file}: {str(e)}")
        
        # Summary
        print(f"\n{'='*60}")
        print(f"Test Summary")
        print(f"{'='*60}")
        print(f"Total tests: {len(test_files)}")
        print(f"Passed: {len(results)}")
        print(f"Failed: {len(test_files) - len(results)}")
        
        if results:
            avg_time = sum(r['processing_time_ms'] for _, r in results) / len(results)
            print(f"Average processing time: {avg_time:.2f}ms")
        
        sys.exit(0 if len(results) == len(test_files) else 1)
    
    # Run single test
    try:
        test_data = load_test_data(args.test_data)
        result = test_room_detection(test_data, args.api_url)
        sys.exit(0 if result else 1)
    except FileNotFoundError as e:
        print(f"❌ Error: {str(e)}")
        print(f"\nAvailable test data files:")
        test_data_dir = Path(__file__).parent / "test_data"
        if test_data_dir.exists():
            for f in test_data_dir.glob("*.json"):
                print(f"  - {f.name}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
