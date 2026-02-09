interface Props {
  securityStatus: string;
  deploying: boolean;
  onDeploy: (mode: 'demo' | 'prod') => void;
}

export default function DeployButton({ securityStatus, deploying, onDeploy }: Props) {
  const blocked = securityStatus === 'fail';

  if (blocked) {
    return (
      <div className="deploy-section">
        <p className="deploy-blocked">
          Deployment blocked — security scan failed. Fix issues and re-upload.
        </p>
      </div>
    );
  }

  return (
    <div className="deploy-section">
      <button
        className="btn btn-demo"
        disabled={deploying}
        onClick={() => onDeploy('demo')}
      >
        {deploying ? 'Deploying...' : 'Launch Demo (1hr)'}
      </button>
      <button
        className="btn btn-prod"
        disabled={deploying}
        onClick={() => onDeploy('prod')}
      >
        {deploying ? 'Deploying...' : 'Deploy to Production'}
      </button>
    </div>
  );
}
