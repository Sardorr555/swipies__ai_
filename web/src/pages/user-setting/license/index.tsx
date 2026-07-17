import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Key, ArrowRight } from 'lucide-react';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';
import { getUserLicensePricing } from '@/services/license-service';
import { useNavigate } from 'react-router';

interface PricingConfig {
  price_6_months: number;
  price_12_months: number;
}

const fmt = (n: number) =>
  new Intl.NumberFormat('uz-UZ').format(n) + ' UZS';

const LicensePurchasePage = () => {
  const navigate = useNavigate();
  const [selectedMonths, setSelectedMonths] = useState<6 | 12>(12);
  const [pricing, setPricing] = useState<PricingConfig>({
    price_6_months: 300000,
    price_12_months: 500000,
  });

  useEffect(() => {
    getUserLicensePricing()
      .then((res: any) => {
        if (res?.data?.code === 0 && res.data.data) {
          setPricing(res.data.data);
        }
      })
      .catch(() => {});
  }, []);

  const handleProceedToCheckout = () => {
    navigate(`/checkout?plan=license&period=${selectedMonths}`);
  };

  return (
    <ProfileSettingWrapperCard
      header={
        <header className="flex flex-col gap-1 w-full">
          <h2 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
            <Key className="text-accent-primary" size={24} />
            License Key Purchase
          </h2>
          <p className="text-text-secondary text-sm">
            Buy a license key compatible with your Swipies AI deployment.
          </p>
        </header>
      }
    >
      <div className="h-full overflow-x-hidden overflow-y-auto pb-8 pr-1 mt-6 space-y-6 px-5 max-w-lg">
        <div className="space-y-5">
          <h3 className="text-base font-semibold text-text-primary">Choose a plan</h3>

          {/* Plan cards */}
          <div className="grid grid-cols-2 gap-4">
            {([6, 12] as const).map((m) => {
              const p = m === 12 ? pricing.price_12_months : pricing.price_6_months;
              const selected = selectedMonths === m;
              return (
                <button
                  key={m}
                  onClick={() => setSelectedMonths(m)}
                  className={`rounded-xl border p-4 text-left transition-all space-y-1 ${
                    selected
                      ? 'border-accent-primary bg-accent-primary/8 ring-1 ring-accent-primary/40'
                      : 'border-border-default bg-bg-card/20 hover:border-accent-primary/40'
                  }`}
                >
                  <div className="text-sm font-semibold text-text-primary">{m} months</div>
                  <div className="text-lg font-bold text-accent-primary">{fmt(p)}</div>
                  {m === 12 && (
                    <span className="text-[10px] bg-emerald-500/15 text-emerald-400 px-1.5 py-0.5 rounded font-semibold uppercase tracking-wide">
                      Best value
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Total */}
          <div className="flex items-center justify-between rounded-xl border border-border-default bg-bg-card/20 px-4 py-3">
            <span className="text-sm text-text-secondary">Total</span>
            <span className="font-bold text-text-primary">
              {fmt(selectedMonths === 12 ? pricing.price_12_months : pricing.price_6_months)}
            </span>
          </div>

          <Button
            className="bg-accent-primary hover:bg-accent-primary/90 text-white w-full gap-2"
            onClick={handleProceedToCheckout}
          >
            Proceed to Checkout <ArrowRight size={16} />
          </Button>
        </div>
      </div>
    </ProfileSettingWrapperCard>
  );
};

export default LicensePurchasePage;
