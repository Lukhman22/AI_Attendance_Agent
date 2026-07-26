import axios from 'axios';

const API_URL = '/api/v1/settings';

export const settingsApi = {
  getSettings: async () => {
    const response = await axios.get(API_URL);
    return response.data;
  },
  
  updateSettings: async (settingsData: any) => {
    const response = await axios.put(API_URL, settingsData);
    return response.data;
  },
  
  testTelegram: async (token: string, chatId: string) => {
    const response = await axios.post(`${API_URL}/test-telegram`, {
      telegram_bot_token: token,
      telegram_chat_id: chatId
    });
    return response.data;
  }
};
