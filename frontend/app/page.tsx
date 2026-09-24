import Link from 'next/link';
import ScrollExpand from '../components/ui/ScrollExpand';
import { Shield, Brain, Zap, Activity, Users, Video, ChevronRight, Lock, BellRing } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="bg-ink-950 text-white min-h-screen selection:bg-cyan-500/30 selection:text-cyan-100">
      
      {/* Navigation Header */}
      <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 backdrop-blur-md bg-ink-950/70 border-b border-ink-800/50">
        <div className="font-bold text-xl flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
            <span className="text-cyan-500 font-mono text-sm">F.</span>
          </div>
          <span className="tracking-tight">FallGuard</span>
        </div>
        <nav className="flex gap-6 items-center">
          <Link href="#features" className="hidden md:block text-gray-400 hover:text-white text-sm font-medium transition-colors">
            Features
          </Link>
          <Link href="#how-it-works" className="hidden md:block text-gray-400 hover:text-white text-sm font-medium transition-colors">
            How it Works
          </Link>
          <Link href="/login" className="text-gray-300 hover:text-white text-sm font-medium transition-colors ml-4">
            Sign In
          </Link>
          <Link 
            href="/login" 
            className="bg-cyan-500 hover:bg-cyan-400 text-ink-950 px-5 py-2 rounded-lg text-sm font-bold transition-all shadow-[0_0_15px_rgba(6,182,212,0.3)] hover:shadow-[0_0_25px_rgba(6,182,212,0.5)]"
          >
            Get Started
          </Link>
        </nav>
      </header>

      <main>
        {/* ScrollExpand Hero Section */}
        <div style={{ height: '180vh' }}>
          <ScrollExpand 
            src="https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&q=80&w=2940&ixlib=rb-4.0.3" 
            title="Next-Gen Care"
            scrollHint="Scroll to explore"
            useWindowScroll
            startWidth={42}
            startHeight={58}
            startRadius={24}
            endRadius={0}
            mediaZoom={1.35}
            scrollDistance={1.2}
            holdDistance={0.35}
            smoothing={0.1}
            overlayScrim={0.75}
          >
            <div className="flex flex-col items-center justify-center max-w-4xl mx-auto gap-8 mt-16 px-4">
              <h2 className="text-5xl md:text-7xl font-bold tracking-tight text-white drop-shadow-lg text-center leading-tight">
                Detect falls before <br className="hidden md:block" /> 
                <span className="text-cyan-400">they become emergencies.</span>
              </h2>
              <p className="text-xl md:text-2xl text-gray-300 font-medium drop-shadow-md text-center max-w-2xl leading-relaxed">
                The frame opens up as you scroll and hands the whole stage to our advanced computer vision algorithms. 
                Real-time, privacy-preserving fall detection at scale.
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4 mt-8">
                <Link 
                  href="/login" 
                  className="bg-white hover:bg-gray-100 text-ink-950 px-8 py-4 rounded-xl text-lg font-bold transition-transform hover:scale-105 flex items-center justify-center gap-2"
                >
                  Enter Dashboard <ChevronRight className="w-5 h-5" />
                </Link>
                <Link 
                  href="#features" 
                  className="bg-ink-900/50 hover:bg-ink-800/80 backdrop-blur-sm border border-ink-700 text-white px-8 py-4 rounded-xl text-lg font-bold transition-all flex items-center justify-center"
                >
                  Learn More
                </Link>
              </div>
            </div>
          </ScrollExpand>
        </div>
        
        {/* Core Value Props (Features) */}
        <section id="features" className="py-32 px-6 bg-ink-950 relative overflow-hidden">
          {/* Subtle background glow */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-cyan-500/5 rounded-full blur-[120px] pointer-events-none"></div>
          
          <div className="max-w-6xl mx-auto relative z-10">
            <div className="text-center mb-20">
              <h2 className="text-sm font-bold tracking-widest text-cyan-500 uppercase mb-3">Why FallGuard?</h2>
              <h3 className="text-4xl md:text-5xl font-bold text-white tracking-tight">Built for modern healthcare.</h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* Feature 1 */}
              <div className="bg-ink-900/40 border border-ink-800/60 p-8 rounded-3xl hover:bg-ink-900 transition-colors group">
                <div className="w-14 h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Shield className="text-cyan-400 w-7 h-7" />
                </div>
                <h4 className="text-2xl font-bold text-white mb-3">Privacy First</h4>
                <p className="text-gray-400 leading-relaxed">
                  Our models process streams locally or via secure channels. Video is never permanently recorded unless explicitly authorized, protecting patient dignity.
                </p>
              </div>
              
              {/* Feature 2 */}
              <div className="bg-ink-900/40 border border-ink-800/60 p-8 rounded-3xl hover:bg-ink-900 transition-colors group">
                <div className="w-14 h-14 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Brain className="text-purple-400 w-7 h-7" />
                </div>
                <h4 className="text-2xl font-bold text-white mb-3">High Accuracy AI</h4>
                <p className="text-gray-400 leading-relaxed">
                  Leveraging dual CNN-LSTM architectures for robust spatio-temporal detection. It understands complex movements, dramatically minimizing false positives.
                </p>
              </div>
              
              {/* Feature 3 */}
              <div className="bg-ink-900/40 border border-ink-800/60 p-8 rounded-3xl hover:bg-ink-900 transition-colors group">
                <div className="w-14 h-14 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Zap className="text-orange-400 w-7 h-7" />
                </div>
                <h4 className="text-2xl font-bold text-white mb-3">Sub-second Alerts</h4>
                <p className="text-gray-400 leading-relaxed">
                  Low latency inference ensures caregivers are notified immediately when a fall event is confirmed, reducing critical response times.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how-it-works" className="py-24 px-6 bg-[#060606] border-y border-ink-900">
          <div className="max-w-6xl mx-auto">
            <div className="flex flex-col md:flex-row items-center gap-16">
              <div className="flex-1 space-y-8">
                <div>
                  <h2 className="text-sm font-bold tracking-widest text-cyan-500 uppercase mb-3">Seamless Workflow</h2>
                  <h3 className="text-3xl md:text-4xl font-bold text-white tracking-tight">How FallGuard protects your facility</h3>
                </div>
                
                <div className="space-y-6">
                  <div className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className="w-10 h-10 rounded-full bg-ink-900 border border-ink-700 flex items-center justify-center text-white font-bold shrink-0">1</div>
                      <div className="w-px h-full bg-ink-800 my-2"></div>
                    </div>
                    <div className="pb-6">
                      <h4 className="text-xl font-bold text-white mb-1 flex items-center gap-2"><Video className="w-5 h-5 text-gray-400"/> Connect Cameras</h4>
                      <p className="text-gray-400">Securely ingest RTSP streams from your existing hardware infrastructure. No proprietary cameras required.</p>
                    </div>
                  </div>
                  
                  <div className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className="w-10 h-10 rounded-full bg-ink-900 border border-ink-700 flex items-center justify-center text-white font-bold shrink-0">2</div>
                      <div className="w-px h-full bg-ink-800 my-2"></div>
                    </div>
                    <div className="pb-6">
                      <h4 className="text-xl font-bold text-white mb-1 flex items-center gap-2"><Activity className="w-5 h-5 text-gray-400"/> Continuous Inference</h4>
                      <p className="text-gray-400">Our machine learning models continuously analyze skeletal poses and temporal changes in real-time, safely on edge or secure cloud.</p>
                    </div>
                  </div>
                  
                  <div className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className="w-10 h-10 rounded-full bg-cyan-500 flex items-center justify-center text-ink-950 font-bold shrink-0 shadow-[0_0_15px_rgba(6,182,212,0.4)]">3</div>
                    </div>
                    <div>
                      <h4 className="text-xl font-bold text-white mb-1 flex items-center gap-2"><BellRing className="w-5 h-5 text-cyan-400"/> Actionable Alerts</h4>
                      <p className="text-gray-400">Caregivers instantly receive a high-priority alert on the dashboard with incident confidence and location, enabling rapid response.</p>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Abstract Visual / Mockup */}
              <div className="flex-1 w-full bg-ink-900/50 border border-ink-800 rounded-3xl p-6 relative overflow-hidden min-h-[400px] flex items-center justify-center shadow-2xl">
                 <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/10 rounded-full blur-[80px]"></div>
                 <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-500/10 rounded-full blur-[80px]"></div>
                 
                 {/* Fake dashboard snippet */}
                 <div className="w-full max-w-sm bg-ink-950 border border-ink-800 rounded-2xl p-4 shadow-xl z-10 space-y-4">
                    <div className="flex justify-between items-center mb-2">
                      <div className="font-bold flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-warning animate-pulse"></span> Needs Attention</div>
                      <span className="text-xs bg-ink-900 text-gray-400 px-2 py-1 rounded">Live</span>
                    </div>
                    
                    <div className="bg-[#121212] border border-warning/30 p-3 rounded-xl flex flex-col gap-2">
                      <div className="flex justify-between">
                        <span className="font-semibold text-white">Room 302</span>
                        <span className="text-xs bg-error text-white px-1.5 py-0.5 rounded font-bold">94% Conf.</span>
                      </div>
                      <span className="text-xs text-gray-400">Camera 4 • Just now</span>
                      <div className="h-1 w-full bg-ink-800 rounded-full overflow-hidden mt-1">
                        <div className="h-full bg-error w-[94%]"></div>
                      </div>
                    </div>
                    
                    <div className="bg-[#121212] border border-ink-800 p-3 rounded-xl flex flex-col gap-2 opacity-50">
                      <div className="flex justify-between">
                        <span className="font-semibold text-white">Hallway B</span>
                        <span className="text-xs bg-warning text-ink-950 px-1.5 py-0.5 rounded font-bold">Pending</span>
                      </div>
                      <span className="text-xs text-gray-400">Camera 12 • 2m ago</span>
                    </div>
                 </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-32 px-6 bg-ink-950 text-center relative overflow-hidden">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[500px] bg-gradient-to-r from-cyan-500/10 to-blue-600/10 rounded-[100%] blur-[100px] pointer-events-none"></div>
          
          <div className="max-w-3xl mx-auto relative z-10 flex flex-col items-center gap-8">
            <h2 className="text-4xl md:text-6xl font-bold tracking-tight text-white">
              Ready to elevate your facility's safety?
            </h2>
            <p className="text-xl text-gray-400">
              Join leading healthcare providers using FallGuard to protect their residents with state-of-the-art AI.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 mt-4">
              <Link 
                href="/login" 
                className="bg-cyan-500 hover:bg-cyan-400 text-ink-950 px-10 py-4 rounded-xl text-lg font-bold transition-transform hover:scale-105 shadow-[0_0_20px_rgba(6,182,212,0.4)]"
              >
                Access Dashboard
              </Link>
            </div>
          </div>
        </section>
      </main>
      
      <footer className="border-t border-ink-800 py-12 px-8 bg-[#040404]">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
          <div className="md:col-span-2 space-y-4">
            <div className="font-bold text-xl flex items-center gap-2 text-white">
              <span className="text-cyan-500 font-mono">F.</span>
              <span>FallGuard</span>
            </div>
            <p className="text-sm text-gray-500 max-w-sm">
              Advanced computer vision solutions for healthcare facilities. We build technology that preserves privacy while saving lives.
            </p>
          </div>
          <div>
            <h4 className="text-white font-bold mb-4">Product</h4>
            <ul className="space-y-2 text-sm text-gray-500">
              <li><a href="#" className="hover:text-cyan-400 transition-colors">Core AI Engine</a></li>
              <li><a href="#" className="hover:text-cyan-400 transition-colors">Hardware Integration</a></li>
              <li><a href="#" className="hover:text-cyan-400 transition-colors">Security & Privacy</a></li>
              <li><a href="#" className="hover:text-cyan-400 transition-colors">Pricing</a></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-bold mb-4">Company</h4>
            <ul className="space-y-2 text-sm text-gray-500">
              <li><a href="#" className="hover:text-cyan-400 transition-colors">About Us</a></li>
              <li><a href="#" className="hover:text-cyan-400 transition-colors">Careers</a></li>
              <li><a href="#" className="hover:text-cyan-400 transition-colors">Contact Support</a></li>
              <li><a href="#" className="hover:text-cyan-400 transition-colors">System Status</a></li>
            </ul>
          </div>
        </div>
        <div className="max-w-6xl mx-auto pt-8 border-t border-ink-900 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-gray-600">
          <div>&copy; {new Date().getFullYear()} FallGuard Systems Inc. All rights reserved.</div>
          <div className="flex gap-6">
            <a href="#" className="hover:text-gray-300 transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-gray-300 transition-colors">Terms of Service</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
