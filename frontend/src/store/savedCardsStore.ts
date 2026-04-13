import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { AnalysisResult, ComparisonResult } from '../types';

export type SavedCardType = 'analysis' | 'comparison';

export interface SavedCard {
  id: string;
  type: SavedCardType;
  title: string;
  data: AnalysisResult | ComparisonResult;
  timestamp: number;
  tags?: string[];
}

interface SavedCardsState {
  cards: SavedCard[];
  searchQuery: string;
  selectedType: SavedCardType | 'all';

  // Actions
  saveCard: (card: SavedCard) => void;
  removeCard: (id: string) => void;
  isCardSaved: (id: string) => boolean;
  setSearchQuery: (query: string) => void;
  setSelectedType: (type: SavedCardType | 'all') => void;
  getFilteredCards: () => SavedCard[];

  // Persistence
  loadCards: () => void;
  saveToStorage: () => void;
}

const STORAGE_KEY = 'spottruth_saved_cards';

export const useSavedCardsStore = create<SavedCardsState>()(
  devtools(
    (set, get) => ({
      cards: [],
      searchQuery: '',
      selectedType: 'all',

      saveCard: (card) => {
        const { cards } = get();
        // Check if already exists
        const exists = cards.some((c) => c.id === card.id);
        if (exists) {
          // Update existing
          set({
            cards: cards.map((c) => (c.id === card.id ? { ...card, timestamp: Date.now() } : c)),
          });
        } else {
          // Add new
          set({ cards: [...cards, card] });
        }
        get().saveToStorage();
      },

      removeCard: (id) => {
        const { cards } = get();
        set({ cards: cards.filter((c) => c.id !== id) });
        get().saveToStorage();
      },

      isCardSaved: (id) => {
        const { cards } = get();
        return cards.some((c) => c.id === id);
      },

      setSearchQuery: (query) => set({ searchQuery: query }),

      setSelectedType: (type) => set({ selectedType: type }),

      getFilteredCards: () => {
        const { cards, searchQuery, selectedType } = get();
        return cards.filter((card) => {
          const matchesType = selectedType === 'all' || card.type === selectedType;
          const matchesSearch =
            !searchQuery ||
            card.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            card.tags?.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()));
          return matchesType && matchesSearch;
        });
      },

      loadCards: () => {
        try {
          const saved = localStorage.getItem(STORAGE_KEY);
          if (saved) {
            const cards = JSON.parse(saved);
            set({ cards });
          }
        } catch (e) {
          console.error('加载保存的卡片失败:', e);
        }
      },

      saveToStorage: () => {
        try {
          const { cards } = get();
          localStorage.setItem(STORAGE_KEY, JSON.stringify(cards));
        } catch (e) {
          console.error('保存卡片失败:', e);
        }
      },
    }),
    { name: 'saved-cards-store' }
  )
);
