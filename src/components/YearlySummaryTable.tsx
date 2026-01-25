import React from "react";
import { YearlySummary } from "../types/financial";
import { ArrowUpIcon, ArrowDownIcon } from "@heroicons/react/24/solid";

export const YearlySummaryTable: React.FC<{ data: YearlySummary[] }> = ({ data }) => {
  const calculateChange = (current: number, previous: number) => {
    if (!previous) return null;
    const change = ((current - previous) / previous) * 100;
    return change;
  };

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-bold text-gray-900">Yearly Financial Summary</h3>
        <p className="text-sm text-gray-600 mt-1">Comprehensive year-over-year analysis</p>
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="py-4 px-6 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                Year
              </th>
              <th className="py-4 px-6 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                GDP ($B)
              </th>
              <th className="py-4 px-6 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                Inflation (%)
              </th>
              <th className="py-4 px-6 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                Close Price
              </th>
              <th className="py-4 px-6 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                Records
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {data.map((row, index) => {
              const prevRow = index > 0 ? data[index - 1] : null;
              const gdpChange = prevRow ? calculateChange(row.gdp, prevRow.gdp) : null;
              const priceChange = prevRow ? calculateChange(row.closePrice, prevRow.closePrice) : null;

              return (
                <tr key={row.year} className="hover:bg-blue-50 transition-colors">
                  <td className="py-4 px-6">
                    <span className="font-bold text-gray-900 text-lg">{row.year}</span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-900">
                        ${row.gdp.toLocaleString()}
                      </span>
                      {gdpChange !== null && (
                        <span className={`flex items-center gap-1 text-xs font-semibold ${
                          gdpChange >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {gdpChange >= 0 ? (
                            <ArrowUpIcon className="w-3 h-3" />
                          ) : (
                            <ArrowDownIcon className="w-3 h-3" />
                          )}
                          {Math.abs(gdpChange).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${
                      row.inflation > 4 
                        ? 'bg-red-100 text-red-700' 
                        : row.inflation > 2 
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-green-100 text-green-700'
                    }`}>
                      {row.inflation.toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-900">
                        ${row.closePrice.toLocaleString()}
                      </span>
                      {priceChange !== null && (
                        <span className={`flex items-center gap-1 text-xs font-semibold ${
                          priceChange >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {priceChange >= 0 ? (
                            <ArrowUpIcon className="w-3 h-3" />
                          ) : (
                            <ArrowDownIcon className="w-3 h-3" />
                          )}
                          {Math.abs(priceChange).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    <span className="font-semibold text-gray-900">
                      {row.recordsProcessed.toLocaleString()}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
