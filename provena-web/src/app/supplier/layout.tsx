import { SupplierShell } from '@/components/supplier/sidebar'

export default function SupplierLayout({ children }: { children: React.ReactNode }) {
  return <SupplierShell>{children}</SupplierShell>
}
