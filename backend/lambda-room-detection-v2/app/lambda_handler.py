"""
AWS Lambda Handler for YOLO Room Detection

This is the entry point for Lambda function invocations.
Handles API Gateway events and returns JSON responses.
"""

import json
import base64
import time
from app.yolo_inference import get_inference_handler


def handler(event, context):
    """
    Lambda handler function
    
    Event format (API Gateway):
    {
        "body": "{\"image\": \"base64-encoded-image\"}",
        "isBase64Encoded": false
    }
    
    Or direct invocation:
    {
        "image": "base64-encoded-image"
    }
    
    Returns:
        {
            "statusCode": 200,
            "headers": {...},
            "body": "{...detection results...}"
        }
    """
    
    print("Lambda invocation started")
    start_time = time.time()

    try:
        # Handle warmup events from EventBridge
        if isinstance(event, dict) and event.get('warmup'):
            print("Warmup event received - keeping Lambda warm")
            # Initialize inference handler to ensure model is loaded
            inference = get_inference_handler()
            print("Model loaded and ready")
            return create_response(200, {
                'success': True,
                'message': 'Lambda warmed up',
                'model_loaded': True
            })

        # Parse input
        if 'body' in event:
            # API Gateway format
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            # Direct invocation
            body = event

        # Extract image data
        if 'image' not in body:
            return create_response(400, {
                'success': False,
                'error': 'Missing "image" field in request body'
            })
        
        image_base64 = body['image']
        
        # Extract optional confidence threshold override
        confidence_threshold = body.get('confidence_threshold')
        if confidence_threshold is not None:
            try:
                confidence_threshold = float(confidence_threshold)
                if not (0.0 <= confidence_threshold <= 1.0):
                    return create_response(400, {
                        'success': False,
                        'error': 'confidence_threshold must be between 0.0 and 1.0'
                    })
            except (ValueError, TypeError):
                return create_response(400, {
                    'success': False,
                    'error': 'confidence_threshold must be a valid number'
                })
        
        # Decode base64 image
        try:
            image_data = base64.b64decode(image_base64)
        except Exception as e:
            return create_response(400, {
                'success': False,
                'error': f'Invalid base64 image data: {str(e)}'
            })
        
        print(f"Image size: {len(image_data)} bytes")
        if confidence_threshold is not None:
            print(f"Using confidence threshold override: {confidence_threshold}")
        
        # Get inference handler
        inference = get_inference_handler()
        
        # Run prediction with optional confidence threshold
        if confidence_threshold is not None:
            results = inference.predict(image_data, confidence_threshold=confidence_threshold)
        else:
            results = inference.predict(image_data)
        
        # Add timing info
        inference_time = time.time() - start_time
        results['inference_time'] = round(inference_time, 2)
        
        print(f"Inference completed in {inference_time:.2f}s")
        print(f"Rooms detected: {results.get('total_rooms_detected', 0)}")
        
        # Return results
        if results.get('success'):
            return create_response(200, results)
        else:
            return create_response(500, results)
    
    except Exception as e:
        print(f"Error in Lambda handler: {e}")
        import traceback
        traceback.print_exc()
        
        return create_response(500, {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        })


def create_response(status_code: int, body: dict) -> dict:
    """
    Create Lambda response for API Gateway
    
    Args:
        status_code: HTTP status code
        body: Response body dictionary
        
    Returns:
        Lambda response object
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # CORS
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        },
        'body': json.dumps(body)
    }
