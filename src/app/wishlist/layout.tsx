import { AuthGuard } from '@/components/auth-guard'

export default function WishlistLayout({ children }: { children: React.ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>
}
