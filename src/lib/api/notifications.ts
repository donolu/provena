import { apiClient } from './client'
import type { NotificationPreferences } from './types'

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
