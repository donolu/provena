import type { Metadata } from 'next'
import Link from 'next/link'
import { LegalPage } from '@/components/legal-page'

export const metadata: Metadata = {
  title: 'Privacy policy — Provena',
  description: 'How Provena collects, uses, and protects your personal data.',
}

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy policy" updated="12 July 2026">
      <p>
        Provena (&ldquo;we&rdquo;, &ldquo;us&rdquo;) is a UK marketplace that connects buyers with independent suppliers. This policy explains what personal data we collect, why, and the choices and rights you have. We act as a data controller for your account and as a processor of order data on behalf of suppliers where relevant.
      </p>

      <h2>What we collect</h2>
      <ul>
        <li><strong>Account data</strong>: your name, email, password (stored only as a secure hash), and role (buyer, supplier, or admin).</li>
        <li><strong>Order and address data</strong>: the shipping details and items you order, and your order history.</li>
        <li><strong>Payment data</strong>: card payments are handled by <strong>Stripe</strong>. We never see or store your full card number; we store only a payment reference and status.</li>
        <li><strong>Supplier data</strong>: for suppliers, business details and identity/KYC documents needed to verify you and to enable payouts via Stripe Connect.</li>
        <li><strong>Usage and device data</strong>: basic technical logs and cookies (see below) used to run and secure the service.</li>
      </ul>

      <h2>Why we use it and our legal basis</h2>
      <ul>
        <li><strong>To provide the service</strong> (accounts, browsing, orders, payments, delivery, support) &ndash; performance of a contract.</li>
        <li><strong>To keep the service secure</strong> (authentication, fraud and abuse prevention, rate limiting) &ndash; legitimate interests.</li>
        <li><strong>To meet legal obligations</strong> (tax, accounting, supplier verification) &ndash; legal obligation.</li>
        <li><strong>To send service messages</strong> (order updates, security notices). Marketing, if any, is sent only with your consent.</li>
      </ul>

      <h2 id="cookies">Cookies</h2>
      <p>
        We use a small number of cookies. <strong>Essential cookies</strong> keep you signed in and protect the checkout and are always active. <strong>Optional cookies</strong> help us understand usage and improve the product, and are set only if you accept them in the cookie banner. You can change your choice at any time by clearing the <code>cookie_consent</code> cookie in your browser.
      </p>

      <h2>Who we share it with</h2>
      <ul>
        <li><strong>Suppliers</strong> receive the order and delivery details needed to fulfil your order.</li>
        <li><strong>Stripe</strong> processes payments and supplier payouts.</li>
        <li><strong>Infrastructure and email providers</strong> host the service and deliver transactional email on our behalf, under data-processing terms.</li>
      </ul>
      <p>We do not sell your personal data.</p>

      <h2>How long we keep it</h2>
      <p>
        We keep account data for as long as your account is active. Order, payment, and tax records are retained for the period required by UK law even after an account is closed. Where we no longer need to identify you, we anonymise the record rather than keep your personal details.
      </p>

      <h2>Your rights</h2>
      <p>Under UK GDPR you can:</p>
      <ul>
        <li><strong>Access and export</strong> your data &ndash; request a copy from <Link href="/account/security">your account</Link>.</li>
        <li><strong>Correct</strong> inaccurate details in your account settings.</li>
        <li><strong>Erase</strong> your account (right to be forgotten), subject to records we must retain for legal reasons, which are anonymised.</li>
        <li><strong>Object to or restrict</strong> certain processing, and withdraw consent for optional cookies.</li>
      </ul>
      <p>
        You also have the right to complain to the UK Information Commissioner&rsquo;s Office (ICO).
      </p>

      <h2>Contact</h2>
      <p>
        Questions about this policy or your data: <a href="mailto:privacy@provena.io">privacy@provena.io</a>.
      </p>
    </LegalPage>
  )
}
