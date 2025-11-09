#!/usr/bin/env python3
"""
Visualize Lambda YOLO detection results on blueprint image
Draws bounding boxes for detected rooms
"""

import json
import sys
import os
from PIL import Image, ImageDraw
import argparse

def load_json(filepath):
    """Load JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)

def denormalize_bbox(bbox, width, height):
    """Convert normalized bbox (0-1000) to pixel coordinates"""
    x1, y1, x2, y2 = bbox
    return [
        int((x1 / 1000) * width),
        int((y1 / 1000) * height),
        int((x2 / 1000) * width),
        int((y2 / 1000) * height)
    ]

def visualize_detections(image_path, results_path, output_path=None):
    """Visualize detected rooms on blueprint image"""
    
    # Load image
    img = Image.open(image_path)
    img_width, img_height = img.size
    
    img = img.convert('RGBA')  # Add this line
    
    # Load results
    results_data = load_json(results_path)
    
    # Parse Lambda response format
    if 'body' in results_data:
        body = json.loads(results_data['body'])
    else:
        body = results_data
    
    detected_rooms = body.get('detected_rooms', [])
    
    if not detected_rooms:
        print("No rooms detected in results")
        return
    
    # Extract confidence threshold for filename
    confidence_threshold = body.get('confidence_threshold', 0.5)
    # Format threshold to 2 decimal places (e.g., 0.05, 0.10, 0.15)
    threshold_str = f"{confidence_threshold:.2f}"
    
    # Create drawing context
    draw = ImageDraw.Draw(img)
    
    print(f"Visualizing {len(detected_rooms)} detected rooms on {img_width}x{img_height} image...")
    print(f"  Confidence threshold: {threshold_str}")
    
    # Draw each detection
    for i, room in enumerate(detected_rooms, 1):
        # Get bounding box (use normalized if available, otherwise pixels)
        if 'bounding_box' in room:
            bbox = room['bounding_box']
            # Check if normalized (0-1000 range) or pixels
            if max(bbox) <= 1000:
                x1, y1, x2, y2 = denormalize_bbox(bbox, img_width, img_height)
            else:
                x1, y1, x2, y2 = bbox
        elif 'bounding_box_pixels' in room:
            x1, y1, x2, y2 = room['bounding_box_pixels']
        else:
            continue
        
        # Use high contrast orange for all bounding boxes
        color = (255, 140, 0)  # High contrast orange (RGB)
        
        # Draw filled bounding box (no labels)
        draw.rectangle([x1, y1, x2, y2], fill=color)
    
    # Save output
    if output_path is None:
        # Extract base name and extension
        base_name = os.path.splitext(image_path)[0]
        ext = os.path.splitext(image_path)[1] or '.png'
        
        # Create filename with threshold: blueprint_processed_0.05.png
        output_path = f"{base_name}_processed_{threshold_str}{ext}"
    
    img.save(output_path)
    print(f"✓ Visualization saved to: {output_path}")
    print(f"  Detected {len(detected_rooms)} rooms")
    
    return output_path

def main():
    parser = argparse.ArgumentParser(description='Visualize Lambda YOLO detection results')
    parser.add_argument('--image', '-i', required=True, help='Path to blueprint image')
    parser.add_argument('--results', '-r', required=True, help='Path to Lambda results JSON file')
    parser.add_argument('--output', '-o', help='Output image path')
    
    args = parser.parse_args()
    
    # Visualize
    output_path = visualize_detections(args.image, args.results, args.output)

if __name__ == '__main__':
    main()

