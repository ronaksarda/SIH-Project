import React from 'react';

const StatCard = ({ title, value, icon: Icon, colorClass = 'bg-indigo-50 text-indigo-600' }) => {
  return (
    <div className="card card-hover p-6 flex flex-col gap-4">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-slate-500">{title}</p>
        {Icon && (
          <div className={`p-2 rounded-lg ${colorClass}`}>
            <Icon size={18} />
          </div>
        )}
      </div>
      <p className="text-3xl font-bold text-slate-900 tracking-tight">{value}</p>
    </div>
  );
};

export default StatCard;
