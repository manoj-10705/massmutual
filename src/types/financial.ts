export type PipelineStatus = "Running" | "Success" | "Failed";

export interface KpiData {
  totalRecords: number;
  avgGdp: number;
  avgInflation: number;
  avgClosePrice: number;
}

export interface YearlySummary {
  year: number;
  gdp: number;
  inflation: number;
  closePrice: number;
  recordsProcessed: number;
}

export interface PipelineState {
  stage: string;
  status: PipelineStatus;
  lastRun: string;
  duration: string;
}
