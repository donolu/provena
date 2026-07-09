import { apiClient } from './client'
import type { Notification, NotificationPreferences, PaginatedResponse } from './types'

export async function getNotifications(unreadOnly?: boolean, page = 1): Promise<PaginatedResponse<Notification>> {
  const params: Record<string, string | number> = { page }
  if (unreadOnly) params.unread = 'true'
  const { data } = await apiClient.get<PaginatedResponse<Notification>>('/notifications/', { params })
  return data
}

export async function markNotificationRead(id: string): Promise<Notification> {
  const { data } = await apiClient.post<Notification>(`/notifications/${id}/read/`)
  return data
}

export async function markAllNotificationsRead(): Promise<{ marked_read: number }> {
  const { data } = await apiClient.post<{ marked_read: number }>('/notifications/read-all/')
  return data
}

export async function deleteNotification(id: string): Promise<void> {
  await apiClient.delete(`/notifications/${id}/`)
}

export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  const { data } = await apiClient.get<NotificationPreferences>('/notifications/preferences/')
  return data
}

export async function updateNotificationPreferences(
  prefs: Partial<Omit<NotificationPreferences, 'updated_at'>>,
): Promise<NotificationPreferences> {
  const { data } = await apiClient.patch<NotificationPreferences>('/notifications/preferences/', prefs)
  return data
}
