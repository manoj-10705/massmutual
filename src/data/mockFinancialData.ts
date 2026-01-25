import { KpiData, YearlySummary, PipelineState } from "../types/financial";

export const kpiData: KpiData = {
  totalRecords: 8750000,
  avgGdp: 23450,
  avgInflation: 3.2,
  avgClosePrice: 4850,
};

export const yearlySummaries: YearlySummary[] = [
  { year: 2018, gdp: 20580, inflation: 2.4, closePrice: 2507, recordsProcessed: 1200000 },
  { year: 2019, gdp: 21380, inflation: 1.8, closePrice: 3231, recordsProcessed: 1350000 },
  { year: 2020, gdp: 20930, inflation: 1.2, closePrice: 3756, recordsProcessed: 1420000 },
  { year: 2021, gdp: 23000, inflation: 4.7, closePrice: 4766, recordsProcessed: 1580000 },
  { year: 2022, gdp: 25460, inflation: 8.0, closePrice: 3839, recordsProcessed: 1450000 },
  { year: 2023, gdp: 27360, inflation: 4.1, closePrice: 4770, recordsProcessed: 1750000 },
];

export const pipelineStates: PipelineState[] = [
  { stage: "Data Ingestion", status: "Success", lastRun: "2024-06-15 06:00:00", duration: "12m 34s" },
  { stage: "Spark ETL - Extract", status: "Success", lastRun: "2024-06-15 06:15:00", duration: "8m 12s" },
  { stage: "Spark ETL - Transform", status: "Running", lastRun: "2024-06-15 06:25:00", duration: "5m 42s" },
  { stage: "Data Quality Check", status: "Success", lastRun: "2024-06-15 06:30:00", duration: "3m 18s" },
  { stage: "Airflow Orchestration", status: "Running", lastRun: "2024-06-15 06:35:00", duration: "2m 05s" },
  { stage: "Load to Data Warehouse", status: "Failed", lastRun: "2024-06-15 06:40:00", duration: "1m 22s" },
  { stage: "Analytics Aggregation", status: "Success", lastRun: "2024-06-15 05:50:00", duration: "15m 47s" },
];
