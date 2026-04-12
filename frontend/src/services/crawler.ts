import axios from 'axios';
import type {
  CrawlerSearchRequest,
  CrawlerSearchResponse,
  CrawlerCommentsRequest,
  CrawlerCommentsResponse,
  Product,
} from '../types';
import { API_BASE_URL } from './api';

// 爬虫服务配置（统一走网关）
const CRAWLER_BASE_URL = API_BASE_URL;

const crawlerClient = axios.create({
  baseURL: CRAWLER_BASE_URL,
  timeout: 120000, // 爬虫可能需要更长时间
  headers: {
    'Content-Type': 'application/json',
  },
});

// 开发测试用 Token（与 api.ts 保持一致）
const DEV_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoidXNlciIsInVzZXJuYW1lIjoic3BvdHRydXRoX3VzZXIiLCJpc3MiOiJzcG90dHJ1dGgtYXBpLWdhdGV3YXkiLCJzdWIiOiJ1LXNwb3R0cnV0aC11c2VyIiwiZXhwIjoxNzc1OTYzMzkwLCJpYXQiOjE3NzU5NjE1OTAsImp0aSI6IjNlNThlZDk0ZjU0MGE4YmY2MjgyMjVlOWJmNGY4YTdjIn0.rQAm1umQQI3XoYyOaPzq_i3zp0MezNgeFbcI4DdMWr4";

// 请求拦截器 - 添加认证
crawlerClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token') || DEV_TOKEN;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 搜索淘宝商品
export const searchTaobaoProducts = async (
  data: CrawlerSearchRequest
): Promise<Product[]> => {
  const response = await crawlerClient.post<CrawlerSearchResponse>('/crawler/taobao/search', {
    brand: data.brand,
    product: data.product,
    max_results: data.maxResults || 5,
  });

  if (!response.data.success) {
    throw new Error('搜索商品失败');
  }

  return response.data.data.map((item, index) => ({
    id: `product-${index}`,
    name: item.name,
    price: item.price,
    sales: item.sales,
    shopName: item.shop_name,
    shopTag: item.shop_tag,
    url: item.url,
    imageUrl: item.image_url,
  }));
};

// 获取淘宝评论
export const getTaobaoComments = async (
  data: CrawlerCommentsRequest
): Promise<string[]> => {
  const response = await crawlerClient.post<CrawlerCommentsResponse>('/crawler/taobao/comments', {
    url: data.url,
    brand: data.brand,
    product: data.product,
    max_count: data.maxCount || 50,
  });

  if (!response.data.success) {
    throw new Error('获取评论失败');
  }

  return response.data.data.map((item) => item.text);
};

// 搜索小红书（异步轮询）
export const searchXiaohongshu = async (
  keyword: string,
  maxNotes: number = 5,
  onProgress?: (progress: number, message: string) => void
): Promise<string[]> => {
  // 1. 创建任务
  const createResponse = await crawlerClient.post('/crawler/xiaohongshu/search', {
    keyword,
    max_notes: maxNotes,
  });

  const { task_id, status } = createResponse.data;

  if (!task_id) {
    throw new Error('创建任务失败');
  }

  // 2. 轮询查询任务状态
  const maxAttempts = 60; // 最多轮询60次（2分钟）
  const pollInterval = 2000; // 每2秒轮询一次

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await new Promise(resolve => setTimeout(resolve, pollInterval));

    const statusResponse = await crawlerClient.get(`/crawler/task/${task_id}/status`);
    const task = statusResponse.data;

    // 通知进度回调
    if (onProgress && task.progress) {
      onProgress(task.progress, task.message);
    }

    // 检查任务状态
    if (task.status === 'completed') {
      if (task.result && task.result.data) {
        return task.result.data.map((item: { text: string }) => item.text);
      }
      return [];
    }

    if (task.status === 'failed') {
      throw new Error(task.error || '爬取失败');
    }

    // 继续轮询...
  }

  throw new Error('轮询超时，任务可能仍在运行');
};

// 搜索黑猫投诉
export const searchHeimao = async (
  brand: string,
  maxComplaints: number = 30
): Promise<string[]> => {
  const response = await crawlerClient.post('/crawler/heimao/search', {
    brand,
    max_complaints: maxComplaints,
  });

  if (!response.data.success) {
    throw new Error('搜索黑猫投诉失败');
  }

  return response.data.data.map((item: { text: string }) => item.text);
};

export { CRAWLER_BASE_URL };
export default crawlerClient;
