import type { Deployment } from '../types';
import DeploymentCard from './DeploymentCard';

interface Props {
  deployments: Deployment[];
  onDelete: (id: string) => void;
}

export default function DeploymentList({ deployments, onDelete }: Props) {
  if (deployments.length === 0) return null;

  return (
    <div className="deployment-list">
      <h3>Deployment History</h3>
      {deployments.map((d) => (
        <DeploymentCard key={d.id} deployment={d} onDelete={onDelete} />
      ))}
    </div>
  );
}
