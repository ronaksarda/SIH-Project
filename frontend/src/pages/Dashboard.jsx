import React, { useState, useEffect } from 'react';
import StatCard from '../components/StatCard';
import ReportTable from '../components/ReportTable';
import { MOCK_REPORTS, MOCK_DASHBOARD_STATS } from '../lib/mockData';
import { ClipboardList, ShieldCheck, AlertCircle, Clock, Search, SlidersHorizontal } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';
const statConfig = [
  {
    title: 'Total Inspections',
    key: 'totalInspections',
    icon: ClipboardList,
    colorClass: 'bg-indigo-50 text-indigo-600',
  },
  {
    title: 'Compliant Products',
    key: 'compliant',
    icon: ShieldCheck,
    colorClass: 'bg-emerald-50 text-emerald-600',
  },
  {
    title: 'Non-Compliant',
    key: 'nonCompliant',
    icon: AlertCircle,
    colorClass: 'bg-rose-50 text-rose-600',
  },
  {
    title: 'Manual Review Needed',
    key: 'manualReview',
    icon: Clock,
    colorClass: 'bg-amber-50 text-amber-600',
  },
];

const Dashboard = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [stats, setStats] = useState(MOCK_DASHBOARD_STATS);
  const [reports, setReports] = useState(MOCK_REPORTS);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        
        const response = await fetch(`${apiUrl}/api/dashboard/dashboard`, {
          headers: {
            'Authorization': `Bearer ${session?.access_token}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          setStats({
            totalInspections: data.stats.total_inspections,
            compliant: data.stats.compliant_count,
            nonCompliant: data.stats.non_compliant_count,
            manualReview: data.stats.review_count,
          });
          
          // Map backend recent_inspections to match frontend ReportTable format
          if (data.recent_inspections && data.recent_inspections.length > 0) {
              const mappedReports = data.recent_inspections.map(i => ({
                  id: i.id,
                  productName: i.product_name,
                  status: i.status,
                  date: new Date(i.inspection_timestamp).toLocaleDateString(),
                  issues: i.status === 'fail' ? 1 : 0
              }));
              setReports(mappedReports);
          } else {
             setReports([]); // Or keep MOCK_REPORTS if empty for demo purposes? Let's use empty if API succeeds but has no data.
          }
        }
      } catch (error) {
        console.error("Failed to fetch dashboard data, using mock data", error);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchDashboardData();
  }, []);

  const filteredReports = reports.filter((report) => {
    const matchesSearch =
      report.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      report.productName.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === 'all' || report.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="px-6 py-8 md:px-10 space-y-8 max-w-7xl">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Enforcement Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Overview of all inspections and compliance status across your jurisdiction.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        {statConfig.map(({ title, key, icon, colorClass }) => (
          <StatCard
            key={key}
            title={title}
            value={stats[key]}
            icon={icon}
            colorClass={colorClass}
          />
        ))}
      </div>

      {/* Divider */}
      <div className="border-t border-slate-200" />

      {/* Recent Inspections */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Recent Inspections</h2>
            <p className="text-xs text-slate-400 mt-0.5">{filteredReports.length} result{filteredReports.length !== 1 ? 's' : ''}</p>
          </div>

          <div className="flex gap-2 flex-col sm:flex-row">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
              <input
                type="text"
                placeholder="Search ID or product..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="form-input pl-9 py-2 text-sm w-full sm:w-56"
              />
            </div>

            <div className="relative">
              <SlidersHorizontal className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 pointer-events-none" />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="form-input pl-9 py-2 text-sm appearance-none pr-8 w-full sm:w-48"
              >
                <option value="all">All Statuses</option>
                <option value="pass">Compliant</option>
                <option value="fail">Non-Compliant</option>
                <option value="review">Review Needed</option>
              </select>
            </div>
          </div>
        </div>

        <ReportTable reports={filteredReports} />
      </div>
    </div>
  );
};

export default Dashboard;
