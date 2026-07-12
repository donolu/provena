import Link from 'next/link'

export function LegalPage({
  title,
  updated,
  children,
}: {
  title: string
  updated: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-mist">
      <header className="border-b border-hoarfrost">
        <div className="max-w-3xl mx-auto px-6 h-16 flex items-center">
          <Link href="/catalogue" className="font-display italic text-2xl text-forest">Provena</Link>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-6 py-14">
        <h1 className="font-display italic text-3xl md:text-4xl text-forest">{title}</h1>
        <p className="mt-2 text-sm text-soil">Last updated {updated}</p>
        <div className="legal mt-10 text-forest">{children}</div>
        <p className="mt-14 text-xs text-soil/70 border-t border-hoarfrost pt-6">
          This document is a plain-language summary of how Provena operates and is provided for transparency. It is not legal advice; the definitive terms are those you accept when you create an account.
        </p>
      </main>
      <style>{`
        .legal h2 { font-family: var(--font-fraunces), serif; font-style: italic; font-size: 1.3rem; color: #1f3d2b; margin: 2.2rem 0 .6rem; }
        .legal h3 { font-weight: 600; font-size: .95rem; margin: 1.4rem 0 .4rem; color: #1f3d2b; }
        .legal p, .legal li { font-size: .95rem; line-height: 1.7; color: #33473b; }
        .legal p { margin: .6rem 0; }
        .legal ul { margin: .5rem 0 .5rem 1.1rem; list-style: disc; }
        .legal li { margin: .3rem 0; }
        .legal a { color: #2f6f4f; text-decoration: underline; text-underline-offset: 2px; }
        .legal strong { color: #1f3d2b; }
      `}</style>
    </div>
  )
}
