interface Step {
  label: string;
  sublabel: string;
  state: 'pending' | 'active' | 'done';
}

interface Props {
  steps: Step[];
}

export default function UploadProgress({ steps }: Props) {
  const icons: Record<string, string> = {
    pending: '\u25CB',   // ○
    active: '\u25CE',    // ◎
    done: '\u2713',      // ✓
  };

  return (
    <div className="progress-container">
      <div className="progress-steps">
        {steps.map((step, i) => (
          <div key={i} className={`progress-step ${step.state}`}>
            <div className={`step-indicator ${step.state}`}>
              {icons[step.state]}
            </div>
            <div>
              <div className="step-label">{step.label}</div>
              <div className="step-sublabel">{step.sublabel}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
