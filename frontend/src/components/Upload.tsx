import React, { useState } from 'react';
import type { DetectionResponse, ModelVersion } from '../services/api';
import { detectRooms } from '../services/api';

export function Upload() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<DetectionResponse | null>(null);
  const [error, setError] = useState<string>('');
  const [modelVersion, setModelVersion] = useState<ModelVersion>('v1');
  // Default confidence thresholds: v1 uses 0.10, v2 uses 0.5
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.10);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file');
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('Image size must be less than 10MB');
      return;
    }

    setSelectedFile(file);
    setError('');
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
      setError('Please select an image');
      return;
    }

    setLoading(true);
    setError('');
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
      setError(err.message || 'Detection failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 pb-6 pt-2">
      {/* Two Column Layout */}
      <div className="mb-4 grid grid-cols-2 gap-4">
        {/* Left Column: Detection Model and Blueprint Upload */}
        <div>
          {/* Detection Model */}
          <div className="mb-4">
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
              className="p-2 border rounded w-full max-w-xs"
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
          <div>
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
                ? 'Lower values detect more walls (may include false positives). Higher values are more conservative. Default: 0.10'
                : 'Lower values detect more rooms (may include false positives). Higher values are more conservative. Default: 0.50'
              }
            </p>
          </div>

          {/* Detect Button */}
          <div>
            <label className="block text-sm font-medium mb-2">
              &nbsp;
            </label>
            <button
              onClick={handleUpload}
              disabled={!selectedFile || loading}
              className="px-6 py-2 bg-blue-600 text-white rounded
                hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed
                transition-colors duration-200"
            >
              {loading ? 'Detecting...' : 'Detect Rooms'}
            </button>
          </div>
        </div>
      </div>

      {/* Image Preview */}
      {imagePreview && (
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Preview:</label>
          <img
            src={imagePreview}
            alt="Blueprint preview"
            className="max-w-full h-auto border rounded shadow-sm"
          />
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Results Display */}
      {results && (
        <div className="mt-6">
          <h2 className="text-2xl font-bold mb-4">Results</h2>
          
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="p-4 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">Rooms Detected</p>
              <p className="text-3xl font-bold">{results.total_rooms}</p>
            </div>
            
            <div className="p-4 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">Processing Time</p>
              <p className="text-3xl font-bold">{results.processing_time_ms.toFixed(0)}ms</p>
            </div>
          </div>

          {/* Visualization */}
          {results.visualization && (
            <div className="mb-4">
              <h3 className="text-lg font-semibold mb-2">Visualization</h3>
              <img
                src={`data:image/png;base64,${results.visualization}`}
                alt="Detection results"
                className="max-w-full h-auto border rounded shadow-sm"
              />
            </div>
          )}

          {/* Room Details */}
          {results.rooms.length > 0 && (
            <div>
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

