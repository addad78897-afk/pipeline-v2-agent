import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('[API]', err.config?.url, err.message)
    return Promise.reject(err)
  }
)
