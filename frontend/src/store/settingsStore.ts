import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface SettingsState {
  // EdgeDriver 路径
  driverPath: string;
  // Kimi API Key
  kimiApiKey: string;
  // 浏览器登录状态（使用统一 profile）
  browserLoggedIn: boolean;

  // 设置方法
  setDriverPath: (path: string) => void;
  setKimiApiKey: (key: string) => void;
  setBrowserLoggedIn: (status: boolean) => void;

  // 登录方法（统一打开浏览器，用户依次登录三个平台）
  loginBrowser: () => Promise<void>;

  // 保存/加载设置
  saveSettings: () => void;
  loadSettings: () => void;
  resetToDefaults: () => void;
}

// 默认配置（硬编码值）
const DEFAULT_DRIVER_PATH = 'E:\\edgedriver_win64 (1)\\msedgedriver.exe';
const DEFAULT_KIMI_API_KEY = 'sk-NxnJvWVKw9cun9Y80gjfQp7PyWR9rOMwy9VH2aNU28xOdxcr';

const STORAGE_KEY = 'spottruth_settings';

export const useSettingsStore = create<SettingsState>()(
  devtools(
    (set, get) => ({
      driverPath: DEFAULT_DRIVER_PATH,
      kimiApiKey: DEFAULT_KIMI_API_KEY,
      browserLoggedIn: false,

      setDriverPath: (path) => {
        set({ driverPath: path });
        get().saveSettings();
      },

      setKimiApiKey: (key) => {
        set({ kimiApiKey: key });
        get().saveSettings();
      },

      setBrowserLoggedIn: (status) => {
        set({ browserLoggedIn: status });
        get().saveSettings();
      },

      loginBrowser: async () => {
        const { driverPath } = get();
        try {
          const response = await fetch('/api/login/browser', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ driverPath }),
          });
          if (response.ok) {
            get().setBrowserLoggedIn(true);
          } else {
            const error = await response.text();
            throw new Error(error);
          }
        } catch (error) {
          console.error('浏览器登录失败:', error);
          throw error;
        }
      },

      saveSettings: () => {
        const { driverPath, kimiApiKey, browserLoggedIn } = get();
        const data = {
          driverPath,
          kimiApiKey,
          browserLoggedIn,
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      },

      loadSettings: () => {
        try {
          const saved = localStorage.getItem(STORAGE_KEY);
          if (saved) {
            const data = JSON.parse(saved);
            set({
              driverPath: data.driverPath || DEFAULT_DRIVER_PATH,
              kimiApiKey: data.kimiApiKey || DEFAULT_KIMI_API_KEY,
              browserLoggedIn: data.browserLoggedIn || false,
            });
          }
        } catch (e) {
          console.error('加载设置失败:', e);
        }
      },

      resetToDefaults: () => {
        set({
          driverPath: DEFAULT_DRIVER_PATH,
          kimiApiKey: DEFAULT_KIMI_API_KEY,
          browserLoggedIn: false,
        });
        get().saveSettings();
      },
    }),
    { name: 'settings-store' }
  )
);

export { DEFAULT_DRIVER_PATH, DEFAULT_KIMI_API_KEY };
