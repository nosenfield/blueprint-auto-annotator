#!/usr/bin/env python3
"""
Compare Lambda YOLO results with Ground Truth and Claude Vision results
"""

import json
import sys
from pathlib import Path

def load_json(filepath):
    """Load JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)

def calculate_iou(box1, box2):
    """Calculate Intersection over Union (IoU) for two bounding boxes"""
    # Box format: [x1, y1, x2, y2]
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

def calculate_bbox_error(box1, box2):
    """Calculate average pixel error between two bounding boxes"""
    errors = [abs(box1[i] - box2[i]) for i in range(4)]
    return sum(errors) / 4

def match_detections(ground_truth, detected, iou_threshold=0.3):
    """Match detected rooms with ground truth using IoU"""
    matches = []
    unmatched_gt = list(range(len(ground_truth)))
    unmatched_det = list(range(len(detected)))
    
    # Calculate IoU for all pairs
    iou_matrix = []
    for gt_idx, gt_room in enumerate(ground_truth):
        row = []
        for det_idx, det_room in enumerate(detected):
            iou = calculate_iou(gt_room['bbox_normalized'], det_room['bounding_box'])
            row.append(iou)
        iou_matrix.append(row)
    
    # Greedy matching
    while True:
        best_iou = 0
        best_match = None
        
        for gt_idx in unmatched_gt:
            for det_idx in unmatched_det:
                iou = iou_matrix[gt_idx][det_idx]
                if iou > best_iou and iou >= iou_threshold:
                    best_iou = iou
                    best_match = (gt_idx, det_idx)
        
        if best_match is None:
            break
        
        gt_idx, det_idx = best_match
        matches.append({
            'gt_idx': gt_idx,
            'det_idx': det_idx,
            'iou': best_iou,
            'error': calculate_bbox_error(
                ground_truth[gt_idx]['bbox_normalized'],
                detected[det_idx]['bounding_box']
            )
        })
        unmatched_gt.remove(gt_idx)
        unmatched_det.remove(det_idx)
    
    return matches, unmatched_gt, unmatched_det

def main():
    # Load results
    poc_dir = Path('../poc')
    poc3_dir = Path('.')
    
    # Find latest Lambda results
    lambda_results_files = sorted(poc3_dir.glob('lambda_test_results_*.json'))
    if not lambda_results_files:
        print("Error: No Lambda test results found")
        sys.exit(1)
    
    lambda_results_file = lambda_results_files[-1]
    print(f"Using Lambda results: {lambda_results_file.name}")
    
    # Load all results
    try:
        lambda_data = load_json(lambda_results_file)
        ground_truth = load_json(poc_dir / 'generated_blueprint_ground_truth.json')
        claude_data = load_json(poc_dir / 'poc_test_results.json')
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Parse Lambda results
    if 'body' in lambda_data:
        lambda_body = json.loads(lambda_data['body'])
    else:
        lambda_body = lambda_data
    
    lambda_rooms = lambda_body.get('detected_rooms', [])
    claude_rooms = claude_data.get('detected_rooms', [])
    gt_rooms = ground_truth.get('rooms', [])
    
    print("\n" + "="*70)
    print("COMPARISON: Lambda YOLO vs Claude Vision vs Ground Truth")
    print("="*70)
    print()
    
    # Detection counts
    print("Detection Count:")
    print(f"  Ground Truth:  {len(gt_rooms)} rooms")
    print(f"  Lambda YOLO:   {len(lambda_rooms)} rooms")
    print(f"  Claude Vision: {len(claude_rooms)} rooms")
    print()
    
    # Match Lambda with Ground Truth
    lambda_matches, lambda_unmatched_gt, lambda_unmatched_det = match_detections(
        gt_rooms, lambda_rooms
    )
    
    # Match Claude with Ground Truth
    claude_matches, claude_unmatched_gt, claude_unmatched_det = match_detections(
        gt_rooms, claude_rooms
    )
    
    # Accuracy metrics
    print("Accuracy Metrics:")
    print()
    
    # Lambda accuracy
    if lambda_matches:
        lambda_avg_iou = sum(m['iou'] for m in lambda_matches) / len(lambda_matches)
        lambda_avg_error = sum(m['error'] for m in lambda_matches) / len(lambda_matches)
        lambda_detection_rate = len(lambda_matches) / len(gt_rooms) * 100
        
        print(f"Lambda YOLO:")
        print(f"  Detection Rate: {lambda_detection_rate:.1f}% ({len(lambda_matches)}/{len(gt_rooms)} matched)")
        print(f"  Average IoU:    {lambda_avg_iou:.3f}")
        print(f"  Average Error:  {lambda_avg_error:.1f} pixels")
        print(f"  False Positives: {len(lambda_unmatched_det)}")
        print(f"  False Negatives: {len(lambda_unmatched_gt)}")
    else:
        print("Lambda YOLO: No matches found")
    print()
    
    # Claude accuracy
    if claude_matches:
        claude_avg_iou = sum(m['iou'] for m in claude_matches) / len(claude_matches)
        claude_avg_error = sum(m['error'] for m in claude_matches) / len(claude_matches)
        claude_detection_rate = len(claude_matches) / len(gt_rooms) * 100
        
        print(f"Claude Vision:")
        print(f"  Detection Rate: {claude_detection_rate:.1f}% ({len(claude_matches)}/{len(gt_rooms)} matched)")
        print(f"  Average IoU:    {claude_avg_iou:.3f}")
        print(f"  Average Error:  {claude_avg_error:.1f} pixels")
        print(f"  False Positives: {len(claude_unmatched_det)}")
        print(f"  False Negatives: {len(claude_unmatched_gt)}")
    else:
        print("Claude Vision: No matches found")
    print()
    
    # Performance comparison
    print("Performance:")
    lambda_inference = lambda_body.get('inference_time', 'N/A')
    print(f"  Lambda (warm): ~3s total, {lambda_inference}s inference")
    print(f"  Claude:        ~5-10s")
    print()
    
    # Cost comparison
    print("Cost Per Image:")
    print(f"  Lambda (warm): ~$0.0002")
    print(f"  Claude:        $0.0086")
    print()
    
    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print()
    
    if lambda_matches and claude_matches:
        if lambda_avg_iou > claude_avg_iou:
            print("✅ Lambda YOLO has better coordinate accuracy (IoU)")
        elif claude_avg_iou > lambda_avg_iou:
            print("✅ Claude Vision has better coordinate accuracy (IoU)")
        else:
            print("⚠️  Similar coordinate accuracy")
        
        if lambda_avg_error < claude_avg_error:
            print("✅ Lambda YOLO has lower pixel error")
        elif claude_avg_error < lambda_avg_error:
            print("✅ Claude Vision has lower pixel error")
        
        if lambda_detection_rate > claude_detection_rate:
            print("✅ Lambda YOLO detected more ground truth rooms")
        elif claude_detection_rate > lambda_detection_rate:
            print("✅ Claude Vision detected more ground truth rooms")
    
    print()
    print("Recommendation:")
    if lambda_matches and lambda_avg_iou > 0.5:
        print("  ✅ Lambda YOLO is working well - proceed with Lambda-based architecture")
    elif claude_matches and claude_avg_iou > 0.5:
        print("  ⚠️  Consider hybrid approach or Claude Vision for better detection rate")
    else:
        print("  ⚠️  Both approaches need improvement - may need more training/testing")
    print()

if __name__ == '__main__':
    main()

