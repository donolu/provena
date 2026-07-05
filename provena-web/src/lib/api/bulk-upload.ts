import { apiClient } from './client'

export interface UploadVariantPreview {
  name: string
  sku: string
  price: string
  compare_at_price: string | null
  weight_grams: number
}

export interface UploadProductPreview {
  name: string
  description: string
  category: string | null
  image_url: string | null
  variants: UploadVariantPreview[]
}

export interface UploadError {
  row: number
  column: string
  message: string
}

export interface PreviewResult {
  valid: boolean
  products?: UploadProductPreview[]
  row_count?: number
  product_count?: number
  errors?: UploadError[]
}

export interface ConfirmResult {
  created: number
  products: UploadProductPreview[]
}

export function getUploadTemplate(): string {
  return `${apiClient.defaults.baseURL ?? ''}/catalogue/products/upload/template/`
}

export async function previewUpload(file: File): Promise<PreviewResult> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await apiClient.post<PreviewResult>(
    '/catalogue/products/upload/preview/',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export async function confirmUpload(file: File): Promise<ConfirmResult> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await apiClient.post<ConfirmResult>(
    '/catalogue/products/upload/confirm/',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}
