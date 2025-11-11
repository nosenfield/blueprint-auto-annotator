import React, { useState, useRef } from 'react';
import type { DetectionResponse, ModelVersion } from '../types';
import { detectRooms } from '../services/api';
import { RoomVisualization, type RoomVisualizationRef } from './RoomVisualization';
import { V1RoomVisualization, type V1RoomVisualizationRef } from './V1RoomVisualization';

export function Upload() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<DetectionResponse | null>(null);
  const [modelVersion, setModelVersion] = useState<ModelVersion>('v1');
  // Default confidence thresholds: v1 uses 0.10, v2 uses 0.5
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.10);
  const v1VisualizationRef = useRef<V1RoomVisualizationRef>(null);
  const v2VisualizationRef = useRef<RoomVisualizationRef>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file');
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      alert('Image size must be less than 10MB');
      return;
    }

    setSelectedFile(file);
    setResults(null);

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleUpload = async () => {
    if (!selectedFile || !imagePreview) {
      alert('Please select an image');
      return;
    }

    setLoading(true);
    setResults(null);

    try {
      // Extract base64 from data URL
      const base64 = imagePreview.split(',')[1];

      // Call API
      const response = await detectRooms(base64, {
        version: modelVersion,
        return_visualization: true,
        confidence_threshold: confidenceThreshold,
      });

      setResults(response);
    } catch (err: any) {
      const errorMessage = err.message || 'Unknown error';
      alert(`Image detection failed.\nError: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveJSON = () => {
    if (!results) return;
    const dataStr = JSON.stringify(results, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `room-detection-results-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleSaveBoth = () => {
    if (!results) return;

    // Save the image first
    if (results.model_version === 'v1' && v1VisualizationRef.current) {
      // For v1, export the canvas as image
      const canvas = v1VisualizationRef.current.getCanvas();
      if (canvas) {
        canvas.toBlob((blob: Blob | null) => {
          if (blob) {
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `room-detection-visualization-${Date.now()}.png`;
            link.click();
            URL.revokeObjectURL(url);

            // Save JSON after a short delay to ensure image download starts
            setTimeout(handleSaveJSON, 100);
          }
        });
      } else {
        // If canvas is not available, still save JSON
        handleSaveJSON();
      }
    } else if (results.model_version === 'v2' && v2VisualizationRef.current) {
      // For v2, export the canvas as image
      const canvas = v2VisualizationRef.current.getCanvas();
      if (canvas) {
        canvas.toBlob((blob: Blob | null) => {
          if (blob) {
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `room-detection-visualization-${Date.now()}.png`;
            link.click();
            URL.revokeObjectURL(url);

            // Save JSON after a short delay to ensure image download starts
            setTimeout(handleSaveJSON, 100);
          }
        });
      } else {
        // If canvas is not available, still save JSON
        handleSaveJSON();
      }
    } else {
      // If no image can be saved, still save JSON
      handleSaveJSON();
    }
  };

  return (
    <div className="max-w-full mx-auto px-6 pb-6 pt-2">
      {/* Two Column Layout */}
      <div className="mb-4 grid grid-cols-2 gap-4">
        {/* Left Column: Detection Model and Blueprint Upload */}
        <div className="flex flex-col items-end">
          {/* Detection Model */}
          <div className="mb-4 w-full max-w-md">
            <label className="block text-sm font-medium mb-2">
              Detection Model:
            </label>
            <select
              value={modelVersion}
              onChange={(e) => {
                const newVersion = e.target.value as ModelVersion;
                setModelVersion(newVersion);
                // Update confidence threshold to model-specific default when switching
                setConfidenceThreshold(newVersion === 'v1' ? 0.10 : 0.5);
              }}
              className="p-2 border rounded w-full"
              disabled={loading}
            >
              <option value="v1">Wall Model (v1) - 2-Step Pipeline</option>
              <option value="v2">Room Model (v2) - Direct Detection</option>
            </select>
            <p className="text-xs text-gray-500 mt-1" style={{ visibility: 'hidden' }}>
              &nbsp;
            </p>
          </div>

          {/* Blueprint Upload */}
          <div className="w-full max-w-md">
            <label className="block text-sm font-medium mb-2">
              Blueprint Image:
            </label>
            <input
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              disabled={loading}
              className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-full file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100
                disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
        </div>

        {/* Right Column: Confidence Threshold and Detect Button */}
        <div>
          {/* Confidence Threshold */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              Confidence Threshold: {confidenceThreshold.toFixed(2)}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
              disabled={loading}
              className="w-full max-w-xs h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer
                disabled:opacity-50 disabled:cursor-not-allowed
                [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-blue-600
                [&::-webkit-slider-thumb]:cursor-pointer
                [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4
                [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-blue-600
                [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:cursor-pointer"
            />
            <p className="text-xs text-gray-500 mt-1">
              {modelVersion === 'v1'
                ? <>Lower values detect more walls (may include false positives).<br />Higher values are more conservative. Default: 0.10</>
                : <>Lower values detect more rooms (may include false positives).<br />Higher values are more conservative. Default: 0.50</>
              }
            </p>
          </div>

          {/* Detect Button and Save JSON */}
          <div>
            <label className="block text-sm font-medium mb-2">
              &nbsp;
            </label>
            <div className="flex gap-3">
              <button
                onClick={handleUpload}
                disabled={!selectedFile || loading}
                className="px-6 py-2 bg-blue-600 text-white rounded
                  hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed
                  transition-colors duration-200"
              >
                {loading ? 'Detecting...' : 'Detect Rooms'}
              </button>
              {results && (
                <button
                  onClick={handleSaveBoth}
                  className="px-6 py-2 bg-blue-600 text-white rounded
                    hover:bg-blue-700 transition-colors duration-200"
                >
                  Save Image + JSON
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Image Placeholders - Show before results */}
      {!results && (
        <div className="mb-4" style={{ maxWidth: '95%', maxHeight: '50vh', margin: 'auto' }}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              {imagePreview ? (
                <img
                  src={imagePreview}
                  alt="Your blueprint"
                  className="w-full h-auto border-2 border-dashed border-gray-300 rounded"
                  style={{ maxWidth: '768px', maxHeight: '512px', objectFit: 'contain' }}
                />
              ) : (
                <div className="w-full h-96 bg-gray-100 border-2 border-dashed border-gray-300 rounded flex items-center justify-center">
                  <p className="text-gray-400">Your blueprint</p>
                </div>
              )}
            </div>
            <div>
              <div className="w-full h-96 bg-gray-100 border-2 border-dashed border-gray-300 rounded flex items-center justify-center">
                <p className="text-gray-400">Awaiting detection...</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Results Display */}
      {results && (
        <div className="mt-6">
          {/* Side-by-Side Image Comparison */}
          <div className="mb-4" style={{ maxWidth: '95%', maxHeight: '50vh', margin: 'auto' }}>
            <div className="grid grid-cols-2 gap-4">
              {/* Input Image */}
              <div>
                <img
                  src={imagePreview}
                  alt="Original blueprint"
                  className="w-full h-auto border rounded shadow-sm"
                  style={{ maxWidth: '768px', maxHeight: '512px', objectFit: 'contain' }}
                />
              </div>

              {/* Output Image */}
              <div>
                {results.model_version === 'v1' && results.rooms.length > 0 ? (
                  <V1RoomVisualization
                    ref={v1VisualizationRef}
                    imageUrl={imagePreview}
                    rooms={results.rooms}
                  />
                ) : results.model_version === 'v2' && results.rooms.length > 0 ? (
                  <RoomVisualization
                    ref={v2VisualizationRef}
                    imageUrl={imagePreview}
                    rooms={results.rooms}
                  />
                ) : (
                  <div className="w-full h-64 flex items-center justify-center bg-gray-100 border rounded">
                    <p className="text-gray-500">No detections to display</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Results header with stats inline */}
          <div className="flex items-center gap-6 mb-4" style={{ margin: '50px' }}>
            <h2 className="text-2xl font-bold">Results</h2>
            <div className="flex gap-6">
              <div>
                <p className="text-sm text-gray-600">Rooms Detected</p>
                <p className="text-2xl font-bold text-right">{results.total_rooms}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Processing Time</p>
                <p className="text-2xl font-bold text-right">{results.processing_time_ms.toFixed(0)}ms</p>
              </div>
            </div>
          </div>

          {/* Room Details */}
          {results.rooms.length > 0 && (
            <div style={{ marginLeft: '50px' }}>
              <h3 className="text-lg font-semibold mb-2">Detected Rooms</h3>
              <div className="space-y-2">
                {results.rooms.map((room) => (
                  <div key={room.id} className="p-3 bg-gray-50 rounded">
                    <p className="font-medium">{room.id}</p>
                    <p className="text-sm text-gray-600">
                      Area: {room.area_pixels}px² | 
                      Confidence: {(room.confidence * 100).toFixed(1)}% |
                      Shape: {room.shape_type}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {results.rooms.length === 0 && (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
              <p className="text-yellow-700">No rooms detected in this image.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

