
import React, { useState } from 'react';
import { translateText } from '../services/geminiService';
import { SwedishWord } from '../types';
import WordDisplay from './WordDisplay';

const Translator: React.FC = () => {
  const [input, setInput] = useState('');
  const [result, setResult] = useState<SwedishWord | string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleTranslate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    setLoading(true);
    try {
      const translationResult = await translateText(input);
      setResult(translationResult);
    } catch (error) {
      console.error("Translation failed:", error);
      setResult("Error occurred during translation.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-8">
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <form onSubmit={handleTranslate} className="space-y-4">
          <label className="block text-sm font-semibold text-gray-600 mb-1">
            Översätt (Translate)
          </label>
          <div className="relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Enter a Swedish word for grammar details, or a sentence to translate..."
              className="w-full h-32 p-4 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-swedish-blue focus:border-transparent outline-none transition-all resize-none text-gray-900"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="absolute bottom-4 right-4 bg-swedish-blue text-white px-6 py-2 rounded-lg font-bold shadow-md hover:bg-opacity-90 disabled:bg-gray-300 disabled:shadow-none transition-all"
            >
              {loading ? '...' : 'Översätt'}
            </button>
          </div>
        </form>
      </div>

      {result && (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
          {typeof result === 'string' ? (
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Result</h3>
              <p className="text-2xl text-gray-800 font-medium">{result}</p>
            </div>
          ) : (
            <WordDisplay data={result} />
          )}
        </div>
      )}
    </div>
  );
};

export default Translator;
