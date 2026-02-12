import type { UploadResponse, DeployRequest, DeployResponse, Deployment } from './types';

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function uploadZip(file: File, partnerUrl?: string): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  if (partnerUrl) {
    form.append('partner_url', partnerUrl);
  }
  return request<UploadResponse>('/upload', { method: 'POST', body: form });
}

export async function deployProject(id: string, req: DeployRequest): Promise<DeployResponse> {
  return request<DeployResponse>(`/deployments/${id}/deploy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
}

export async function listDeployments(): Promise<Deployment[]> {
  return request<Deployment[]>('/deployments');
}

export async function getDeployment(id: string): Promise<Deployment> {
  return request<Deployment>(`/deployments/${id}`);
}

export async function deleteDeployment(id: string): Promise<void> {
  await request(`/deployments/${id}`, { method: 'DELETE' });
}

// Auth API
export async function checkAuthStatus(): Promise<{ authenticated: boolean; user?: { id: string; email: string; name: string; picture?: string } }> {
  const res = await fetch(`${BASE}/auth/status`, { credentials: 'include' });
  return res.json();
}

export async function logout(): Promise<void> {
  await fetch(`${BASE}/auth/logout`, { credentials: 'include' });
}

export function login(): void {
  window.location.href = `${BASE}/auth/login`;
}
