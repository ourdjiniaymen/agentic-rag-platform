import './StatusBadge.css';

const STATUS_LABELS = {
  pending: 'Pending',
  processing: 'Processing',
  indexed: 'Indexed',
  failed: 'Failed',
};

export default function StatusBadge({ status }) {
  return <span className={`status-badge status-badge--${status}`}>{STATUS_LABELS[status] ?? status}</span>;
}