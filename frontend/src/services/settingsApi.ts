import { api } from './apiClient';

export const settingsApi = {
  getSettings: async () => {
    const response = await api.get('/settings');
    return response.data;
  },

  updateSettings: async (settingsData: Record<string, unknown>) => {
    const response = await api.put('/settings', settingsData);
    return response.data;
  },

  testTelegram: async (token: string, chatId: string) => {
    const response = await api.post('/settings/test-telegram', {
      telegram_bot_token: token,
      telegram_chat_id: chatId,
    });
    return response.data;
  },
};
