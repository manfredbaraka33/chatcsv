import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";

export const processUrls = (urls) => axios.post(`${API_BASE}/process/`, { urls });
export const askQuestion = (query) => axios.post(`${API_BASE}/ask/`, { query });
