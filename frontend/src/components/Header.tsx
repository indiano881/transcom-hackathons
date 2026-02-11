import { login, logout } from '../api';

interface HeaderProps {
  authState: {
    authenticated: boolean;
    user?: {
      id: string;
      email: string;
      name: string;
      picture?: string;
    };
  };
  onAuthChange: () => void;
}

export default function Header({ authState, onAuthChange }: HeaderProps) {
  const handleLogout = async () => {
    await logout();
    onAuthChange();
  };

  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-logo">A</div>
        <div>
          <div className="header-title">
            Innovation <span>Airlock</span>
          </div>
          <div className="header-subtitle">Transcom Deployment Gateway</div>
        </div>
      </div>

      <div className="header-auth">
        {authState.authenticated && authState.user ? (
          <div className="auth-user">
            <span className="auth-user-name">{authState.user.name || authState.user.email}</span>
            <button className="btn-auth btn-logout" onClick={handleLogout}>
              Sign out
            </button>
          </div>
        ) : (
          <button className="btn-auth btn-login" onClick={login}>
            Sign in with Google
          </button>
        )}
      </div>
    </header>
  );
}