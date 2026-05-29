import StatusBadge from './StatusBadge';

export default function Navbar({ cacheWarm, noConnection, lastUpdated, onRefresh }) {
  return (
    <nav className="navbar navbar-dark px-4 py-2" style={{ background: '#1a1a2e' }}>
      <span className="navbar-brand fw-bold fs-5">Supermercado Analytics</span>
      <div className="d-flex align-items-center gap-3">
        {lastUpdated && (
          <small className="text-secondary">Actualizado: {lastUpdated}</small>
        )}
        <StatusBadge cacheWarm={cacheWarm} noConnection={noConnection} />
      </div>
    </nav>
  );
}
