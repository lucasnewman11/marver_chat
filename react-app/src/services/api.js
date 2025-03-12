import axios from 'axios';

// Base API configuration
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const axiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Generic API methods
export const get = async (endpoint, params = {}) => {
  try {
    const response = await axiosInstance.get(endpoint, { params });
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const post = async (endpoint, data = {}) => {
  try {
    const response = await axiosInstance.post(endpoint, data);
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const put = async (endpoint, data = {}) => {
  try {
    const response = await axiosInstance.put(endpoint, data);
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const del = async (endpoint) => {
  try {
    const response = await axiosInstance.delete(endpoint);
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// Error handling
const handleApiError = (error) => {
  const errorMessage = error.response?.data?.error || error.message || 'Unknown error occurred';
  console.error('API Error:', errorMessage);
  throw new Error(errorMessage);
};

export default {
  get,
  post,
  put,
  del,
};