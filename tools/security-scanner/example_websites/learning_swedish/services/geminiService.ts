
import { GoogleGenAI, Type } from "@google/genai";
import { SwedishWord } from "../types";

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY || '' });

export const getDailyWord = async (): Promise<SwedishWord> => {
  const response = await ai.models.generateContent({
    model: 'gemini-3-flash-preview',
    contents: 'Generate a common Swedish word of the day with its English translation and grammatical details.',
    config: {
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.OBJECT,
        properties: {
          word: { type: Type.STRING },
          translation: { type: Type.STRING },
          pronunciation: { type: Type.STRING },
          type: { type: Type.STRING },
          gender: { type: Type.STRING, enum: ['en', 'ett'] },
          pluralForm: { type: Type.STRING },
          definiteForm: { type: Type.STRING },
          conjugations: { type: Type.ARRAY, items: { type: Type.STRING } },
          exampleSentence: { type: Type.STRING },
          exampleTranslation: { type: Type.STRING },
          usageNote: { type: Type.STRING }
        },
        required: ["word", "translation", "type", "exampleSentence"]
      }
    }
  });

  return JSON.parse(response.text) as SwedishWord;
};

export const translateText = async (text: string): Promise<SwedishWord | string> => {
  // If text is a single word, return structured data. Otherwise, return plain string translation.
  const isSingleWord = text.trim().split(/\s+/).length === 1;

  if (isSingleWord) {
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: `Provide a detailed linguistic analysis for the Swedish word: "${text}". If it's English, translate to Swedish first.`,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            word: { type: Type.STRING },
            translation: { type: Type.STRING },
            pronunciation: { type: Type.STRING },
            type: { type: Type.STRING },
            gender: { type: Type.STRING, enum: ['en', 'ett'] },
            pluralForm: { type: Type.STRING },
            definiteForm: { type: Type.STRING },
            conjugations: { type: Type.ARRAY, items: { type: Type.STRING } },
            exampleSentence: { type: Type.STRING },
            exampleTranslation: { type: Type.STRING },
            usageNote: { type: Type.STRING }
          }
        }
      }
    });
    return JSON.parse(response.text) as SwedishWord;
  } else {
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: `Translate this text between Swedish and English: "${text}". Just provide the translation text.`
    });
    return response.text;
  }
};

export const createChatSession = () => {
  return ai.chats.create({
    model: 'gemini-3-pro-preview',
    config: {
      systemInstruction: 'You are a friendly Swedish language tutor. Your goal is to help the user practice Swedish. Always respond primarily in Swedish, but provide English translations in brackets for difficult words or complex sentences. Encourage the user and correct their grammar gently.'
    }
  });
};
