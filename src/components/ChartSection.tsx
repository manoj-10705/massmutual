import React from "react";
import "chart.js/auto";
import { Line, Bar, Doughnut } from "react-chartjs-2";
import { YearlySummary } from "../types/financial";

export const ChartSection: React.FC<{ data: YearlySummary[] }> = ({ data }) => {
  const years = data.map((d) => d.year);
  const gdp = data.map((d) => d.gdp);
  const inflation = data.map((d) => d.inflation);
  const closePrice = data.map((d) => d.closePrice);
  const recordsProcessed = data.map((d) => d.recordsProcessed);

  const baseOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-2xl shadow-lg p-6">
        <div className="h-72">
          <Line
            redraw
            data={{
              labels: years,
              datasets: [
                { label: "GDP", data: gdp, borderColor: "#3b82f6", fill: false },
                { label: "Close", data: closePrice, borderColor: "#a855f7", fill: false },
              ],
            }}
            options={baseOptions}
          />
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-lg p-6">
        <div className="h-72">
          <Bar
            redraw
            data={{
              labels: years,
              datasets: [
                { label: "Inflation", data: inflation, backgroundColor: "#ec4899" },
              ],
            }}
            options={baseOptions}
          />
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-lg p-6">
        <div className="h-72">
          <Line
            redraw
            data={{
              labels: years,
              datasets: [
                { label: "Records", data: recordsProcessed, borderColor: "#f97316" },
              ],
            }}
            options={baseOptions}
          />
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-lg p-6">
        <div className="h-72">
          <Doughnut
            redraw
            data={{
              labels: years,
              datasets: [
                {
                  data: recordsProcessed,
                  backgroundColor: ["#3b82f6", "#8b5cf6", "#ec4899", "#f97316"],
                },
              ],
            }}
            options={baseOptions}
          />
        </div>
      </div>
    </div>
  );
};
