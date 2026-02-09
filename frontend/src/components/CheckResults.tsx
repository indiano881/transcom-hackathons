import type { CheckResult } from '../types';
import StatusBadge from './StatusBadge';

interface Props {
  security: CheckResult;
  cost: CheckResult;
  brand: CheckResult;
}

function ResultCard({ title, result }: { title: string; result: CheckResult }) {
  return (
    <div className={`result-card ${result.status}`}>
      <div className="result-header">
        <span className="result-title">{title}</span>
        <StatusBadge status={result.status} />
      </div>
      <p className="result-summary">{result.summary}</p>
      {result.details.length > 0 && (
        <ul className="result-details">
          {result.details.map((d, i) => (
            <li key={i}>{d}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function CheckResults({ security, cost, brand }: Props) {
  return (
    <div className="results-section">
      <div className="results-grid">
        <ResultCard title="Security" result={security} />
        <ResultCard title="Cost" result={cost} />
        <ResultCard title="Brand" result={brand} />
      </div>
    </div>
  );
}
