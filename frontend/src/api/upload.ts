import { api } from './client'

export async function uploadFiles(files: File[]): Promise<{ session_id: string; file_count: number }> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  const { data } = await api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
