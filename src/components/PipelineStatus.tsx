import React from "react";
import { PipelineState } from "../types/financial";
import { 
  CheckCircleIcon, 
  ExclamationCircleIcon, 
  ArrowPathIcon,
  ClockIcon 
} from "@heroicons/react/24/solid";

const statusConfig: Record<string, { 
  color: string; 
  bgColor: string; 
  icon: React.ReactNode;
  borderColor: string;
}> = {
  Running: {
    color: "text-blue-700",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
    icon: <ArrowPathIcon className="w-4 h-4 animate-spin" />,
  },
  Success: {
    color: "text-green-700",
    bgColor: "bg-green-50",
    borderColor: "border-green-200",
    icon: <CheckCircleIcon className="w-4 h-4" />,
  },
  Failed: {
    color: "text-red-700",
    bgColor: "bg-red-50",
    borderColor: "border-red-200",
    icon: <ExclamationCircleIcon className="w-4 h-4" />,
  },
};

export const PipelineStatus: React.FC<{ states: PipelineState[] }> = ({ states }) => {
  const successCount = states.filter(s => s.status === "Success").length;
  const runningCount = states.filter(s => s.status === "Running").length;
  const failedCount = states.filter(s => s.status === "Failed").length;

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
      <div className="bg-gradient-to-r from-purple-50 to-pink-50 px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-bold text-gray-900">Pipeline Status</h3>
        <p className="text-sm text-gray-600 mt-1">Real-time execution monitoring</p>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-3 gap-3 p-4 bg-gray-50 border-b border-gray-200">
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{successCount}</div>
          <div className="text-xs text-gray-600 font-medium">Success</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">{runningCount}</div>
          <div className="text-xs text-gray-600 font-medium">Running</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-red-600">{failedCount}</div>
          <div className="text-xs text-gray-600 font-medium">Failed</div>
        </div>
      </div>

      {/* Pipeline Stages */}
      <div className="p-4">
        <ul className="space-y-3">
          {states.map((s, index) => {
            const config = statusConfig[s.status];
            return (
              <li 
                key={s.stage} 
                className={`${config.bgColor} ${config.borderColor} border-2 rounded-xl p-4 transition-all hover:shadow-md`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`${config.color} flex items-center justify-center w-6 h-6 rounded-full bg-white shadow-sm`}>
                      {config.icon}
                    </span>
                    <span className="font-bold text-gray-900 text-sm">{s.stage}</span>
                  </div>
                  <span className={`${config.color} ${config.bgColor} px-3 py-1 rounded-full text-xs font-bold border ${config.borderColor}`}>
                    {s.status}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-gray-600 ml-8">
                  <div className="flex items-center gap-1">
                    <ClockIcon className="w-3 h-3" />
                    <span>{s.lastRun}</span>
                  </div>
                  <span className="font-semibold">{s.duration}</span>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
};
