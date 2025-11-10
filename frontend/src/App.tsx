import React from 'react';
import { Upload } from './components/Upload';
import './App.css';

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-900">Room Reader</h1>
          <p className="text-sm text-gray-600">Automated room detection from architectural blueprints</p>
        </div>
      </header>
      
      <main className="py-8">
        <Upload />
      </main>
      
      <footer className="bg-white border-t mt-12">
        <div className="max-w-4xl mx-auto px-6 py-4 text-center text-sm text-gray-600">
          <p>Room Reader v1.0 - Powered by YOLO-based wall detection and geometric algorithms</p>
        </div>
      </footer>
    </div>
  );
}

export default App;

