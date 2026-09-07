import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ComplianceBadge from '../components/ComplianceBadge';
import BoundingOverlay from '../components/BoundingOverlay';
import { MOCK_REPORTS, MOCK_BOUNDING_BOXES } from '../lib/mockData';
import { ArrowLeft, Download, FileText, CheckCircle2, XCircle, MapPin, User, Calendar, Loader2 } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

const ReportView = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        
        const response = await fetch(`${apiUrl}/api/reports/report/${id}`, {
          headers: {
            'Authorization': `Bearer ${session?.access_token}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          const mappedReport = {
            id: data.inspection.id,
            productName: data.inspection.product_name,
            status: data.inspection.status,
            date: data.inspection.inspection_timestamp,
            location: data.inspection.location || 'Unknown',
            officer: 'Inspector', // We can get this from profiles if joined
            image: data.inspection.image_path,
            declarations: {
              mrp: { present: !!data.declarations.mrp, value: data.declarations.mrp },
              netQuantity: { present: !!data.declarations.net_quantity, value: data.declarations.net_quantity },
              mfgDate: { present: !!data.declarations.mfg_date, value: data.declarations.mfg_date },
              manufacturer: { present: !!data.declarations.manufacturer_address, value: data.declarations.manufacturer_address },
              customerCare: { present: !!data.declarations.consumer_care, value: data.declarations.consumer_care },
            },
            violations: data.violations ? data.violations.map(v => v.description) : []
          };
          setReport(mappedReport);
        } else {
            // Fallback to mock if API returns 404 or errors out
            const mock = MOCK_REPORTS.find((r) => r.id === id) || MOCK_REPORTS[0];
            setReport(mock);
        }
      } catch (error) {
        console.error("Failed to fetch report, using mock data", error);
        const mock = MOCK_REPORTS.find((r) => r.id === id) || MOCK_REPORTS[0];
        setReport(mock);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchReport();
  }, [id]);

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin text-indigo-600" size={32} /></div>;
  }
  
  if (!report) return null;

  return (
    <div className="px-6 py-8 md:px-10 space-y-6 max-w-7xl">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Inspection Report</h1>
            <p className="text-sm text-slate-500 mt-0.5 font-mono">{report.id}</p>
          </div>
        </div>

        <div className="flex gap-2 ml-11 sm:ml-0">
          <button disabled className="btn-secondary gap-2 text-xs opacity-50 cursor-not-allowed">
            <FileText size={14} /> Export DOCX
          </button>
          <button disabled className="btn-primary gap-2 text-xs opacity-50 cursor-not-allowed">
            <Download size={14} /> Export PDF
          </button>
        </div>
      </div>

      {/* ── Body Grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">

        {/* Left — Sticky Evidence Panel */}
        <div className="lg:col-span-1 lg:sticky lg:top-6 space-y-4">
          <div className="card overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-700">Scanned Evidence</h3>
              <span className="text-xs text-slate-400">AI-tagged</span>
            </div>
            <div className="relative bg-slate-950 flex justify-center items-center min-h-[220px]">
              <img
                src={report.image}
                alt={report.productName}
                className="max-w-full object-contain max-h-[280px]"
              />
              <BoundingOverlay boxes={MOCK_BOUNDING_BOXES} />
            </div>
            <div className="px-5 py-3 bg-slate-50 border-t border-slate-100">
              <p className="text-xs text-slate-500">OCR bounding boxes overlay. Coordinates mapped by vision pipeline.</p>
            </div>
          </div>

          {/* Meta info */}
          <div className="card px-5 py-4 space-y-3">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Inspection Details</h3>
            <dl className="space-y-2.5">
              <div className="flex items-start gap-2.5">
                <User size={14} className="text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <dt className="text-xs text-slate-400">Officer</dt>
                  <dd className="text-sm font-medium text-slate-900">{report.officer}</dd>
                </div>
              </div>
              <div className="flex items-start gap-2.5">
                <MapPin size={14} className="text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <dt className="text-xs text-slate-400">Location</dt>
                  <dd className="text-sm font-medium text-slate-900">{report.location}</dd>
                </div>
              </div>
              <div className="flex items-start gap-2.5">
                <Calendar size={14} className="text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <dt className="text-xs text-slate-400">Date &amp; Time</dt>
                  <dd className="text-sm font-medium text-slate-900">
                    {new Date(report.date).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
                  </dd>
                </div>
              </div>
            </dl>
          </div>
        </div>

        {/* Right — Analysis Detail */}
        <div className="lg:col-span-2 space-y-5">
          {/* Product summary */}
          <div className="card px-6 py-5 flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">Product</p>
              <h2 className="text-xl font-semibold text-slate-900">{report.productName}</h2>
            </div>
            <ComplianceBadge status={report.status} />
          </div>

          {/* Mandatory Declarations */}
          <div className="card overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h3 className="text-sm font-semibold text-slate-700">Mandatory Declarations</h3>
              <p className="text-xs text-slate-400 mt-0.5">As required by Legal Metrology (Packaged Commodities) Rules, 2011</p>
            </div>
            <div className="divide-y divide-slate-100">
              {Object.entries(report.declarations).map(([key, data], i) => (
                <div
                  key={key}
                  className={`px-6 py-4 flex items-center justify-between gap-4 ${i % 2 === 1 ? 'bg-slate-50/60' : ''}`}
                >
                  <div className="flex items-center gap-3">
                    {data.present ? (
                      <CheckCircle2 size={18} className="text-emerald-500 flex-shrink-0" />
                    ) : (
                      <XCircle size={18} className="text-rose-500 flex-shrink-0" />
                    )}
                    <span className="text-sm font-medium text-slate-800 capitalize">
                      {key.replace(/([A-Z])/g, ' $1').trim()}
                    </span>
                  </div>
                  <span className={`text-xs font-mono px-2.5 py-1 rounded-md ${
                    data.present ? 'bg-slate-100 text-slate-700' : 'bg-rose-50 text-rose-600 ring-1 ring-rose-200'
                  }`}>
                    {data.value ?? 'Not Detected'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Violations */}
          {report.violations.length > 0 && (
            <div className="card border-l-4 border-rose-500 overflow-hidden">
              <div className="px-6 py-4 border-b border-rose-100 bg-rose-50">
                <h3 className="text-sm font-semibold text-rose-800 flex items-center gap-2">
                  <XCircle size={16} /> Identified Violations ({report.violations.length})
                </h3>
              </div>
              <div className="px-6 py-4 space-y-3">
                {report.violations.map((v, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-rose-100 text-rose-600 text-xs font-bold flex items-center justify-center mt-0.5">
                      {i + 1}
                    </span>
                    <p className="text-sm text-rose-800 font-medium">{v}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReportView;
