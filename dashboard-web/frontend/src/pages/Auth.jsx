import { useState } from 'react'
import { KeyRound, Mail, User, ShieldCheck } from 'lucide-react'

export default function Auth({ onLogin }) {
  const [isSignUp, setIsSignUp] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    if (!email || !password || (isSignUp && !name)) return

    setLoading(true)
    setTimeout(() => {
      // Complete mock auth login/signup pipeline
      onLogin({
        email,
        name: isSignUp ? name : (email === 'dev@llmops.com' ? 'Priyanshi Choudhary' : 'Priyanshi Choudhary'),
        token: 'mock-jwt-token-xyz'
      })
      setLoading(false)
    }, 800)
  }

  function handleDemoBypass() {
    setLoading(true)
    setTimeout(() => {
      onLogin({
        email: 'dev@llmops.com',
        name: 'Priyanshi Choudhary',
        token: 'mock-jwt-token-xyz'
      })
      setLoading(false)
    }, 450)
  }

  return (
    <div className="min-h-screen bg-[#06070A] flex items-center justify-center px-4 font-sans selection:bg-[#5B7FFF]/30">
      <div className="absolute inset-0 bg-radial-gradient from-[#5B7FFF]/5 to-transparent opacity-50 pointer-events-none" />
      
      <div className="w-full max-w-md bg-[#12161F] border border-[#222938] rounded-2xl shadow-2xl p-8 relative overflow-hidden space-y-6">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[#5B7FFF] via-[#06B6D4] to-[#22C55E]" />

        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-full bg-[#5B7FFF]/10 border border-[#5B7FFF]/25 flex items-center justify-center mx-auto text-[#5B7FFF] mb-3">
            <ShieldCheck size={26} />
          </div>
          <h2 className="text-xl font-extrabold text-white tracking-tight">
            {isSignUp ? 'Create your account' : 'Sign in to LLMops Workspace'}
          </h2>
          <p className="text-xs text-gray-500 font-medium leading-normal">
            Continuous regression detection and semantic drift monitoring.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {isSignUp && (
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider block">Full Name</label>
              <div className="relative">
                <User size={14} className="absolute left-3 top-3 text-gray-500" />
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Priyanshi Choudhary"
                  className="w-full bg-[#0D1117] border border-[#222938] rounded-lg pl-9 pr-3 py-2 text-sm text-gray-200 placeholder:text-gray-650 outline-none focus:border-[#5B7FFF]/40 transition-colors"
                />
              </div>
            </div>
          )}

          <div className="space-y-1">
            <label className="text-[10px] font-bold text-gray-555 uppercase tracking-wider block">Email Address</label>
            <div className="relative">
              <Mail size={14} className="absolute left-3 top-3 text-gray-500" />
              <input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="dev@llmops.com"
                className="w-full bg-[#0D1117] border border-[#222938] rounded-lg pl-9 pr-3 py-2 text-sm text-gray-200 placeholder:text-gray-650 outline-none focus:border-[#5B7FFF]/40 transition-colors"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-bold text-gray-555 uppercase tracking-wider block">Password</label>
            <div className="relative">
              <KeyRound size={14} className="absolute left-3 top-3 text-gray-500" />
              <input
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-[#0D1117] border border-[#222938] rounded-lg pl-9 pr-3 py-2 text-sm text-gray-200 placeholder:text-gray-650 outline-none focus:border-[#5B7FFF]/40 transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#5B7FFF] hover:bg-[#5B7FFF]/90 text-white rounded-lg py-2.5 text-xs font-bold transition-all disabled:opacity-50 tracking-wide mt-2"
          >
            {loading ? 'Processing…' : isSignUp ? 'CREATE ACCOUNT' : 'SIGN IN'}
          </button>
        </form>

        <div className="relative flex py-1 items-center">
          <div className="flex-grow border-t border-[#222938]/60" />
          <span className="flex-shrink mx-3 text-[10px] text-gray-555 uppercase tracking-wider font-bold">Or</span>
          <div className="flex-grow border-t border-[#222938]/60" />
        </div>

        <button
          onClick={handleDemoBypass}
          disabled={loading}
          className="w-full bg-[#0D1117] hover:bg-[#0D1117]/80 border border-[#222938] hover:border-[#5B7FFF]/40 text-[#A0AEC0] hover:text-white rounded-lg py-2.5 text-xs font-bold transition-colors disabled:opacity-50"
        >
          {loading ? 'Please wait…' : 'BYPASS WITH DEMO ACCOUNT (PC)'}
        </button>

        <div className="text-center pt-2">
          <button
            onClick={() => setIsSignUp(!isSignUp)}
            className="text-xs text-[#5B7FFF] hover:underline font-semibold"
          >
            {isSignUp ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
          </button>
        </div>
      </div>
    </div>
  )
}
