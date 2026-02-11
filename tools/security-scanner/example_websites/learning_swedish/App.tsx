
import React, { useState } from 'react';
import { AppTab } from './types';
import DailyCard from './components/DailyCard';
import Translator from './components/Translator';
import Chat from './components/Chat';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AppTab>(AppTab.DAILY);

  const renderContent = () => {
    switch (activeTab) {
      case AppTab.DAILY:
        return <DailyCard />;
      case AppTab.TRANSLATOR:
        return <Translator />;
      case AppTab.CHAT:
        return <Chat />;
      default:
        return <DailyCard />;
    }
  };

  const navItems = [
    { id: AppTab.DAILY, label: 'Dagens ord', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
    )},
    { id: AppTab.TRANSLATOR, label: 'Översätt', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" /></svg>
    )},
    { id: AppTab.CHAT, label: 'Prata', icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
    )},
  ];

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-[#f8fafc]">
      {/* Sidebar - Desktop */}
      <aside className="hidden md:flex flex-col w-64 swedish-blue h-screen sticky top-0 border-r border-white/10 shadow-xl z-10">
        <div className="p-8">
          <h1 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <span className="text-swedish-yellow text-3xl italic">S</span>venska Lär
          </h1>
          <p className="text-white/60 text-xs font-medium uppercase tracking-widest mt-1">Lär dig svenska</p>
        </div>

        <nav className="flex-1 px-4 py-8 space-y-2">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-4 px-4 py-4 rounded-xl font-bold transition-all ${
                activeTab === item.id 
                ? 'bg-swedish-yellow text-swedish-blue shadow-lg scale-[1.02]' 
                : 'text-white hover:bg-white/10'
              }`}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>

        <div className="p-6">
          <div className="bg-white/10 rounded-2xl p-4 border border-white/5">
            <p className="text-white/80 text-sm italic font-medium">"Lagom är bäst."</p>
            <p className="text-white/40 text-[10px] mt-1">- Swedish Proverb</p>
          </div>
        </div>
      </aside>

      {/* Header - Mobile */}
      <header className="md:hidden swedish-blue p-6 sticky top-0 z-20 shadow-md">
        <h1 className="text-xl font-black text-white tracking-tight text-center">
          <span className="text-swedish-yellow italic">S</span>venska Lär
        </h1>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-4 md:p-12 pb-32 md:pb-12">
        <div className="max-w-4xl mx-auto animate-in fade-in duration-700">
          {renderContent()}
        </div>
      </main>

      {/* Bottom Nav - Mobile */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 swedish-blue border-t border-white/10 px-6 py-4 flex justify-between items-center z-20 shadow-[0_-4px_20px_rgba(0,0,0,0.1)]">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`flex flex-col items-center gap-1 px-4 py-1 rounded-xl transition-all ${
              activeTab === item.id 
              ? 'text-swedish-yellow scale-110' 
              : 'text-white/50'
            }`}
          >
            {item.icon}
            <span className="text-[10px] font-bold uppercase tracking-wider">{item.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
};

export default App;
