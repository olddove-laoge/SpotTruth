// Message Types
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  type: MessageType;
  metadata?: MessageMetadata;
  timestamp: number;
}

export type MessageType =
  | 'text'
  | 'loading'
  | 'product_select'
  | 'analysis_report'
  | 'comparison_report'
  | 'error';

export interface MessageMetadata {
  products?: Product[];
  analysisResult?: AnalysisResult;
  comparisonResult?: ComparisonResult;
  error?: string;
}

// Product Types
export interface Product {
  id: string;
  name: string;
  price: string;
  sales: string;
  shopName: string;
  shopTag: string;
  url: string;
  imageUrl: string;
}

export interface ProductCache {
  productName: string;
  brand: string;
  category: string;
  taobaoComments: string[];
  xiaohongshuNotes: string[];
  heimaoComplaints: string[];
  taobaoAnalysis: TaobaoAnalysis | null;
  xiaohongshuAnalysis: XiaohongshuAnalysis | null;
  heimaoAnalysis: HeimaoAnalysis | null;
  analyzedPlatforms: string[];
}

// Analysis Types
export interface AnalysisResult {
  productName: string;
  category: string;
  statistics: Statistics;
  summary: string;
  advice: string;
  results: CommentItem[];
  xiaohongshu?: XiaohongshuAnalysis;
  heimao?: HeimaoAnalysis;
}

export interface Statistics {
  total: number;
  positiveCount: number;
  negativeCount: number;
  sarcasmCount: number;
  positiveRate: number;
  negativeRate: number;
}

export interface CommentItem {
  text: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  isSarcasm: boolean;
  confidence: number;
  sarcasmConfidence: number;
  llmAnalysis?: string;
}

export interface TaobaoAnalysis {
  stats: Statistics;
  results: CommentItem[];
  summary: string;
  advice: string;
}

export interface XiaohongshuAnalysis {
  summary: string;
  keyPoints: string[];
  sentiment: 'mostly_positive' | 'mixed' | 'mostly_negative' | 'unknown';
}

export interface HeimaoAnalysis {
  summary: string;
  complaintTypes: string[];
  severity: 'high' | 'medium' | 'low' | 'unknown';
  recommendation: string;
}

// Comparison Types
export interface ComparisonResult {
  productA: ComparisonProduct;
  productB: ComparisonProduct;
  conclusion: string;
}

export interface ComparisonProduct {
  name: string;
  statistics: Statistics;
  summary: string;
  advice: string;
  xhsAnalysis?: XiaohongshuAnalysis;
  heimaoAnalysis?: HeimaoAnalysis;
  xhsCount: number;
  heimaoCount: number;
}

// Intent Types
export interface IntentData {
  intent: 'analyze' | 'compare' | 'search_xhs' | 'search_heimao' | 'help' | 'unknown';
  brand: string;
  product: string;
  needXiaohongshu: boolean;
  needHeimao: boolean;
  needTaobao: boolean;
  clarificationNeeded: boolean;
  clarificationQuestion: string;
  response: string;
  products?: { brand: string; product: string }[];
}

// API Request/Response Types
export interface ParseIntentRequest {
  userInput: string;
  conversationHistory: { role: string; content: string }[];
  currentProduct: string;
  analyzedPlatforms: string[];
}

export interface ClassifyRequest {
  productName: string;
}

export interface ClassifyResponse {
  productName: string;
  category: string;
  keywordsMatch: boolean;
}

export interface AnalyzeRequest {
  comments: string[];
  productName: string;
  category: string;
}

export interface AnalyzeResponse {
  product_name: string;
  category: string;
  statistics: {
    total: number;
    positive_count: number;
    negative_count: number;
    sarcasm_count: number;
    positive_rate: number;
    negative_rate: number;
  };
  results: {
    text: string;
    sentiment: string;
    is_sarcasm: boolean;
    confidence: number;
    sarcasm_confidence: number;
    llm_analysis?: string;
  }[];
}

export interface SummarizeRequest {
  statistics: {
    total: number;
    positive_rate: number;
    negative_rate: number;
    sarcasm_count: number;
  };
  sampleComments: {
    text: string;
    sentiment: string;
    is_sarcasm: boolean;
  }[];
}

export interface SummarizeResponse {
  summary: string;
  advice: string;
}

export interface XiaohongshuRequest {
  notes: { title: string; content: string; likes: number }[];
  keyword: string;
}

export interface XiaohongshuResponse {
  summary: string;
  key_points: string[];
  sentiment: string;
}

export interface HeimaoRequest {
  complaints: { title: string; content: string; status: string }[];
  brand: string;
}

export interface HeimaoResponse {
  summary: string;
  complaint_types: string[];
  severity: string;
  recommendation: string;
}

export interface CompareConclusionRequest {
  productAName: string;
  productBName: string;
  statsA: Statistics;
  statsB: Statistics;
  summaryA: string;
  summaryB: string;
  adviceA: string;
  adviceB: string;
  heimaoAnalysisA?: HeimaoAnalysis;
  heimaoAnalysisB?: HeimaoAnalysis;
  xhsAnalysisA?: XiaohongshuAnalysis;
  xhsAnalysisB?: XiaohongshuAnalysis;
  hasTaobaoA: boolean;
  hasTaobaoB: boolean;
}

// Crawler Types
export interface CrawlerSearchRequest {
  brand: string;
  product: string;
  maxResults?: number;
}

export interface CrawlerSearchResponse {
  success: boolean;
  data: Array<{
    name: string;
    price: string;
    sales: string;
    shop_name: string;
    shop_tag: string;
    url: string;
    image_url: string;
  }>;
}

export interface CrawlerCommentsRequest {
  url: string;
  brand: string;
  product: string;
  maxCount?: number;
}

export interface CrawlerCommentsResponse {
  success: boolean;
  data: Array<{
    text: string;
  }>;
}
