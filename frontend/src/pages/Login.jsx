import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/auth';
import { authAPI } from '../services/api';
import { apiError } from '../utils/apiError';
import AuthShell, { AuthField, AuthAlert, AuthSubmit, AuthSwitch } from '../components/AuthShell';
import { FiUser, FiLock, FiLogIn } from 'react-icons/fi';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await authAPI.login({ username, password });
      login(res.data);
      navigate('/dashboard');
    } catch (err) {
      setError(apiError(err, 'Login failed. Please check your credentials.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Welcome back" subtitle="Sign in to your CropHealth AI account.">
      <AuthAlert>{error}</AuthAlert>

      <form onSubmit={handleSubmit} className="space-y-5">
        <AuthField id="username" label="Username" icon={FiUser} type="text" value={username}
          onChange={(e) => setUsername(e.target.value)} placeholder="Enter your username" required
          autoComplete="username" autoCapitalize="none" spellCheck={false}
          invalid={!!error} describedBy={error ? 'auth-error' : undefined} />

        <AuthField id="password" label="Password" icon={FiLock} type="password" value={password}
          onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" required
          autoComplete="current-password"
          invalid={!!error} describedBy={error ? 'auth-error' : undefined} />

        <div className="pt-1">
          <AuthSubmit loading={loading} loadingLabel="Signing in..." icon={FiLogIn}>Sign in</AuthSubmit>
        </div>
      </form>

      <AuthSwitch prompt="Don't have an account?" to="/register" linkLabel="Register" />
    </AuthShell>
  );
}
