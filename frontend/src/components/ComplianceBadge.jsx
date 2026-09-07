import React from 'react';
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const configs = {
  pass: {
    classes: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
    label: 'Compliant',
  },
  fail: {
    classes: 'bg-rose-50 text-rose-700 ring-1 ring-rose-600/20',
    icon: <XCircle className="w-3.5 h-3.5" />,
    label: 'Non-Compliant',
  },
  review: {
    classes: 'bg-amber-50 text-amber-700 ring-1 ring-amber-600/20',
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
    label: 'Manual Review',
  },
};

const ComplianceBadge = ({ status }) => {
  const config = configs[status] ?? {
    classes: 'bg-slate-100 text-slate-600 ring-1 ring-slate-300',
    icon: null,
    label: 'Unknown',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${config.classes}`}>
      {config.icon}
      {config.label}
    </span>
  );
};

export default ComplianceBadge;
