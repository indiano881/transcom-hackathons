
export interface SwedishWord {
  word: string;
  translation: string;
  pronunciation: string;
  type: string; // noun, verb, adjective, etc.
  gender?: 'en' | 'ett'; // for nouns
  pluralForm?: string;
  definiteForm?: string;
  conjugations?: string[]; // for verbs
  exampleSentence: string;
  exampleTranslation: string;
  usageNote?: string;
}

export interface ChatMessage {
  role: 'user' | 'model';
  text: string;
  timestamp: Date;
}

export enum AppTab {
  DAILY = 'daily',
  TRANSLATOR = 'translator',
  CHAT = 'chat'
}
