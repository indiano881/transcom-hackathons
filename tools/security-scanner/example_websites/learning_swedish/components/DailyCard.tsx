
import React, { useEffect, useState } from 'react';
import { getDailyWord } from '../services/geminiService';
import { SwedishWord } from '../types';
import WordDisplay from './WordDisplay';

const DailyCard: React.FC = () => {
  const [word, setWord] = useState<SwedishWord | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchWord = async () => {
      try {
        const data = await getDailyWord();
        setWord(data);
      } catch (error) {
        console.error("Failed to fetch word:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchWord();
  }, []);

  if (loading) {
    return (
      <div className="w-full max-w-xl mx-auto p-12 flex flex-col items-center justify-center space-y-4">
        <div className="w-12 h-12 border-4 border-swedish-blue border-t-transparent rounded-full animate-spin"></div>
        <p className="text-gray-500 font-medium">Laddar dagens ord...</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-xl mx-auto space-y-6">
      <div className="flex items-center gap-3 px-2">
        <div className="w-8 h-8 rounded-full swedish-blue flex items-center justify-center">
          <span className="text-swedish-yellow text-xs font-bold">SV</span>
        </div>
        <h2 className="text-2xl font-bold text-gray-800">Dagens ord</h2>
      </div>
      {word && <WordDisplay data={word} />}
    </div>
  );
};

export default DailyCard;
