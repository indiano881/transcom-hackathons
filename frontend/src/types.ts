export interface CheckResult {
  status: 'pass' | 'warn' | 'fail';
  summary: string;
  details: string[];
}

export interface UploadResponse {
  deployment_id: string;
  name: string;
  file_count: number;
  total_size: number;
  security: CheckResult;
  cost: CheckResult;
  brand: CheckResult;
}

export interface DeployRequest {
  mode: 'demo' | 'prod';
}

export interface DeployResponse {
  deployment_id: string;
  cloud_run_url: string;
  mode: string;
  expires_at: string | null;
}

export interface Deployment {
  id: string;
  name: string;
  status: string;
  mode: string | null;
  file_count: number;
  total_size: number;
  security_status: string | null;
  security_details: string | null;
  cost_status: string | null;
  cost_details: string | null;
  brand_status: string | null;
  brand_details: string | null;
  cloud_run_url: string | null;
  created_at: string;
  deployed_at: string | null;
  expires_at: string | null;
}

export type AppPhase = 'upload' | 'checking' | 'results' | 'deploying' | 'deployed';
