import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Loader2, Eye, EyeOff } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';
const Login = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    if (!email || !password) {
      setError('Please enter both email and password.');
      return;
    }
    setIsLoading(true);
    
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    
    setIsLoading(false);
    
    if (error) {
      setError(error.message || 'Invalid credentials. Please try again.');
    } else {
      navigate('/dashboard');
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* ── Left Branding Panel (desktop only) ── */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-900 flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-indigo-600">
            <ShieldCheck className="text-white" size={22} />
          </div>
          <div>
            <p className="text-white font-semibold text-base leading-none">Legal Metrology</p>
            <p className="text-slate-400 text-xs mt-0.5">Compliance System</p>
          </div>
        </div>

        <div>
          <h1 className="text-4xl font-bold text-white leading-tight">
            Enforcement-grade<br />
            label compliance<br />
            at scale.
          </h1>
          <p className="mt-4 text-slate-400 text-base leading-relaxed max-w-sm">
            AI-powered scanning and rule verification for Legal Metrology (Packaged Commodities) Rules, 2011.
          </p>
        </div>

        <div className="text-slate-600 text-xs">
          Ministry of Consumer Affairs, Food &amp; Public Distribution
        </div>
      </div>

      {/* ── Right Form Panel ── */}
      <div className="flex-1 flex flex-col justify-center bg-white px-6 py-12 lg:px-16">
        {/* Mobile logo */}
        <div className="flex items-center gap-3 mb-10 lg:hidden">
          <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-indigo-600">
            <ShieldCheck className="text-white" size={20} />
          </div>
          <div>
            <p className="text-slate-900 font-semibold text-sm leading-none">Legal Metrology</p>
            <p className="text-slate-500 text-xs mt-0.5">Compliance System</p>
          </div>
        </div>

        <div className="max-w-sm w-full mx-auto">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-900">Sign in to your account</h2>
            <p className="mt-2 text-sm text-slate-500">Enter your credentials to access the enforcement portal.</p>
          </div>

          <form className="space-y-5" onSubmit={handleLogin}>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1.5">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="inspector@gov.in"
                className="form-input"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="form-input pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-2.5 bg-rose-50 border border-rose-200 rounded-lg p-3.5">
                <div className="w-1.5 h-1.5 rounded-full bg-rose-500 mt-1.5 flex-shrink-0" />
                <p className="text-sm text-rose-700">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full py-2.5 mt-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="animate-spin mr-2 h-4 w-4" />
                  Authenticating...
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          <div className="mt-6 p-3.5 bg-slate-50 rounded-lg ring-1 ring-slate-200">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Demo credentials</p>
            <p className="text-xs text-slate-600 font-mono">inspector@gov.in / password</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
