"""
YOLO Inference Module for AWS Lambda

Handles model loading and inference for blueprint room detection.
"""

import os
import io
import base64
import tarfile
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Any, Optional
from PIL import Image
import torch
from ultralytics import YOLO
import numpy as np


class YOLOInference:
    """YOLO model inference handler"""
    
    def __init__(self):
        """Initialize the inference handler"""
        self.model = None
        self.model_path = "/tmp/model.pt"
        self.s3_client = boto3.client('s3')
        
        # Model configuration from environment variables
        self.model_s3_bucket = os.environ.get(
            'MODEL_S3_BUCKET',
            'sagemaker-us-east-1-971422717446'
        )
        self.model_s3_key = os.environ.get(
            'MODEL_S3_KEY',
            'room-detection-yolo-1762559721/output/model.tar.gz'
        )
        
        # Inference parameters
        # Lower confidence threshold to catch more detections (walls vs rooms)
        self.confidence_threshold = float(os.environ.get('CONFIDENCE_THRESHOLD', '0.3'))
        # Lower IoU threshold to allow more detections (less aggressive NMS)
        self.iou_threshold = float(os.environ.get('IOU_THRESHOLD', '0.3'))
        self.image_size = int(os.environ.get('IMAGE_SIZE', '640'))
        
        print(f"YOLOInference initialized")
        print(f"  Model: s3://{self.model_s3_bucket}/{self.model_s3_key}")
        print(f"  Confidence: {self.confidence_threshold}")
        print(f"  IoU: {self.iou_threshold}")
        print(f"  Image size: {self.image_size}")
    
    def validate_s3_path(self):
        """Validate that the S3 model path exists and is accessible"""
        try:
            self.s3_client.head_object(
                Bucket=self.model_s3_bucket,
                Key=self.model_s3_key
            )
            print(f"  ✓ Model file verified in S3")
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404' or error_code == 'NoSuchKey':
                print(f"  ✗ Error: Model file not found in S3: s3://{self.model_s3_bucket}/{self.model_s3_key}")
                raise FileNotFoundError(
                    f"Model file not found in S3. Please verify MODEL_S3_BUCKET and MODEL_S3_KEY environment variables."
                )
            elif error_code == '403':
                print(f"  ✗ Error: Access denied to S3 bucket. Check IAM permissions.")
                raise PermissionError(
                    f"Access denied to S3 bucket {self.model_s3_bucket}. "
                    f"Ensure Lambda execution role has s3:GetObject permission."
                )
            else:
                print(f"  ✗ Error accessing S3: {error_code}")
                raise
        except NoCredentialsError:
            print(f"  ✗ Error: AWS credentials not configured")
            raise RuntimeError(
                "AWS credentials not configured. Ensure Lambda execution role has proper permissions."
            )
    
    def load_model(self):
        """Load YOLO model from S3 (called on cold start)"""
        if self.model is not None:
            print("Model already loaded (warm start)")
            return
        
        print("Loading model from S3 (cold start)...")
        
        try:
            # Validate S3 path exists before attempting download
            self.validate_s3_path()
            
            # Download model.tar.gz from S3 to /tmp
            tar_path = "/tmp/model.tar.gz"
            
            print(f"  Downloading from s3://{self.model_s3_bucket}/{self.model_s3_key}")
            self.s3_client.download_file(
                self.model_s3_bucket,
                self.model_s3_key,
                tar_path
            )
            print(f"  Downloaded to {tar_path}")
            
            # Extract tar.gz
            print("  Extracting model files...")
            with tarfile.open(tar_path, 'r:gz') as tar:
                tar.extractall('/tmp/model/')
            
            # Find the model file
            # Based on your model structure: try final_model.pt first, then best.pt
            possible_paths = [
                '/tmp/model/final_model.pt',
                '/tmp/model/room_detection/weights/best.pt',
                '/tmp/model/best.pt',
            ]
            
            model_file = None
            for path in possible_paths:
                if os.path.exists(path):
                    model_file = path
                    print(f"  Found model at: {path}")
                    break
            
            if model_file is None:
                # List all files to debug
                print("  Available files:")
                for root, dirs, files in os.walk('/tmp/model/'):
                    for file in files:
                        filepath = os.path.join(root, file)
                        print(f"    {filepath}")
                raise FileNotFoundError("Could not find model .pt file in extracted archive")
            
            # Load YOLO model
            print(f"  Loading YOLO model from {model_file}...")
            self.model = YOLO(model_file)
            print("  ✓ Model loaded successfully")
            
            # Set device
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"  Using device: {device}")
            
            # Clean up tar file to save space
            os.remove(tar_path)
            
        except Exception as e:
            print(f"  ✗ Error loading model: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def preprocess_image(self, image_data: bytes) -> Image.Image:
        """
        Preprocess image for inference
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            PIL Image object
        """
        img = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        return img
    
    def run_inference(self, image: Image.Image, confidence_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Run YOLO inference on image
        
        Args:
            image: PIL Image
            confidence_threshold: Optional confidence threshold override (0.0-1.0)
                                  If None, uses self.confidence_threshold from environment
            
        Returns:
            List of detected rooms with bounding boxes
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        # Get original image size
        original_width, original_height = image.size
        
        # Use provided threshold or fall back to instance default
        conf_threshold = confidence_threshold if confidence_threshold is not None else self.confidence_threshold
        
        # Run inference
        results = self.model(
            image,
            conf=conf_threshold,
            iou=self.iou_threshold,
            imgsz=self.image_size,
            verbose=False  # Suppress YOLO output
        )
        
        # Extract detections
        detections = []
        
        for result in results:
            boxes = result.boxes
            
            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    # Get box coordinates (xyxy format - pixel coordinates)
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    # Get confidence and class
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    
                    # Get class name
                    class_name = result.names[class_id] if hasattr(result, 'names') else f"class_{class_id}"
                    
                    # Calculate box dimensions
                    box_width = x2 - x1
                    box_height = y2 - y1
                    box_area = box_width * box_height
                    image_area = original_width * original_height
                    area_ratio = box_area / image_area
                    
                    # Filter out very small detections (likely noise or wall segments)
                    # Keep detections that are at least 0.5% of image area
                    if area_ratio < 0.005:
                        continue
                    
                    # Expand bounding boxes slightly to include room interiors
                    # If detection is very thin (likely a wall), expand it
                    aspect_ratio = box_width / box_height if box_height > 0 else 1.0
                    
                    # If very narrow (likely vertical wall), expand horizontally
                    if aspect_ratio < 0.1:
                        expand_x = min(box_width * 2, original_width * 0.1)  # Expand up to 10% of image width
                        x1 = max(0, x1 - expand_x / 2)
                        x2 = min(original_width, x2 + expand_x / 2)
                    # If very wide and short (likely horizontal wall), expand vertically
                    elif aspect_ratio > 10:
                        expand_y = min(box_height * 2, original_height * 0.1)  # Expand up to 10% of image height
                        y1 = max(0, y1 - expand_y / 2)
                        y2 = min(original_height, y2 + expand_y / 2)
                    # Otherwise, expand slightly in all directions (room interior)
                    else:
                        expand_x = box_width * 0.1  # 10% expansion
                        expand_y = box_height * 0.1
                        x1 = max(0, x1 - expand_x / 2)
                        x2 = min(original_width, x2 + expand_x / 2)
                        y1 = max(0, y1 - expand_y / 2)
                        y2 = min(original_height, y2 + expand_y / 2)
                    
                    # Normalize to 0-1000 range
                    norm_x1 = int((x1 / original_width) * 1000)
                    norm_y1 = int((y1 / original_height) * 1000)
                    norm_x2 = int((x2 / original_width) * 1000)
                    norm_y2 = int((y2 / original_height) * 1000)
                    
                    detections.append({
                        'bounding_box': [norm_x1, norm_y1, norm_x2, norm_y2],
                        'bounding_box_pixels': [int(x1), int(y1), int(x2), int(y2)],
                        'confidence': confidence,
                        'class_id': class_id,
                        'class_name': class_name,
                        'shape_type': 'rectangle'
                    })
        
        # Post-process: Merge nearby detections that likely represent the same room
        detections = self.merge_nearby_detections(detections, original_width, original_height)
        
        return detections
    
    def merge_nearby_detections(
        self,
        detections: List[Dict[str, Any]],
        image_width: int,
        image_height: int,
        merge_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Merge nearby detections that likely represent the same room
        
        Args:
            detections: List of detection dictionaries
            image_width: Original image width
            image_height: Original image height
            merge_threshold: IoU threshold for merging (default 0.3)
            
        Returns:
            Merged detection list
        """
        if len(detections) <= 1:
            return detections
        
        # Sort by confidence (highest first)
        sorted_detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        merged = []
        used = set()
        
        for i, det1 in enumerate(sorted_detections):
            if i in used:
                continue
            
            # Start with this detection
            merged_box = det1['bounding_box_pixels'].copy()
            merged_conf = det1['confidence']
            merged_class = det1['class_name']
            count = 1
            
            # Look for nearby detections to merge
            for j, det2 in enumerate(sorted_detections[i+1:], start=i+1):
                if j in used:
                    continue
                
                # Calculate IoU
                iou = self._calculate_iou_pixels(
                    det1['bounding_box_pixels'],
                    det2['bounding_box_pixels']
                )
                
                # If IoU is high enough, merge them
                if iou >= merge_threshold:
                    # Merge bounding boxes (union)
                    x1_1, y1_1, x2_1, y2_1 = merged_box
                    x1_2, y1_2, x2_2, y2_2 = det2['bounding_box_pixels']
                    
                    merged_box = [
                        min(x1_1, x1_2),
                        min(y1_1, y1_2),
                        max(x2_1, x2_2),
                        max(y2_1, y2_2)
                    ]
                    
                    # Average confidence
                    merged_conf = (merged_conf * count + det2['confidence']) / (count + 1)
                    count += 1
                    used.add(j)
            
            # Create merged detection
            x1, y1, x2, y2 = merged_box
            norm_x1 = int((x1 / image_width) * 1000)
            norm_y1 = int((y1 / image_height) * 1000)
            norm_x2 = int((x2 / image_width) * 1000)
            norm_y2 = int((y2 / image_height) * 1000)
            
            merged.append({
                'bounding_box': [norm_x1, norm_y1, norm_x2, norm_y2],
                'bounding_box_pixels': merged_box,
                'confidence': merged_conf,
                'class_id': det1['class_id'],
                'class_name': merged_class,
                'shape_type': 'rectangle'
            })
            used.add(i)
        
        return merged
    
    def _calculate_iou_pixels(self, box1: List[int], box2: List[int]) -> float:
        """Calculate IoU for two bounding boxes in pixel coordinates"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def postprocess_detections(
        self,
        detections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Format detections into final output structure
        
        Args:
            detections: Raw detection list
            
        Returns:
            Formatted detection results
        """
        # Add IDs and format
        formatted_rooms = []
        for i, detection in enumerate(detections, 1):
            formatted_rooms.append({
                'id': f"room_{i:03d}",
                'bounding_box': detection['bounding_box'],
                'bounding_box_pixels': detection['bounding_box_pixels'],
                'name_hint': detection['class_name'],
                'confidence': detection['confidence'],
                'shape_type': detection['shape_type']
            })
        
        return {
            'success': True,
            'detected_rooms': formatted_rooms,
            'total_rooms_detected': len(formatted_rooms),
            'model': 'YOLOv8-Large',
            'confidence_threshold': self.confidence_threshold
        }
    
    def predict(self, image_data: bytes, confidence_threshold: Optional[float] = None) -> Dict[str, Any]:
        """
        Main prediction pipeline
        
        Args:
            image_data: Raw image bytes
            confidence_threshold: Optional confidence threshold override (0.0-1.0)
                                  If None, uses self.confidence_threshold from environment
            
        Returns:
            Detection results
        """
        try:
            # Ensure model is loaded
            self.load_model()
            
            # Preprocess image
            image = self.preprocess_image(image_data)
            
            # Run inference with optional confidence threshold override
            detections = self.run_inference(image, confidence_threshold=confidence_threshold)
            
            # Format results
            results = self.postprocess_detections(detections)
            
            # Add image dimensions
            results['image_dimensions'] = list(image.size)
            
            # Include the actual confidence threshold used in results
            actual_threshold = confidence_threshold if confidence_threshold is not None else self.confidence_threshold
            results['confidence_threshold'] = actual_threshold
            
            return results
            
        except Exception as e:
            print(f"Error during prediction: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }


# Global instance (reused across warm Lambda invocations)
_inference_handler = None

def get_inference_handler() -> YOLOInference:
    """Get or create the global inference handler"""
    global _inference_handler
    if _inference_handler is None:
        _inference_handler = YOLOInference()
    return _inference_handler
