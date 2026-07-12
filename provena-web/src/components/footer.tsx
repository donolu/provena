import Link from 'next/link'

export function Footer() {
  const year = new Date().getFullYear()
  return (
    <footer className="bg-forest text-mist/80 mt-auto">
      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
          <div className="max-w-xs">
            <Link href="/catalogue" className="font-display italic text-xl text-mist">Provena</Link>
            <p className="mt-2 text-xs text-mist/60 leading-relaxed">
              A UK marketplace connecting buyers with vetted suppliers. Know your source.
            </p>
          </div>

          <nav className="grid gap-2 text-sm" aria-label="Footer">
            <span className="text-[11px] uppercase tracking-[0.14em] text-mist/40 mb-1">Marketplace</span>
            <Link href="/catalogue" className="hover:text-marigold transition-colors">Browse products</Link>
            <Link href="/orders" className="hover:text-marigold transition-colors">Orders</Link>
            <Link href="/account/security" className="hover:text-marigold transition-colors">Your account</Link>
          </nav>

          <nav className="grid gap-2 text-sm" aria-label="Legal">
            <span className="text-[11px] uppercase tracking-[0.14em] text-mist/40 mb-1">Legal</span>
            <Link href="/privacy" className="hover:text-marigold transition-colors">Privacy policy</Link>
            <Link href="/terms" className="hover:text-marigold transition-colors">Terms of service</Link>
            <Link href="/privacy#cookies" className="hover:text-marigold transition-colors">Cookie policy</Link>
          </nav>
        </div>

        <div className="mt-10 pt-6 border-t border-mist/10 text-xs text-mist/50">
          &copy; {year} Provena. All rights reserved.
        </div>
      </div>
    </footer>
  )
}
