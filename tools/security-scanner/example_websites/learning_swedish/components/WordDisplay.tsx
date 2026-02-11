
import React from 'react';
import { SwedishWord } from '../types';

interface WordDisplayProps {
  data: SwedishWord;
}

const WordDisplay: React.FC<WordDisplayProps> = ({ data }) => {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-4xl font-bold text-swedish-blue">{data.word}</h2>
          <p className="text-lg text-gray-500 italic mt-1">/{data.pronunciation}/</p>
        </div>
        <div className="flex flex-col items-end">
          <span className="px-3 py-1 bg-blue-50 text-swedish-blue rounded-full text-sm font-semibold border border-blue-100">
            {data.type}
          </span>
          {data.gender && (
            <span className={`mt-2 px-3 py-1 rounded-full text-xs font-bold uppercase ${data.gender === 'en' ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'}`}>
              {data.gender}
            </span>
          )}
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Translation</h3>
          <p className="text-xl text-gray-800 font-medium">{data.translation}</p>
        </div>

        {(data.pluralForm || data.definiteForm) && (
          <div className="grid grid-cols-2 gap-4">
            {data.definiteForm && (
              <div>
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Definite</h3>
                <p className="text-gray-700">{data.definiteForm}</p>
              </div>
            )}
            {data.pluralForm && (
              <div>
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Plural</h3>
                <p className="text-gray-700">{data.pluralForm}</p>
              </div>
            )}
          </div>
        )}

        {data.conjugations && data.conjugations.length > 0 && (
          <div>
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Conjugations</h3>
            <div className="flex flex-wrap gap-2">
              {data.conjugations.map((c, i) => (
                <span key={i} className="bg-gray-50 px-2 py-1 rounded border border-gray-200 text-sm text-gray-600">
                  {c}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="pt-4 border-t border-gray-50">
          <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Example</h3>
          <div className="bg-swedish-yellow/10 p-4 rounded-xl border-l-4 border-swedish-yellow">
            <p className="text-gray-800 font-medium italic">"{data.exampleSentence}"</p>
            <p className="text-gray-500 text-sm mt-1">{data.exampleTranslation}</p>
          </div>
        </div>

        {data.usageNote && (
          <div className="bg-blue-50 p-3 rounded-lg text-sm text-blue-800 border border-blue-100 italic">
            <strong>Note:</strong> {data.usageNote}
          </div>
        )}
      </div>
    </div>
  );
};

export default WordDisplay;
