import { useEffect, useState } from 'react';
import type { Deployment } from '../types';

interface Props {
  deployment: Deployment;
  onDelete: (id: string) => void;
}

function formatTimeLeft(expiresAt: string): string {
  const diff = new Date(expiresAt).getTime() - Date.now();
  if (diff <= 0) return 'Expired';
  const minutes = Math.floor(diff / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);
  if (minutes > 0) return `${minutes}m ${seconds}s left`;
  return `${seconds}s left`;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

export default function DeploymentCard({ deployment, onDelete }: Props) {
  const [timeLeft, setTimeLeft] = useState('');

  useEffect(() => {
    if (!deployment.expires_at) return;
    const update = () => setTimeLeft(formatTimeLeft(deployment.expires_at!));
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [deployment.expires_at]);

  return (
    <div className="deployment-card">
      <div className="deployment-info">
        <div className="deployment-name">{deployment.name}</div>
        <div className="deployment-meta">
          <span className={`status-pill ${deployment.status}`}>
            {deployment.status}
          </span>
          {deployment.mode && <span>{deployment.mode}</span>}
          <span>{deployment.file_count} files, {formatSize(deployment.total_size)}</span>
          {deployment.cloud_run_url && (
            <a href={deployment.cloud_run_url} target="_blank" rel="noopener noreferrer">
              Open site
            </a>
          )}
          {deployment.expires_at && deployment.status === 'deployed' && (
            <span className="countdown">{timeLeft}</span>
          )}
        </div>
      </div>
      <div className="deployment-actions">
        <button
          className="btn btn-danger btn-sm"
          onClick={() => onDelete(deployment.id)}
        >
          Teardown
        </button>
      </div>
    </div>
  );
}
