/**
 * Type definitions for Room Detection API
 */

export type ModelVersion = 'v1' | 'v2';

export interface DetectionOptions {
  version?: ModelVersion;
  confidence_threshold?: number;
  min_room_area?: number;
  return_visualization?: boolean;
  enable_refinement?: boolean;
}

export interface Room {
  id: string;
  polygon_vertices: [number, number][];
  bounding_box: {
    x_min: number;
    y_min: number;
    x_max: number;
    y_max: number;
  };
  area_pixels: number;
  centroid: [number, number];
  confidence: number;
  shape_type: 'rectangle' | 'l_shape' | 'complex';
  num_vertices: number;
}

export interface DetectionResponse {
  success: boolean;
  rooms: Room[];
  total_rooms: number;
  processing_time_ms: number;
  model_version: ModelVersion;
  visualization?: string;
  metadata: Record<string, any>;
}

export interface Wall {
  id: string;
  bounding_box: [number, number, number, number];
  confidence: number;
}

export interface WallDetectionResponse {
  success: boolean;
  walls: Wall[];
  total_walls: number;
  image_dimensions: [number, number];
  processing_time_ms: number;
  model_version?: ModelVersion;
  visualization?: string;
  metadata?: Record<string, any>;
}

