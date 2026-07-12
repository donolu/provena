import type { Metadata } from 'next'
import Link from 'next/link'
import { LegalPage } from '@/components/legal-page'

export const metadata: Metadata = {
  title: 'Terms of service — Provena',
  description: 'The terms that govern your use of the Provena marketplace.',
}

export default function TermsPage() {
  return (
    <LegalPage title="Terms of service" updated="12 July 2026">
      <p>
        These terms govern your use of the Provena marketplace. By creating an account or placing an order, you agree to them. Provena is a platform: suppliers list and sell their own products, and we facilitate discovery, checkout, payment, and support.
      </p>

      <h2>Your account</h2>
      <p>
        You must provide accurate details and keep your credentials secure. You are responsible for activity under your account. We offer optional two-factor authentication and strongly recommend enabling it. You can close your account at any time from <Link href="/account/security">your account settings</Link>.
      </p>

      <h2>Buying on Provena</h2>
      <ul>
        <li>Product descriptions, prices, and availability are provided by suppliers and may change until an order is placed.</li>
        <li>Placing an order creates a contract between you and the supplier for the items in that order.</li>
        <li>Stock is briefly reserved while you check out; a reservation may expire if checkout is not completed.</li>
      </ul>

      <h2>Payments</h2>
      <p>
        Payments are processed securely by <strong>Stripe</strong>. We do not store your card details. Prices are shown in pounds sterling. You authorise the charge shown at checkout when you confirm your order.
      </p>

      <h2>Delivery, returns, and disputes</h2>
      <p>
        Suppliers are responsible for dispatching and delivering orders. If something is wrong with an order, you can raise a return or a dispute from your order history; our team can mediate and, where appropriate, issue a refund. Your statutory consumer rights are unaffected by these terms.
      </p>

      <h2>Selling on Provena</h2>
      <p>
        Suppliers must complete verification (including identity/KYC checks) and connect a Stripe account to receive payouts. Suppliers are responsible for the accuracy of their listings, the quality and safety of their products, fulfilment, and compliance with applicable law. Provena charges a commission on sales, disclosed during onboarding.
      </p>

      <h2>Acceptable use</h2>
      <ul>
        <li>Do not misuse the service, attempt to access other users&rsquo; data, or interfere with its security.</li>
        <li>Do not list unlawful, unsafe, or infringing products.</li>
        <li>We may suspend or close accounts that breach these terms.</li>
      </ul>

      <h2>Liability</h2>
      <p>
        The service is provided on a reasonable-efforts basis. To the extent permitted by law, Provena is not liable for the acts or omissions of suppliers or buyers, or for indirect or consequential loss. Nothing in these terms limits liability that cannot be limited under UK law.
      </p>

      <h2>Changes and governing law</h2>
      <p>
        We may update these terms and will post the new version here with a revised date. These terms are governed by the laws of England and Wales, and the courts of England and Wales have exclusive jurisdiction.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about these terms: <a href="mailto:support@provena.io">support@provena.io</a>.
      </p>
    </LegalPage>
  )
}
