/**
 * API client for room detection service.
 * Supports both v1 (wall model) and v2 (room model).
 */
import type {
  ModelVersion,
  DetectionOptions,
  DetectionResponse,
  WallDetectionResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Detect rooms in blueprint image using v1 model (wall detection → geometric conversion).
 * For v1, this function handles the 2-step pipeline internally.
 */
export async function detectRooms(
  imageBase64: string,
  options: DetectionOptions = {}
): Promise<DetectionResponse> {
  const {
    version = 'v1',
    confidence_threshold = 0.10,
    min_room_area = 2000,
    return_visualization = true,
  } = options;

  if (version === 'v1') {
    // V1 pipeline: wall detection → geometric conversion
    // Step 1: Detect walls
    const wallResponse = await detectWallsV1(imageBase64, confidence_threshold);
    
    if (!wallResponse.success || wallResponse.walls.length === 0) {
      return {
        success: true,
        rooms: [],
        total_rooms: 0,
        processing_time_ms: wallResponse.processing_time_ms,
        model_version: 'v1',
        visualization: wallResponse.visualization,
        metadata: {
          ...wallResponse.metadata,
          intermediate_detections: 0,
        },
      };
    }

    // Step 2: Convert walls to rooms
    const [width, height] = wallResponse.metadata?.image_dimensions || [0, 0];
    
    const conversionResponse = await convertWallsToRoomsV1(
      wallResponse.walls,
      [width, height],
      {
        min_room_area,
        return_visualization,
      }
    );

    return {
      ...conversionResponse,
      processing_time_ms: wallResponse.processing_time_ms + conversionResponse.processing_time_ms,
      metadata: {
        ...conversionResponse.metadata,
        wall_detection_time_ms: wallResponse.processing_time_ms,
        geometric_conversion_time_ms: conversionResponse.processing_time_ms,
      },
    };
  } else {
    // V2: Direct room detection
    return await detectRoomsV2(imageBase64, {
      confidence_threshold,
      return_visualization,
    });
  }
}

/**
 * Detect walls in blueprint image (v1 model).
 * This is for debugging/testing only - normal users should use detectRooms().
 */
export async function detectWallsV1(
  imageBase64: string,
  confidence_threshold: number = 0.10
): Promise<WallDetectionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/detect-walls`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      image: imageBase64,
      confidence_threshold,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: 'Wall detection failed' } }));
    throw new Error(error.error?.message || 'Wall detection failed');
  }

  return response.json();
}

/**
 * Convert wall detections to room polygons (v1 model).
 * This is for debugging/testing only - normal users should use detectRooms().
 */
export async function convertWallsToRoomsV1(
  walls: any[],
  imageDimensions: [number, number],
  options: {
    min_room_area?: number;
    return_visualization?: boolean;
  } = {}
): Promise<DetectionResponse> {
  const { min_room_area = 2000, return_visualization = true } = options;

  const response = await fetch(`${API_BASE_URL}/api/convert-to-rooms`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      walls,
      image_dimensions: imageDimensions,
      min_room_area,
      return_visualization,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: 'Geometric conversion failed' } }));
    throw new Error(error.error?.message || 'Geometric conversion failed');
  }

  return response.json();
}

/**
 * Detect rooms directly using v2 model (room detection).
 * Calls the room detection Lambda directly.
 */
export async function detectRoomsV2(
  imageBase64: string,
  options: {
    confidence_threshold?: number;
    return_visualization?: boolean;
  } = {}
): Promise<DetectionResponse> {
  const { confidence_threshold = 0.5, return_visualization = true } = options;

  const response = await fetch(`${API_BASE_URL}/api/v2/detect-rooms`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      image: imageBase64,
      confidence_threshold,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: { message: 'Room detection failed' } }));
    throw new Error(error.error?.message || 'Room detection failed');
  }

  // Parse Lambda response (may be wrapped in body if from API Gateway)
  const data = await response.json();
  
  // Handle API Gateway response format (statusCode, body)
  let v2Response: any;
  if (data.statusCode && data.body) {
    v2Response = typeof data.body === 'string' ? JSON.parse(data.body) : data.body;
  } else {
    v2Response = data;
  }

  // Transform v2 response format to frontend format
  return transformV2Response(v2Response);
}

/**
 * Transform v2 Lambda response to frontend DetectionResponse format
 */
function transformV2Response(v2Response: any): DetectionResponse {
  if (!v2Response.success) {
    throw new Error(v2Response.error || 'Room detection failed');
  }

  const detectedRooms = v2Response.detected_rooms || [];
  const imageDimensions = v2Response.image_dimensions || [0, 0];
  const [width, height] = imageDimensions;

  // Transform rooms to frontend format
  const rooms = detectedRooms.map((room: any) => {
    // v2 provides bounding_box_pixels as [x1, y1, x2, y2]
    const [x1, y1, x2, y2] = room.bounding_box_pixels || room.bounding_box || [0, 0, 0, 0];
    
    // Calculate area
    const area_pixels = (x2 - x1) * (y2 - y1);
    
    // Calculate centroid
    const centroid: [number, number] = [
      Math.round((x1 + x2) / 2),
      Math.round((y1 + y2) / 2)
    ];
    
    // Create polygon vertices from bounding box (rectangle)
    const polygon_vertices: [number, number][] = [
      [x1, y1],
      [x2, y1],
      [x2, y2],
      [x1, y2]
    ];

    return {
      id: room.id || `room_${Math.random().toString(36).substr(2, 9)}`,
      polygon_vertices,
      bounding_box: {
        x_min: x1,
        y_min: y1,
        x_max: x2,
        y_max: y2,
      },
      area_pixels,
      centroid,
      confidence: room.confidence || 0.5,
      shape_type: room.shape_type || 'rectangle',
      num_vertices: 4, // Rectangle has 4 vertices
    };
  });

  return {
    success: true,
    rooms,
    total_rooms: v2Response.total_rooms_detected || rooms.length,
    processing_time_ms: (v2Response.inference_time || 0) * 1000, // Convert seconds to milliseconds
    model_version: 'v2',
    visualization: undefined, // v2 doesn't provide visualization yet
    metadata: {
      model: v2Response.model || 'YOLOv8-Large',
      confidence_threshold: v2Response.confidence_threshold || 0.5,
      image_dimensions: imageDimensions,
    },
  };
}

