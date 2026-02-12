import { useState, useEffect, useCallback } from 'react';
import type { AppPhase, UploadResponse, Deployment } from './types';
import { uploadZip, deployProject, listDeployments, deleteDeployment } from './api';
import Header from './components/Header';
import DropZone from './components/DropZone';
import UploadProgress from './components/UploadProgress';
import CheckResults from './components/CheckResults';
import DeployButton from './components/DeployButton';
import DeploymentList from './components/DeploymentList';

function App() {
  const [phase, setPhase] = useState<AppPhase>('upload');
  const [error, setError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [deploying, setDeploying] = useState(false);
  const [partnerUrl, setPartnerUrl] = useState('');
  const [savedPartnerUrl, setSavedPartnerUrl] = useState('');

  const loadDeployments = useCallback(async () => {
    try {
      const list = await listDeployments();
      setDeployments(list);
    } catch {
      // silently fail on list refresh
    }
  }, []);

  useEffect(() => {
    loadDeployments();
    const interval = setInterval(loadDeployments, 10000);
    return () => clearInterval(interval);
  }, [loadDeployments]);

  const handleFile = async (file: File) => {
    setError(null);
    setPhase('checking');
    try {
      const result = await uploadZip(file, savedPartnerUrl || undefined);
      setUploadResult(result);
      setPhase('results');
      loadDeployments();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
      setPhase('upload');
    }
  };

  const handleDeploy = async (mode: 'demo' | 'prod') => {
    if (!uploadResult) return;
    setError(null);
    setDeploying(true);
    setPhase('deploying');
    try {
      await deployProject(uploadResult.deployment_id, { mode });
      setPhase('deployed');
      loadDeployments();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Deploy failed';
      setError(message);
      setPhase('results');
    } finally {
      setDeploying(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDeployment(id);
      loadDeployments();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Delete failed';
      setError(message);
    }
  };

  const reset = () => {
    setPhase('upload');
    setUploadResult(null);
    setError(null);
    setPartnerUrl('');
    setSavedPartnerUrl('');
  };

  const checkingSteps = [
    {
      label: 'Security Scan',
      sublabel: 'Checking for XSS, secrets, and malicious code',
      state: phase === 'checking' ? 'active' as const : 'done' as const,
    },
    {
      label: 'Cost Forecast',
      sublabel: 'Estimating Cloud Run hosting costs',
      state: phase === 'checking' ? 'active' as const : 'done' as const,
    },
    {
      label: 'Brand Validation',
      sublabel: savedPartnerUrl
        ? `Checking brand alignment with ${(() => { try { return new URL(savedPartnerUrl).hostname; } catch { return savedPartnerUrl; } })()}`
        : 'Checking Transcom brand alignment',
      state: phase === 'checking' ? 'active' as const : 'done' as const,
    },
  ];

  return (
    <>
      <Header />
      <main className="main">
        {error && (
          <div className="error-banner">{error}</div>
        )}

        {phase === 'upload' && (
          <>
            <DropZone onFile={handleFile} />
            <div className="partner-option">
              <p className="partner-helper">
                Brand check defaults to Transcom. Add a partner URL to check against their brand instead.
              </p>
              {savedPartnerUrl ? (
                <div className="partner-saved">
                  <span className="partner-saved-url">{savedPartnerUrl}</span>
                  <button
                    className="partner-saved-remove"
                    onClick={() => { setSavedPartnerUrl(''); setPartnerUrl(''); }}
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <div className="partner-url-row">
                  <input
                    type="url"
                    className="partner-input"
                    placeholder="https://www.pinterest.com"
                    value={partnerUrl}
                    onChange={(e) => setPartnerUrl(e.target.value)}
                  />
                  <button
                    className="btn btn-sm btn-demo"
                    disabled={!partnerUrl}
                    onClick={() => setSavedPartnerUrl(partnerUrl)}
                  >
                    Save
                  </button>
                </div>
              )}
            </div>
          </>
        )}

        {phase === 'checking' && (
          <UploadProgress steps={checkingSteps} />
        )}

        {(phase === 'results' || phase === 'deploying') && uploadResult && (
          <>
            <CheckResults
              security={uploadResult.security}
              cost={uploadResult.cost}
              brand={uploadResult.brand}
            />
            <DeployButton
              securityStatus={uploadResult.security.status}
              deploying={deploying}
              onDeploy={handleDeploy}
            />
            <div className="new-upload">
              <button className="btn btn-secondary btn-sm" onClick={reset}>
                Upload another
              </button>
            </div>
          </>
        )}

        {phase === 'deployed' && uploadResult && (
          <>
            <CheckResults
              security={uploadResult.security}
              cost={uploadResult.cost}
              brand={uploadResult.brand}
            />
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <p style={{ fontSize: 18, fontWeight: 600, color: 'var(--success)' }}>
                Deployed successfully!
              </p>
              <p style={{ marginTop: 8, color: 'var(--gray-400)' }}>
                Check the deployment history below for your live URL.
              </p>
            </div>
            <div className="new-upload">
              <button className="btn btn-demo" onClick={reset}>
                Deploy another
              </button>
            </div>
          </>
        )}

        <DeploymentList deployments={deployments} onDelete={handleDelete} />
      </main>
    </>
  );
}

export default App;
