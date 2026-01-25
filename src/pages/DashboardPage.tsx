import React from "react";
import { KpiCard } from "../components/KpiCard";
import { ChartSection } from "../components/ChartSection";
import { YearlySummaryTable } from "../components/YearlySummaryTable";
import { PipelineStatus } from "../components/PipelineStatus";
import { kpiData, yearlySummaries, pipelineStates } from "../data/mockFinancialData";
import { 
  DocumentChartBarIcon, 
  CurrencyDollarIcon, 
  ArrowTrendingUpIcon,
  ChartBarIcon 
} from "@heroicons/react/24/outline";

export const DashboardPage: React.FC = () => {
  return (
    <div className="flex flex-col gap-8 px-2 md:px-0 py-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
            Financial Data Pipeline Overview
          </h2>
          <p className="text-gray-600">Real-time insights from your data processing pipeline</p>
        </div>
        <div className="hidden md:flex items-center gap-2 bg-green-50 px-4 py-2 rounded-lg border border-green-200">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          <span className="text-sm font-semibold text-green-700">Pipeline Active</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KpiCard
          label="Total Records Processed"
          value={kpiData.totalRecords.toLocaleString()}
          icon={<DocumentChartBarIcon className="w-6 h-6" />}
          trend="+12.5%"
          trendUp={true}
          gradient="from-blue-500 to-blue-600"
        />
        <KpiCard
          label="Avg. GDP ($B)"
          value={`$${kpiData.avgGdp.toLocaleString()}`}
          icon={<CurrencyDollarIcon className="w-6 h-6" />}
          trend="+8.3%"
          trendUp={true}
          gradient="from-purple-500 to-purple-600"
        />
        <KpiCard
          label="Avg. Inflation Rate"
          value={`${kpiData.avgInflation.toFixed(1)}%`}
          icon={<ChartBarIcon className="w-6 h-6" />}
          trend="-2.1%"
          trendUp={false}
          gradient="from-pink-500 to-pink-600"
        />
        <KpiCard
          label="Avg. Market Close"
          value={`$${kpiData.avgClosePrice.toLocaleString()}`}
          icon={<ArrowTrendingUpIcon className="w-6 h-6" />}
          trend="+15.7%"
          trendUp={true}
          gradient="from-orange-500 to-orange-600"
        />
      </div>

      {/* Charts */}
      {<ChartSection key="dashboard-charts" data={yearlySummaries} />}

      {/* Table and Pipeline Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <YearlySummaryTable data={yearlySummaries} />
        </div>
        <div>
          <PipelineStatus states={pipelineStates} />
        </div>
      </div>
    </div>
  );
};
