import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  Message,
  Product,
  ProductCache,
  AnalysisResult,
  IntentData,
} from '../types';
import * as api from '../services/api';
import * as crawler from '../services/crawler';

const generateId = () => Math.random().toString(36).substring(2, 9);

interface ConversationState {
  sessionId: string;
  currentProduct: string;
  messages: Message[];
  conversationHistory: { role: string; content: string }[];
  productCache: Map<string, ProductCache>;
  isLoading: boolean;
  loadingText: string;
  pendingCrawlData: {
    brand: string;
    product: string;
    needXhs: boolean;
    needHeimao: boolean;
    needTaobao: boolean;
    taobaoComments: string[];
    xhsNotes: string[];
    heimaoComplaints: string[];
  } | null;

  setLoading: (loading: boolean, text?: string) => void;
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  sendMessage: (text: string) => Promise<void>;
  selectProduct: (product: Product) => Promise<void>;
  analyzeProduct: (brand: string, product: string, needXhs: boolean, needHeimao: boolean, needTaobao: boolean) => Promise<void>;
  handleAnalyzeIntent: (intentData: IntentData) => Promise<void>;
  handleXiaohongshuIntent: (intentData: IntentData) => Promise<void>;
  handleHeimaoIntent: (intentData: IntentData) => Promise<void>;
  handleCompareIntent: (intentData: IntentData) => Promise<void>;
  clearConversation: () => void;
  getProductCache: (productName: string) => ProductCache | undefined;
  setProductCache: (cache: ProductCache) => void;
}

const createInitialState = () => ({
  sessionId: generateId(),
  currentProduct: '',
  messages: [],
  conversationHistory: [],
  productCache: new Map<string, ProductCache>(),
  isLoading: false,
  loadingText: '',
  pendingCrawlData: null,
});

export const useConversationStore = create<ConversationState>()(
  devtools(
    (set, get) => ({
      ...createInitialState(),

      setLoading: (loading, text = '') => {
        set({ isLoading: loading, loadingText: text });
      },

      addMessage: (message) => {
        const newMessage: Message = {
          ...message,
          id: generateId(),
          timestamp: Date.now(),
        };
        set((state) => ({ messages: [...state.messages, newMessage] }));
      },

      updateMessage: (id, updates) => {
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === id ? { ...msg, ...updates } : msg
          ),
        }));
      },

      sendMessage: async (text: string) => {
        const { addMessage, conversationHistory, currentProduct, productCache } = get();

        addMessage({
          role: 'user',
          content: text,
          type: 'text',
        });

        addMessage({
          role: 'assistant',
          content: '思考中...',
          type: 'loading',
        });

        const loadingId = get().messages[get().messages.length - 1].id;

        try {
          const analyzedPlatforms = productCache.get(currentProduct)?.analyzedPlatforms || [];
          const intentData = await api.parseIntent({
            userInput: text,
            conversationHistory: conversationHistory.slice(-6),
            currentProduct,
            analyzedPlatforms,
          });

          get().updateMessage(loadingId, {
            type: 'text',
            content: intentData.response,
          });

          set((prevState) => ({
            conversationHistory: [
              ...prevState.conversationHistory,
              { role: 'user', content: text },
              { role: 'assistant', content: intentData.response },
            ],
          }));

          if (intentData.clarificationNeeded) {
            return;
          }

          switch (intentData.intent) {
            case 'analyze':
              await get().handleAnalyzeIntent(intentData);
              break;
            case 'compare':
              await get().handleCompareIntent(intentData);
              break;
            case 'search_xhs':
              await get().handleXiaohongshuIntent(intentData);
              break;
            case 'search_heimao':
              await get().handleHeimaoIntent(intentData);
              break;
          }
        } catch (error) {
          get().updateMessage(loadingId, {
            type: 'error',
            content: error instanceof Error ? error.message : '请求失败',
          });
        }
      },

      handleAnalyzeIntent: async (intentData: IntentData) => {
        const { brand, product, needXiaohongshu, needHeimao } = intentData;
        const needTaobao = intentData.needTaobao ?? !(needXiaohongshu || needHeimao);

        if (!product) {
          get().addMessage({
            role: 'assistant',
            content: '请告诉我你想分析什么商品，比如：德芙巧克力',
            type: 'text',
          });
          return;
        }

        await get().analyzeProduct(brand, product, needXiaohongshu, needHeimao, needTaobao);
      },

      analyzeProduct: async (brand: string, product: string, needXhs: boolean, needHeimao: boolean, needTaobao: boolean) => {
        const { addMessage, setLoading, setProductCache, getProductCache } = get();
        const productName = `${brand} ${product}`.trim();

        set(() => ({ currentProduct: productName }));
        setLoading(true, '分析中...');

        try {
          // 1. 检查缓存
          const cache = getProductCache(productName);
          const needCrawlTaobao = needTaobao && !cache?.taobaoComments.length;
          const needCrawlXhs = needXhs && !cache?.xiaohongshuNotes.length;
          const needCrawlHeimao = needHeimao && !cache?.heimaoComplaints.length;

          if (cache && !needCrawlTaobao && !needCrawlXhs && !needCrawlHeimao) {
            addMessage({
              role: 'assistant',
              content: '✅ 全部命中缓存，直接使用缓存数据...',
              type: 'text',
            });
          }

          // 2. 使用缓存数据作为基础
          let taobaoComments = cache?.taobaoComments || [];
          let xhsNotes = cache?.xiaohongshuNotes || [];
          let heimaoComplaints = cache?.heimaoComplaints || [];

          // 3. 爬取需要的平台数据
          if (needCrawlTaobao || needCrawlXhs || needCrawlHeimao) {
            addMessage({
              role: 'assistant',
              content: `🌐 需要爬取: 淘宝=${needCrawlTaobao}, 小红书=${needCrawlXhs}, 黑猫=${needCrawlHeimao}`,
              type: 'text',
            });

            // 如果需要淘宝，先显示商品选择
            if (needCrawlTaobao) {
              setLoading(true, '搜索淘宝商品...');
              const products = await crawler.searchTaobaoProducts({ brand, product, maxResults: 5 });

              if (products.length === 0) {
                addMessage({
                  role: 'assistant',
                  content: '⚠️ 未找到淘宝商品',
                  type: 'text',
                });
              } else {
                // 保存待处理数据，等待用户选择
                set({
                  pendingCrawlData: {
                    brand,
                    product,
                    needXhs: needCrawlXhs,
                    needHeimao: needCrawlHeimao,
                    needTaobao: false, // 淘宝需要用户选择后处理
                    taobaoComments: [],
                    xhsNotes: [],
                    heimaoComplaints: [],
                  },
                });

                addMessage({
                  role: 'assistant',
                  content: `📦 找到 ${products.length} 个商品，请选择要分析的商品：`,
                  type: 'product_select',
                  metadata: { products },
                });
                setLoading(false);
                return; // 等待用户选择
              }
            }

            // 爬取小红书
            if (needCrawlXhs) {
              setLoading(true, '📱 正在启动小红书爬取任务...');
              try {
                const keyword = productName;
                xhsNotes = await crawler.searchXiaohongshu(
                  keyword,
                  5,
                  (progress, message) => {
                    setLoading(true, `📱 ${message} (${progress}%)`);
                  }
                );
                addMessage({
                  role: 'assistant',
                  content: `✅ 获取 ${xhsNotes.length} 条小红书笔记`,
                  type: 'text',
                });
              } catch (e) {
                console.error('小红书爬取失败:', e);
                addMessage({
                  role: 'assistant',
                  content: `⚠️ 小红书爬取失败: ${e instanceof Error ? e.message : '未知错误'}`,
                  type: 'text',
                });
              }
            }

            // 爬取黑猫
            if (needCrawlHeimao) {
              setLoading(true, '⚠️ 获取黑猫投诉...');
              try {
                heimaoComplaints = await crawler.searchHeimao(brand || productName, 30);
                addMessage({
                  role: 'assistant',
                  content: `✅ 获取 ${heimaoComplaints.length} 条黑猫投诉`,
                  type: 'text',
                });
              } catch (e) {
                console.error('黑猫爬取失败:', e);
              }
            }
          }

          // 4. 检查是否有任何数据
          if (!taobaoComments.length && !xhsNotes.length && !heimaoComplaints.length) {
            addMessage({
              role: 'assistant',
              content: `❌ 未获取到 ${productName} 的任何数据`,
              type: 'error',
            });
            setLoading(false);
            return;
          }

          // 5. 品类分类
          setLoading(true, '🏷️ 商品分类...');
          let category: string;
          try {
            const classifyResult = await api.classifyProduct({ productName });
            category = classifyResult.category;
          } catch (e) {
            category = 'electronics';
          }

          // 6. 淘宝情感分析（如果有淘宝数据）
          let stats = { total: 0, positiveCount: 0, negativeCount: 0, sarcasmCount: 0, positiveRate: 0, negativeRate: 0 };
          let results: any[] = [];
          let summary = '';
          let advice = '';

          if (taobaoComments.length > 0) {
            setLoading(true, '🧠 正在进行淘宝评论情感分析...');
            try {
              const analyzeData = await api.analyzeComments({
                comments: taobaoComments,
                productName,
                category,
              });

              stats = {
                total: analyzeData.statistics.total,
                positiveCount: analyzeData.statistics.positive_count,
                negativeCount: analyzeData.statistics.negative_count,
                sarcasmCount: analyzeData.statistics.sarcasm_count,
                positiveRate: analyzeData.statistics.positive_rate,
                negativeRate: analyzeData.statistics.negative_rate,
              };
              results = analyzeData.results;

              // 生成总结
              setLoading(true, '📝 正在生成淘宝评论分析报告...');
              const summarizeData = await api.summarize({
                statistics: {
                  total: stats.total,
                  positive_rate: stats.positiveRate,
                  negative_rate: stats.negativeRate,
                  sarcasm_count: stats.sarcasmCount,
                },
                sampleComments: results.slice(0, 15).map((r) => ({
                  text: r.text,
                  sentiment: r.sentiment,
                  is_sarcasm: r.is_sarcasm,
                })),
              });
              summary = summarizeData.summary;
              advice = summarizeData.advice;
            } catch (e) {
              console.error('淘宝分析失败:', e);
            }
          }

          // 7. 小红书分析
          let xhsAnalysis: AnalysisResult['xiaohongshu'];
          if (xhsNotes.length > 0 && needXhs) {
            setLoading(true, '📱 正在分析小红书笔记...');
            try {
              const xhsData = await api.analyzeXiaohongshu({
                notes: xhsNotes.map((text) => ({ title: '', content: text, likes: 0 })),
                keyword: productName,
              });
              xhsAnalysis = {
                summary: xhsData.summary,
                keyPoints: xhsData.key_points,
                sentiment: xhsData.sentiment as 'mostly_positive' | 'mixed' | 'mostly_negative' | 'unknown',
              };
            } catch (e) {
              console.error('小红书分析失败:', e);
            }
          }

          // 8. 黑猫分析
          let heimaoAnalysis: AnalysisResult['heimao'];
          if (heimaoComplaints.length > 0 && needHeimao) {
            setLoading(true, '⚠️ 正在分析黑猫投诉...');
            try {
              const heimaoData = await api.analyzeHeimao({
                complaints: heimaoComplaints.map((text) => ({ title: '', content: text, status: '' })),
                brand: brand || productName,
              });
              heimaoAnalysis = {
                summary: heimaoData.summary,
                complaintTypes: heimaoData.complaint_types,
                severity: heimaoData.severity as 'high' | 'medium' | 'low' | 'unknown',
                recommendation: heimaoData.recommendation,
              };
            } catch (e) {
              console.error('黑猫分析失败:', e);
            }
          }

          // 9. 保存到缓存
          const analyzedPlatforms: string[] = [];
          if (taobaoComments.length) analyzedPlatforms.push('taobao');
          if (xhsNotes.length) analyzedPlatforms.push('xiaohongshu');
          if (heimaoComplaints.length) analyzedPlatforms.push('heimao');

          const newCache: ProductCache = {
            productName,
            brand,
            category,
            taobaoComments,
            xiaohongshuNotes: xhsNotes,
            heimaoComplaints,
            taobaoAnalysis: taobaoComments.length
              ? { stats, results, summary, advice }
              : null,
            xiaohongshuAnalysis: xhsAnalysis || null,
            heimaoAnalysis: heimaoAnalysis || null,
            analyzedPlatforms,
          };
          setProductCache(newCache);

          // 10. 展示结果
          const finalResult: AnalysisResult = {
            productName,
            category,
            statistics: stats,
            summary,
            advice,
            results,
            xiaohongshu: xhsAnalysis,
            heimao: heimaoAnalysis,
          };

          addMessage({
            role: 'assistant',
            content: '分析完成',
            type: 'analysis_report',
            metadata: { analysisResult: finalResult },
          });
        } catch (error) {
          addMessage({
            role: 'assistant',
            content: error instanceof Error ? error.message : '分析失败',
            type: 'error',
          });
        } finally {
          setLoading(false);
          set({ pendingCrawlData: null });
        }
      },

      selectProduct: async (product: Product) => {
        const { addMessage, setLoading, pendingCrawlData } = get();

        if (!pendingCrawlData) {
          addMessage({
            role: 'assistant',
            content: '❌ 选择商品失败：没有待处理的数据',
            type: 'error',
          });
          return;
        }

        const { brand, product: productName, needXhs, needHeimao } = pendingCrawlData;
        const fullProductName = `${brand} ${productName}`.trim();

        setLoading(true, '💬 获取淘宝评论...');

        try {
          const comments = await crawler.getTaobaoComments({
            url: product.url,
            brand,
            product: productName,
            maxCount: 50,
          });

          addMessage({
            role: 'assistant',
            content: `✅ 已选择: ${product.name}，获取到 ${comments.length} 条淘宝评论`,
            type: 'text',
          });

          // 继续分析流程（此时淘宝数据已经有了）
          const cache: ProductCache = {
            productName: fullProductName,
            brand,
            category: '',
            taobaoComments: comments,
            xiaohongshuNotes: [],
            heimaoComplaints: [],
            taobaoAnalysis: null,
            xiaohongshuAnalysis: null,
            heimaoAnalysis: null,
            analyzedPlatforms: ['taobao'],
          };
          get().setProductCache(cache);

          // 继续分析（needTaobao=false 因为已经获取了）
          await get().analyzeProduct(brand, productName, needXhs, needHeimao, false);
        } catch (error) {
          addMessage({
            role: 'assistant',
            content: error instanceof Error ? error.message : '获取评论失败',
            type: 'error',
          });
          setLoading(false);
        }
      },

      handleXiaohongshuIntent: async (intentData: IntentData) => {
        const { brand, product } = intentData;
        const keyword = `${brand} ${product}`.trim() || get().currentProduct;

        if (!keyword) {
          get().addMessage({
            role: 'assistant',
            content: '🤖 请告诉我你想搜索什么商品的小红书笔记',
            type: 'text',
          });
          return;
        }

        await get().analyzeProduct('', keyword, true, false, false);
      },

      handleHeimaoIntent: async (intentData: IntentData) => {
        const { brand } = intentData;
        const keyword = brand || get().currentProduct.split(' ')[0];

        if (!keyword) {
          get().addMessage({
            role: 'assistant',
            content: '🤖 请告诉我你想查询什么品牌的投诉信息',
            type: 'text',
          });
          return;
        }

        await get().analyzeProduct(keyword, '', false, true, false);
      },

      handleCompareIntent: async (intentData: IntentData) => {
        get().addMessage({
          role: 'assistant',
          content: '对比功能正在开发中...',
          type: 'text',
        });
      },

      clearConversation: () => {
        set(createInitialState());
      },

      getProductCache: (productName: string) => {
        return get().productCache.get(productName);
      },

      setProductCache: (cache: ProductCache) => {
        set((state) => ({
          productCache: new Map(state.productCache).set(cache.productName, cache),
        }));

        const { sessionId, productCache, currentProduct, messages, conversationHistory } = get();
        const data = {
          currentProduct,
          messages,
          conversationHistory,
          productCache: Object.fromEntries(productCache),
        };
        localStorage.setItem(`session_${sessionId}`, JSON.stringify(data));
      },
    }),
    { name: 'conversation-store' }
  )
);

export default useConversationStore;
