import axios, { AxiosError } from 'axios'
import type { ApiErrorBody } from '../types/api'

export const api = axios.create({
  baseURL: '/api/v1',
})

export function getErrorMessage(error: unknown, fallback = 'Something went wrong') {
  if (axios.isAxiosError(error)) {
    const ax = error as AxiosError<ApiErrorBody>
    return ax.response?.data?.error?.message || ax.message || fallback
  }
  if (error instanceof Error) return error.message
  return fallback
}
