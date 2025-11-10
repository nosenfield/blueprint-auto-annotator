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
      });

      setResults(response);
    } catch (err: any) {
      setError(err.message || 'Detection failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Room Detection</h1>

      {/* Model Selection */}
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">
          Detection Model:
        </label>
        <select
          value={modelVersion}
          onChange={(e) => setModelVersion(e.target.value as ModelVersion)}
          className="p-2 border rounded w-full max-w-xs"
          disabled={loading}
        >
          <option value="v1">Wall Model (v1) - 2-Step Pipeline</option>
          <option value="v2">Room Model (v2) - Direct Detection</option>
        </select>
      </div>

      {/* File Upload */}
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">
          Upload Blueprint Image:
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

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={!selectedFile || loading}
        className="px-6 py-2 bg-blue-600 text-white rounded
          hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed
          transition-colors duration-200"
      >
        {loading ? 'Detecting...' : 'Detect Rooms'}
      </button>

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

