"""
YOLO-based wall detection logic.
Loads the wall detection model and performs inference.
"""
import time
import numpy as np
from ultralytics import YOLO
from typing import List, Tuple
import os
import boto3
import tarfile


class WallDetector:
    """
    Wall detection using YOLO model.
    Detects wall segments in architectural blueprints.
    """
    
    def __init__(
        self,
        model_path: str = "/app/models/best_wall_model.pt",
        confidence_threshold: float = 0.10
    ):
        """
        Initialize wall detector.
        
        Args:
            model_path: Path to YOLO model weights
            confidence_threshold: Minimum confidence for detections
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load YOLO model from disk or download from S3"""
        # If model doesn't exist locally, download from S3 (like POC)
        if not os.path.exists(self.model_path):
            print(f"Custom model not found at {self.model_path}")
            print("Downloading trained model from S3...")

            try:
                self._download_model_from_s3()
            except Exception as e:
                print(f"Failed to download model from S3: {e}")
                print("ERROR: Cannot proceed without trained model")
                raise FileNotFoundError(f"Model not found at {self.model_path} and S3 download failed: {e}")

        print(f"Loading wall detection model from {self.model_path}")
        self.model = YOLO(self.model_path)
        print("Model loaded successfully")

    def _download_model_from_s3(self):
        """Download trained WALL detection model from S3 (SageMaker training output)"""
        s3_bucket = os.environ.get('MODEL_S3_BUCKET', 'sagemaker-us-east-1-971422717446')
        s3_key = os.environ.get('MODEL_S3_KEY', 'room-detection-yolo-1762559721/output/model.tar.gz')

        print(f"  S3 Bucket: {s3_bucket}")
        print(f"  S3 Key: {s3_key}")

        s3_client = boto3.client('s3')
        tar_path = "/tmp/model.tar.gz"
        model_path = "/tmp/final_model.pt"

        # Download tar.gz from S3
        print(f"  Downloading from s3://{s3_bucket}/{s3_key}")
        s3_client.download_file(s3_bucket, s3_key, tar_path)
        print(f"  ✓ Downloaded to {tar_path}")

        # Extract final_model.pt from tar.gz
        print(f"  Extracting model...")
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall('/tmp/')

        # Model should be at /tmp/final_model.pt after extraction
        if os.path.exists(model_path):
            print(f"  ✓ Model extracted to {model_path}")
            self.model_path = model_path
        else:
            raise FileNotFoundError("final_model.pt not found in tar.gz archive")
    
    def detect(
        self,
        image: np.ndarray,
        confidence_threshold: float = None
    ) -> Tuple[List[dict], float]:
        """
        Detect walls in image.
        
        Args:
            image: OpenCV image (BGR format)
            confidence_threshold: Override default confidence threshold
            
        Returns:
            Tuple of (wall_list, inference_time_ms)
            Each wall is a dict with: id, bounding_box, confidence
        """
        start_time = time.time()
        
        # Use instance threshold if not overridden
        threshold = confidence_threshold or self.confidence_threshold
        
        # Run inference
        results = self.model(
            image,
            conf=threshold,
            verbose=False
        )
        
        # Extract detections
        walls = []
        for i, detection in enumerate(results[0].boxes):
            # Get bounding box coordinates
            x1, y1, x2, y2 = detection.xyxy[0].tolist()
            confidence = float(detection.conf[0])
            
            walls.append({
                "id": f"wall_{i+1:03d}",
                "bounding_box": [int(x1), int(y1), int(x2), int(y2)],
                "confidence": confidence
            })
        
        inference_time = (time.time() - start_time) * 1000
        
        return walls, inference_time
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        return {
            "model_path": self.model_path,
            "confidence_threshold": self.confidence_threshold,
            "model_loaded": self.model is not None
        }

