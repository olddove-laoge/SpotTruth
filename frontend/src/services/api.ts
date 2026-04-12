import axios, { AxiosError } from 'axios';
import type {
  ParseIntentRequest,
  ClassifyRequest,
  ClassifyResponse,
  AnalyzeRequest,
  AnalyzeResponse,
  SummarizeRequest,
  SummarizeResponse,
  XiaohongshuRequest,
  XiaohongshuResponse,
  HeimaoRequest,
  HeimaoResponse,
  CompareConclusionRequest,
  IntentData,
} from '../types';

// API 基础配置
// 开发环境使用空字符串（走 Vite 代理），生产环境使用完整 URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60秒超时
  headers: {
    'Content-Type': 'application/json',
  },
});

// 开发测试用 Token（从登录接口获取，30分钟有效）
// 注意：实际项目应该实现登录页面获取 Token
const DEV_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoidXNlciIsInVzZXJuYW1lIjoic3BvdHRydXRoX3VzZXIiLCJpc3MiOiJzcG90dHJ1dGgtYXBpLWdhdGV3YXkiLCJzdWIiOiJ1LXNwb3R0cnV0aC11c2VyIiwiZXhwIjoxNzc1OTcyNDU0LCJpYXQiOjE3NzU5NzA2NTQsImp0aSI6IjMxY2Y3MmJlOGU3MzJhOWIzMzVhNWVkN2NkOTIzM2M0In0.AUNkl3m__4J5Rev5dm7uGhqk2r4TNmyqkFcosPy9Aos";

// 请求拦截器 - 添加认证
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token') || DEV_TOKEN;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器 - 错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data as any;

      if (status === 401) {
        // Token 过期，清除并提示
        localStorage.removeItem('access_token');
        throw new Error('登录已过期，请重新登录');
      }

      if (status === 429) {
        throw new Error('请求过于频繁，请稍后再试');
      }

      if (status === 503 && data?.code === 'GATEWAY_DEGRADED') {
        throw new Error('服务繁忙，请稍后重试');
      }

      throw new Error(data?.message || '请求失败');
    }

    if (error.request) {
      throw new Error('网络错误，请检查服务是否启动');
    }

    throw error;
  }
);

// 健康检查
export const healthCheck = async (): Promise<{ status: string; service: string; version: string }> => {
  const response = await apiClient.get('/healthz');
  return response.data;
};

// 就绪检查
export const readyCheck = async (): Promise<{ status: string; message?: string }> => {
  const response = await apiClient.get('/readyz');
  return response.data;
};

// 解析意图
export const parseIntent = async (data: ParseIntentRequest): Promise<IntentData> => {
  const response = await apiClient.post('/api/parse_intent', {
    user_input: data.userInput,
    conversation_history: data.conversationHistory,
    current_product: data.currentProduct,
    analyzed_platforms: data.analyzedPlatforms,
  });

  const result = response.data;
  return {
    intent: result.intent,
    brand: result.brand || '',
    product: result.product || '',
    needXiaohongshu: result.need_xiaohongshu || false,
    needHeimao: result.need_heimao || false,
    needTaobao: result.need_taobao ?? !(result.need_xiaohongshu || result.need_heimao),
    clarificationNeeded: result.clarification_needed || false,
    clarificationQuestion: result.clarification_question || '',
    response: result.response || '',
    products: result.products,
  };
};

// 品类分类
export const classifyProduct = async (data: ClassifyRequest): Promise<ClassifyResponse> => {
  const response = await apiClient.post('/api/classify', {
    product_name: data.productName,
  });
  return {
    productName: response.data.product_name,
    category: response.data.category,
    keywordsMatch: response.data.keywords_match,
  };
};

// 评论分析
export const analyzeComments = async (data: AnalyzeRequest): Promise<AnalyzeResponse> => {
  const response = await apiClient.post('/api/analyze', {
    comments: data.comments,
    product_name: data.productName,
    category: data.category,
  });
  return response.data;
};

// 生成总结
export const summarize = async (data: SummarizeRequest): Promise<SummarizeResponse> => {
  const response = await apiClient.post('/api/summarize', {
    statistics: data.statistics,
    sample_comments: data.sampleComments,
  });
  return {
    summary: response.data.summary,
    advice: response.data.advice,
  };
};

// 小红书分析
export const analyzeXiaohongshu = async (data: XiaohongshuRequest): Promise<XiaohongshuResponse> => {
  const response = await apiClient.post('/api/analyze_xiaohongshu', {
    notes: data.notes,
    keyword: data.keyword,
  });
  return {
    summary: response.data.summary,
    key_points: response.data.key_points || [],
    sentiment: response.data.sentiment,
  };
};

// 黑猫投诉分析
export const analyzeHeimao = async (data: HeimaoRequest): Promise<HeimaoResponse> => {
  const response = await apiClient.post('/api/analyze_heimao', {
    complaints: data.complaints,
    brand: data.brand,
  });
  return {
    summary: response.data.summary,
    complaint_types: response.data.complaint_types || [],
    severity: response.data.severity,
    recommendation: response.data.recommendation,
  };
};

// 生成对比结论
export const generateComparisonConclusion = async (
  data: CompareConclusionRequest
): Promise<{ conclusion: string }> => {
  const response = await apiClient.post('/api/compare_conclusion', {
    product_a_name: data.productAName,
    product_b_name: data.productBName,
    stats_a: data.statsA,
    stats_b: data.statsB,
    summary_a: data.summaryA,
    summary_b: data.summaryB,
    advice_a: data.adviceA,
    advice_b: data.adviceB,
    heimao_analysis_a: data.heimaoAnalysisA,
    heimao_analysis_b: data.heimaoAnalysisB,
    xhs_analysis_a: data.xhsAnalysisA,
    xhs_analysis_b: data.xhsAnalysisB,
    has_taobao_a: data.hasTaobaoA,
    has_taobao_b: data.hasTaobaoB,
  });
  return { conclusion: response.data.conclusion };
};

export default apiClient;
export { API_BASE_URL };
