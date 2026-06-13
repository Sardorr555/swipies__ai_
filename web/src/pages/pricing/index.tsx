import { BRAND } from '@/constants/branding';
import { Button } from '@/components/ui/button';
import { LucideCheck, LucideZap, LucideArrowLeft } from 'lucide-react';
import { Link } from 'react-router';
import { Routes } from '@/routes';

const plans = [
  {
    name: 'Free',
    price: '$0',
    period: '/month',
    description: 'Get started with basic features',
    features: [
      '1 Knowledge Base',
      '50 MB Storage',
      '100 Queries/day',
      'Basic Chat Assistant',
      'Community Support',
    ],
    cta: 'Current Plan',
    disabled: true,
    gradient: false,
  },
  {
    name: 'Pro',
    price: '$29',
    period: '/month',
    description: 'For professionals and small teams',
    features: [
      '10 Knowledge Bases',
      '5 GB Storage',
      'Unlimited Queries',
      'Advanced AI Agents',
      'Priority Support',
      'Custom Branding',
      'API Access',
    ],
    cta: 'Upgrade to Pro',
    disabled: false,
    gradient: true,
    popular: true,
  },
  {
    name: 'Enterprise',
    price: '$99',
    period: '/month',
    description: 'For organizations with advanced needs',
    features: [
      'Unlimited Knowledge Bases',
      '50 GB Storage',
      'Unlimited Queries',
      'Advanced AI Agents',
      'Dedicated Support',
      'Custom Branding',
      'API Access',
      'SSO & SAML',
      'Audit Logs',
      'SLA Guarantee',
    ],
    cta: 'Contact Sales',
    disabled: false,
    gradient: false,
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-bg-body p-8 overflow-auto">
      <div className="max-w-6xl mx-auto">
        {/* Back button */}
        <Link
          to={Routes.Root}
          className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary mb-8 transition-colors"
        >
          <LucideArrowLeft className="size-4" />
          Back to {BRAND.name}
        </Link>

        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-text-primary mb-4">
            Upgrade Your {BRAND.name} Plan
          </h1>
          <p className="text-lg text-text-secondary max-w-2xl mx-auto">
            Choose the plan that fits your needs. Unlock powerful AI features,
            more storage, and priority support.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`relative rounded-2xl border p-8 flex flex-col transition-all duration-300 hover:shadow-xl ${
                plan.gradient
                  ? 'border-[#478AF5] bg-gradient-to-b from-[#478AF5]/5 to-[#42D7E7]/5 shadow-lg scale-[1.02]'
                  : 'border-border bg-bg-component hover:border-[#478AF5]/50'
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold text-white rounded-full bg-gradient-to-r from-[#478AF5] to-[#42D7E7]">
                    <LucideZap className="size-3" />
                    Most Popular
                  </span>
                </div>
              )}

              <div className="mb-6">
                <h2 className="text-xl font-bold text-text-primary mb-1">
                  {plan.name}
                </h2>
                <p className="text-sm text-text-secondary">
                  {plan.description}
                </p>
              </div>

              <div className="mb-6">
                <span className="text-4xl font-bold text-text-primary">
                  {plan.price}
                </span>
                <span className="text-text-secondary">{plan.period}</span>
              </div>

              <ul className="flex-1 space-y-3 mb-8">
                {plan.features.map((feature) => (
                  <li
                    key={feature}
                    className="flex items-center gap-2 text-sm text-text-secondary"
                  >
                    <LucideCheck className="size-4 text-[#42D7E7] shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>

              <Button
                className={`w-full ${
                  plan.gradient
                    ? 'bg-gradient-to-r from-[#478AF5] to-[#42D7E7] text-white hover:from-[#3a7ae0] hover:to-[#35c5d4] shadow-md'
                    : ''
                }`}
                variant={plan.gradient ? 'default' : 'outline'}
                disabled={plan.disabled}
              >
                {plan.cta}
              </Button>
            </div>
          ))}
        </div>

        {/* Footer note */}
        <p className="text-center text-sm text-text-secondary mt-8">
          All plans include a 14-day free trial. Cancel anytime.
        </p>
      </div>
    </div>
  );
}
