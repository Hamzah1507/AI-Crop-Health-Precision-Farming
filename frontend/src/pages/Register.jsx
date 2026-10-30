import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api';
import { apiError } from '../utils/apiError';
import AuthShell, { AuthField, AuthAlert, AuthSubmit, AuthSwitch } from '../components/AuthShell';
import { FiUser, FiMail, FiLock, FiUserPlus } from 'react-icons/fi';

export default function Register() {
  const [formData, setFormData] = useState({ username: '', email: '', password: '', confirmPassword: '' });
  const [error, setError] = useState('');                 // server-side errors (for example "Username already registered")
  const [fieldErrors, setFieldErrors] = useState({});     // client-side validation, shown next to the field
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
    if (fieldErrors[name]) setFieldErrors({ ...fieldErrors, [name]: undefined });
  };

  const fail = (field, message) => {
    setFieldErrors({ [field]: message });
    document.getElementById(field)?.focus();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});

    if (formData.password !== formData.confirmPassword) {
      fail('confirmPassword', 'Passwords do not match');
      return;
    }
    if (formData.password.length < 6) {
      fail('password', 'Password must be at least 6 characters');
      return;
    }

    setLoading(true);
    try {
      // The server always creates farmer accounts; the role sent here is ignored.
      await authAPI.register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        role: 'farmer',
      });
      navigate('/login');
    } catch (err) {
      setError(apiError(err, 'Registration failed. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const common = { onChange: handleChange, required: true };

  return (
    <AuthShell title="Create your account" subtitle="Join CropHealth AI to manage your farm data.">
      <AuthAlert>{error}</AuthAlert>

      <form onSubmit={handleSubmit} className="space-y-4">
        <AuthField id="username" name="username" label="Username" icon={FiUser} type="text" value={formData.username}
          placeholder="Choose a username" autoComplete="username" autoCapitalize="none" spellCheck={false} {...common} />

        <AuthField id="email" name="email" label="Email" icon={FiMail} type="email" value={formData.email}
          placeholder="Enter your email" autoComplete="email" autoCapitalize="none" spellCheck={false} {...common} />

        <AuthField id="password" name="password" label="Password" icon={FiLock} type="password" value={formData.password}
          placeholder="At least 6 characters" autoComplete="new-password" error={fieldErrors.password} {...common} />

        <AuthField id="confirmPassword" name="confirmPassword" label="Confirm password" icon={FiLock} type="password" value={formData.confirmPassword}
          placeholder="Repeat your password" autoComplete="new-password" error={fieldErrors.confirmPassword} {...common} />

        <div className="pt-2">
          <AuthSubmit loading={loading} loadingLabel="Creating account..." icon={FiUserPlus}>Create account</AuthSubmit>
        </div>
      </form>

      <AuthSwitch prompt="Already have an account?" to="/login" linkLabel="Sign in" />
    </AuthShell>
  );
}
