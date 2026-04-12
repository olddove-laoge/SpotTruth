import axios from 'axios';
import type {
  CrawlerSearchRequest,
  CrawlerCommentsRequest,
  Product,
} from '../types';
import { API_BASE_URL } from './api';

// 爬虫服务配置（统一走网关，使用 cookie 认证）
const CRAWLER_BASE_URL = API_BASE_URL;

const crawlerClient = axios.create({
  baseURL: CRAWLER_BASE_URL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // 允许跨域请求携带 cookie
});

// 搜索淘宝商品（异步轮询）
export const searchTaobaoProducts = async (
  data: CrawlerSearchRequest,
  onProgress?: (progress: number, message: string) => void
): Promise<Product[]> => {
  const createResponse = await crawlerClient.post('/crawler/taobao/search', {
    brand: data.brand,
    product: data.product,
    max_results: data.maxResults || 5,
  });

  const { task_id } = createResponse.data;

  if (!task_id) {
    throw new Error('创建任务失败');
  }

  const maxAttempts = 60;
  const pollInterval = 2000;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await new Promise(resolve => setTimeout(resolve, pollInterval));

    const statusResponse = await crawlerClient.get(`/crawler/task/${task_id}/status`);
    const task = statusResponse.data;

    if (onProgress && task.progress) {
      onProgress(task.progress, task.message);
    }

    if (task.status === 'completed') {
      if (task.result && task.result.data) {
        return task.result.data.map((item: any, index: number) => ({
          id: `product-${index}`,
          name: item.name,
          price: item.price,
          sales: item.sales,
          shopName: item.shop_name,
          shopTag: item.shop_tag,
          url: item.url,
          imageUrl: item.image_url,
        }));
      }
      return [];
    }

    if (task.status === 'failed') {
      throw new Error(task.error || '搜索商品失败');
    }
  }

  throw new Error('轮询超时，任务可能仍在运行');
};

// 获取淘宝评论（异步轮询）
export const getTaobaoComments = async (
  data: CrawlerCommentsRequest,
  onProgress?: (progress: number, message: string) => void
): Promise<string[]> => {
  const createResponse = await crawlerClient.post('/crawler/taobao/comments', {
    url: data.url,
    brand: data.brand,
    product: data.product,
    max_count: data.maxCount || 50,
  });

  const { task_id } = createResponse.data;

  if (!task_id) {
    throw new Error('创建任务失败');
  }

  const maxAttempts = 60;
  const pollInterval = 2000;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await new Promise(resolve => setTimeout(resolve, pollInterval));

    const statusResponse = await crawlerClient.get(`/crawler/task/${task_id}/status`);
    const task = statusResponse.data;

    if (onProgress && task.progress) {
      onProgress(task.progress, task.message);
    }

    if (task.status === 'completed') {
      if (task.result && task.result.data) {
        return task.result.data.map((item: { text: string }) => item.text);
      }
      return [];
    }

    if (task.status === 'failed') {
      throw new Error(task.error || '获取评论失败');
    }
  }

  throw new Error('轮询超时，任务可能仍在运行');
};

// 搜索小红书（异步轮询）
export const searchXiaohongshu = async (
  keyword: string,
  maxNotes: number = 5,
  onProgress?: (progress: number, message: string) => void
): Promise<string[]> => {
  const createResponse = await crawlerClient.post('/crawler/xiaohongshu/search', {
    keyword,
    max_notes: maxNotes,
  });

  const { task_id } = createResponse.data;

  if (!task_id) {
    throw new Error('创建任务失败');
  }

  const maxAttempts = 60;
  const pollInterval = 2000;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await new Promise(resolve => setTimeout(resolve, pollInterval));

    const statusResponse = await crawlerClient.get(`/crawler/task/${task_id}/status`);
    const task = statusResponse.data;

    if (onProgress && task.progress) {
      onProgress(task.progress, task.message);
    }

    if (task.status === 'completed') {
      if (task.result && task.result.data) {
        return task.result.data.map((item: { text: string }) => item.text);
      }
      return [];
    }

    if (task.status === 'failed') {
      throw new Error(task.error || '爬取失败');
    }
  }

  throw new Error('轮询超时，任务可能仍在运行');
};

// 搜索黑猫投诉（异步轮询）
export const searchHeimao = async (
  brand: string,
  maxComplaints: number = 30,
  onProgress?: (progress: number, message: string) => void
): Promise<string[]> => {
  const createResponse = await crawlerClient.post('/crawler/heimao/search', {
    brand,
    max_complaints: maxComplaints,
  });

  const { task_id } = createResponse.data;

  if (!task_id) {
    throw new Error('创建任务失败');
  }

  const maxAttempts = 60;
  const pollInterval = 2000;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await new Promise(resolve => setTimeout(resolve, pollInterval));

    const statusResponse = await crawlerClient.get(`/crawler/task/${task_id}/status`);
    const task = statusResponse.data;

    if (onProgress && task.progress) {
      onProgress(task.progress, task.message);
    }

    if (task.status === 'completed') {
      if (task.result && task.result.data) {
        return task.result.data.map((item: { text: string }) => item.text);
      }
      return [];
    }

    if (task.status === 'failed') {
      throw new Error(task.error || '搜索黑猫投诉失败');
    }
  }

  throw new Error('轮询超时，任务可能仍在运行');
};

export { CRAWLER_BASE_URL };
export default crawlerClient;
