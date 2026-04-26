import axios from 'axios';

const BASE_URL = __DEV__ ? 'http://10.0.2.2:8000/api/v1' : 'https://your-api.example.com/api/v1';

const client = axios.create({baseURL: BASE_URL, timeout: 10_000});

export const api = {
  getInbox: async () => {
    const {data} = await client.get('/inbox');
    return data;
  },

  getEmailDetail: async (emailId: string) => {
    const {data} = await client.get(`/inbox/${emailId}`);
    return data;
  },

  submitFeedback: async (emailId: string, isScam: boolean) => {
    const {data} = await client.post('/feedback', {
      flagged_email_id: emailId,
      is_scam: isScam,
      user_id: 'local-user',
    });
    return data;
  },
};
