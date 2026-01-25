import React from "react";
import { Link } from "react-router-dom";
import { 
  ChartBarIcon, 
  CircleStackIcon, 
  CpuChipIcon, 
  ArrowRightIcon,
  CheckCircleIcon 
} from "@heroicons/react/24/outline";

export const LandingPage: React.FC = () => (
  <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)] px-4 py-12">
    <div className="max-w-6xl w-full">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <div className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-50 to-purple-50 px-4 py-2 rounded-full mb-6 border border-blue-200">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          <span className="text-sm font-semibold text-blue-700">Live Production Pipeline</span>
        </div>
        
        <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent mb-6">
          MassMutual Financial Data Pipeline
        </h1>
        
        <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8 leading-relaxed">
          Enterprise-grade data processing platform powered by Apache Spark and Airflow, 
          delivering real-time financial insights and analytics at scale.
        </p>

        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-8 py-4 rounded-xl font-semibold shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200"
        >
          View Dashboard
          <ArrowRightIcon className="w-5 h-5" />
        </Link>
      </div>

      {/* Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-2xl p-8 border border-blue-200 hover:shadow-xl transition-shadow">
          <div className="w-14 h-14 bg-blue-600 rounded-xl flex items-center justify-center mb-4">
            <CpuChipIcon className="w-8 h-8 text-white" />
          </div>
          <h3 className="text-xl font-bold text-blue-900 mb-3">Apache Spark Processing</h3>
          <p className="text-blue-700 leading-relaxed">
            Distributed computing framework processing millions of financial records with 
            lightning-fast ETL operations and real-time transformations.
          </p>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-2xl p-8 border border-purple-200 hover:shadow-xl transition-shadow">
          <div className="w-14 h-14 bg-purple-600 rounded-xl flex items-center justify-center mb-4">
            <CircleStackIcon className="w-8 h-8 text-white" />
          </div>
          <h3 className="text-xl font-bold text-purple-900 mb-3">Airflow Orchestration</h3>
          <p className="text-purple-700 leading-relaxed">
            Automated workflow management with intelligent scheduling, monitoring, and 
            error handling for seamless data pipeline execution.
          </p>
        </div>

        <div className="bg-gradient-to-br from-pink-50 to-pink-100 rounded-2xl p-8 border border-pink-200 hover:shadow-xl transition-shadow">
          <div className="w-14 h-14 bg-pink-600 rounded-xl flex items-center justify-center mb-4">
            <ChartBarIcon className="w-8 h-8 text-white" />
          </div>
          <h3 className="text-xl font-bold text-pink-900 mb-3">Real-Time Analytics</h3>
          <p className="text-pink-700 leading-relaxed">
            Executive dashboards with live KPIs, trend analysis, and actionable insights 
            for data-driven financial decision making.
          </p>
        </div>
      </div>

      {/* Pipeline Flow */}
      <div className="bg-gradient-to-r from-slate-50 to-slate-100 rounded-2xl p-8 border border-slate-200">
        <h2 className="text-2xl font-bold text-slate-900 mb-6 text-center">Data Pipeline Architecture</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-center">
          <div className="bg-white rounded-xl p-6 shadow-md border-2 border-blue-200">
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-2xl">📥</span>
              </div>
              <h4 className="font-bold text-slate-900 mb-1">Ingestion</h4>
              <p className="text-xs text-slate-600">Raw Data Sources</p>
            </div>
          </div>

          <div className="hidden md:flex justify-center">
            <ArrowRightIcon className="w-8 h-8 text-slate-400" />
          </div>

          <div className="bg-white rounded-xl p-6 shadow-md border-2 border-purple-200">
            <div className="text-center">
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-2xl">⚡</span>
              </div>
              <h4 className="font-bold text-slate-900 mb-1">Spark ETL</h4>
              <p className="text-xs text-slate-600">Transform & Clean</p>
            </div>
          </div>

          <div className="hidden md:flex justify-center">
            <ArrowRightIcon className="w-8 h-8 text-slate-400" />
          </div>

          <div className="bg-white rounded-xl p-6 shadow-md border-2 border-pink-200">
            <div className="text-center">
              <div className="w-12 h-12 bg-pink-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-2xl">📊</span>
              </div>
              <h4 className="font-bold text-slate-900 mb-1">Analytics</h4>
              <p className="text-xs text-slate-600">Insights & Reports</p>
            </div>
          </div>
        </div>

        <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
          
        </div>
      </div>
    </div>
  </div>
);
