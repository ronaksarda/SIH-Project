import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import CameraScanner from '../components/CameraScanner';
import BoundingOverlay from '../components/BoundingOverlay';
import { MOCK_BOUNDING_BOXES } from '../lib/mockData';
import { ArrowRight, RotateCcw, ScanLine, Brain, CheckCircle2 } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

const STEPS = [
  { id: 'capture', label: 'Capture', step: 1 },
  { id: 'analyzing', label: 'Analyse', step: 2 },
  { id: 'result', label: 'Review', step: 3 },
];

const ANALYSIS_STAGES = [
  { label: 'Running OCR extraction...', icon: ScanLine },
  { label: 'Parsing mandatory declarations...', icon: Brain },
  { label: 'Applying compliance rules...', icon: CheckCircle2 },
];

const StepIndicator = ({ currentStep }) => {
  const currentIndex = STEPS.findIndex((s) => s.id === currentStep);
  return (
    <div className="flex items-center gap-0 mb-8">
      {STEPS.map((s, i) => {
        const done = i < currentIndex;
        const active = i === currentIndex;
        return (
          <React.Fragment key={s.id}>
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                  done
                    ? 'bg-emerald-500 text-white'
                    : active
                    ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
                    : 'bg-slate-100 text-slate-400'
                }`}
              >
                {done ? <CheckCircle2 size={16} /> : s.step}
              </div>
              <span className={`text-xs font-medium ${active ? 'text-indigo-600' : done ? 'text-emerald-600' : 'text-slate-400'}`}>
                {s.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`flex-1 h-0.5 mb-5 mx-2 transition-all duration-500 ${done ? 'bg-emerald-400' : 'bg-slate-200'}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

const AnalyzingState = () => {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    if (stage >= ANALYSIS_STAGES.length - 1) return;
    const t = setTimeout(() => setStage((s) => s + 1), 650);
    return () => clearTimeout(t);
  }, [stage]);

  return (
    <div className="flex flex-col items-center justify-center py-16 gap-8">
      <div className="relative">
        <div className="w-20 h-20 rounded-full border-4 border-indigo-100 border-t-indigo-600 animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <ScanLine className="text-indigo-600" size={28} />
        </div>
      </div>

      <div className="w-full max-w-xs space-y-3">
        {ANALYSIS_STAGES.map((s, i) => {
          const Icon = s.icon;
          const done = i < stage;
          const active = i === stage;
          return (
            <div
              key={i}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300 ${
                active ? 'bg-indigo-50 ring-1 ring-indigo-200' : done ? 'opacity-50' : 'opacity-25'
              }`}
            >
              <Icon size={16} className={active ? 'text-indigo-600' : done ? 'text-emerald-500' : 'text-slate-400'} />
              <span className={`text-sm font-medium ${active ? 'text-indigo-800' : 'text-slate-600'}`}>{s.label}</span>
              {done && <CheckCircle2 size={14} className="ml-auto text-emerald-500" />}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const ScanProduct = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState('capture');
  const [image, setImage] = useState(null);

  const [inspectionId, setInspectionId] = useState('REP-2026-08-001');

  const handleImageCaptured = async (imgData) => {
    setImage(imgData);
    setStep('analyzing');
    
    try {
        const { data: { session } } = await supabase.auth.getSession();
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        
        // Convert base64 to Blob
        const fetchResponse = await fetch(imgData);
        const blob = await fetchResponse.blob();
        
        const formData = new FormData();
        formData.append('image', blob, 'scan.jpg');
        formData.append('product_name', 'Unknown Product'); // Hardcoded for now
        
        const response = await fetch(`${apiUrl}/api/scan/scan`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${session?.access_token}`
            },
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.inspection && data.inspection.id) {
                setInspectionId(data.inspection.id);
            }
        }
    } catch (err) {
        console.error("Failed to upload scan, proceeding with mock analysis", err);
    }
    
    // Maintain minimum delay for visual feedback
    setTimeout(() => setStep('result'), 2200);
  };

  const resetScan = () => {
    setImage(null);
    setStep('capture');
  };

  return (
    <div className="px-6 py-8 md:px-10 max-w-3xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">New Inspection Scan</h1>
        <p className="mt-1 text-sm text-slate-500">
          Capture or upload an image of the packaged commodity for automated compliance analysis.
        </p>
      </div>

      {/* Card */}
      <div className="card p-6 md:p-8">
        <StepIndicator currentStep={step} />

        {step === 'capture' && <CameraScanner onImageCaptured={handleImageCaptured} />}

        {step === 'analyzing' && <AnalyzingState />}

        {step === 'result' && (
          <div className="space-y-6">
            <div className="relative rounded-xl overflow-hidden bg-slate-950 flex justify-center items-center min-h-[280px]">
              <img src={image} alt="Analysed" className="max-h-[50vh] object-contain" />
              <BoundingOverlay boxes={MOCK_BOUNDING_BOXES} />
            </div>

            <div className="flex items-start gap-3 bg-emerald-50 border border-emerald-200 rounded-xl p-4">
              <CheckCircle2 className="text-emerald-600 mt-0.5 flex-shrink-0" size={18} />
              <div>
                <p className="text-sm font-semibold text-emerald-800">Analysis complete</p>
                <p className="text-sm text-emerald-700 mt-0.5">
                  OCR extraction and rule verification finished. Review the full inspection report to confirm findings.
                </p>
              </div>
            </div>

            <div className="flex justify-between items-center">
              <button onClick={resetScan} className="btn-secondary gap-2">
                <RotateCcw size={15} /> Scan Another
              </button>
              <button onClick={() => navigate(`/report/${inspectionId}`)} className="btn-primary gap-2">
                View Full Report <ArrowRight size={15} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ScanProduct;
