interface Props {
  status: string;
}

export default function StatusBadge({ status }: Props) {
  const labels: Record<string, string> = {
    pass: 'Pass',
    warn: 'Warn',
    fail: 'Fail',
  };

  return (
    <span className={`badge ${status}`}>
      {labels[status] || status}
    </span>
  );
}
