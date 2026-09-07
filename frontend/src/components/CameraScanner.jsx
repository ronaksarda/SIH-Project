import React, { useRef, useState, useCallback, useEffect } from 'react';
import { Camera, Image as ImageIcon, RotateCcw, Check } from 'lucide-react';

const CameraScanner = ({ onImageCaptured }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  const [stream, setStream] = useState(null);
  const [error, setError] = useState(null);
  const [capturedImage, setCapturedImage] = useState(null);

  const startCamera = async () => {
    setError(null);
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      setError('Unable to access camera. Please check permissions or use the upload option.');
    }
  };

  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      setStream(null);
    }
  }, [stream]);

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext('2d').drawImage(video, 0, 0);
      setCapturedImage(canvas.toDataURL('image/jpeg'));
      stopCamera();
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onloadend = () => setCapturedImage(reader.result);
    reader.readAsDataURL(file);
  };

  const retakePhoto = () => {
    setCapturedImage(null);
    startCamera();
  };

  const confirmPhoto = () => {
    if (capturedImage && onImageCaptured) onImageCaptured(capturedImage);
  };

  useEffect(() => () => stopCamera(), [stopCamera]);

  /* ── Confirmed image ── */
  if (capturedImage) {
    return (
      <div className="flex flex-col gap-4">
        <div className="relative rounded-xl overflow-hidden bg-slate-900 flex justify-center items-center min-h-[280px]">
          <img src={capturedImage} alt="Captured" className="max-h-[60vh] object-contain" />
        </div>
        <div className="flex justify-center gap-3">
          <button onClick={retakePhoto} className="btn-secondary gap-2">
            <RotateCcw size={16} /> Retake
          </button>
          <button onClick={confirmPhoto} className="btn-primary gap-2">
            <Check size={16} /> Confirm & Analyse
          </button>
        </div>
      </div>
    );
  }

  /* ── Camera / upload ── */
  return (
    <div className="flex flex-col gap-4">
      {error && (
        <div className="bg-rose-50 border-l-4 border-rose-500 rounded-r-lg p-4">
          <p className="text-sm text-rose-700">{error}</p>
        </div>
      )}

      {/* Viewfinder */}
      <div className="relative rounded-xl overflow-hidden bg-slate-950 flex justify-center items-center min-h-[300px]">
        {stream ? (
          <video ref={videoRef} autoPlay playsInline className="absolute inset-0 w-full h-full object-cover" />
        ) : (
          <div className="flex flex-col items-center gap-4 text-center px-6 py-12">
            <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center">
              <Camera className="text-slate-400" size={32} />
            </div>
            <div>
              <p className="text-slate-300 font-medium">No camera active</p>
              <p className="text-slate-500 text-sm mt-1">Start camera or upload an image file</p>
            </div>
            <button onClick={startCamera} className="btn-primary mt-2">
              Start Camera
            </button>
          </div>
        )}

        {/* Corner-bracket viewfinder overlay */}
        {stream && (
          <div className="absolute inset-0 pointer-events-none">
            {/* Top-left */}
            <span className="absolute top-4 left-4 w-8 h-8 border-t-2 border-l-2 border-indigo-400 rounded-tl" />
            {/* Top-right */}
            <span className="absolute top-4 right-4 w-8 h-8 border-t-2 border-r-2 border-indigo-400 rounded-tr" />
            {/* Bottom-left */}
            <span className="absolute bottom-4 left-4 w-8 h-8 border-b-2 border-l-2 border-indigo-400 rounded-bl" />
            {/* Bottom-right */}
            <span className="absolute bottom-4 right-4 w-8 h-8 border-b-2 border-r-2 border-indigo-400 rounded-br" />
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex justify-center gap-3">
        <button
          onClick={capturePhoto}
          disabled={!stream}
          className="btn-primary gap-2 flex-1 sm:flex-none sm:px-8"
        >
          <Camera size={16} /> Capture
        </button>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="btn-secondary gap-2 flex-1 sm:flex-none sm:px-8"
        >
          <ImageIcon size={16} /> Upload File
        </button>
      </div>

      <input type="file" accept="image/*" ref={fileInputRef} onChange={handleFileUpload} className="hidden" />
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
};

export default CameraScanner;
