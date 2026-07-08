import { useEffect, useState } from 'react';
import Spotlight from '@/components/spotlight';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal/modal';
import message from '@/components/ui/message';
import { 
  Key, 
  Sparkles, 
  Trash2, 
  Edit3, 
  Copy, 
  Check, 
  Calendar, 
  CreditCard, 
  ShieldCheck, 
  Info,
  Clock,
  AlertTriangle
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ProfileSettingWrapperCard } from '../components/user-setting-header';
import { 
  listLicenses, 
  createLicensePay, 
  preApplyLicensePay, 
  applyLicensePay, 
  renameLicense, 
  revokeLicense 
} from '@/services/license-service';

interface LicenseKeyItem {
  id: string;
  name: string;
  license_key: string | null;
  amount: number;
  duration_months: number;
  expiry_date: string | null;
  create_time: number;
  status: 'pending' | 'active' | 'revoked' | 'expired';
}

const LicensePage = () => {
  const { t } = useTranslation();
  const [licenses, setLicenses] = useState<LicenseKeyItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Modals state
  const [isPurchaseModalOpen, setIsPurchaseModalOpen] = useState(false);
  const [isRenameModalOpen, setIsRenameModalOpen] = useState(false);
  const [isRevokeModalOpen, setIsRevokeModalOpen] = useState(false);

  // Purchase flow state
  const [purchaseStep, setPurchaseStep] = useState<'plan' | 'card' | 'otp' | 'success'>( 'plan');
  const [newLicenseName, setNewLicenseName] = useState('');
  const [selectedDuration, setSelectedDuration] = useState<6 | 12>(12);
  const [transactionId, setTransactionId] = useState('');
  const [cardNumber, setCardNumber] = useState('');
  const [cardExpiry, setCardExpiry] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [generatedKey, setGeneratedKey] = useState('');
  const [isMockTx, setIsMockTx] = useState(false);
  const [payingLoading, setPayingLoading] = useState(false);

  // Actions target
  const [selectedLicense, setSelectedLicense] = useState<LicenseKeyItem | null>(null);
  const [renameValue, setRenameValue] = useState('');

  const fetchLicenses = async () => {
    setLoading(true);
    try {
      const res = await listLicenses();
      if (res?.data?.code === 0) {
        setLicenses(res.data.data || []);
      }
    } catch (err) {
      console.error(err);
      message.error(t('setting.failedToFetchLicenses', 'Failed to fetch licenses'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLicenses();
  }, []);

  const handleCopy = (keyText: string, id: string) => {
    navigator.clipboard.writeText(keyText);
    setCopiedId(id);
    message.success(t('setting.copiedToClipboard', 'Copied to clipboard'));
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Step 1: Initialize Payment
  const handleInitiatePayment = async () => {
    if (!newLicenseName.trim()) {
      message.error(t('setting.licenseNameRequired', 'Please enter a name for your license key'));
      return;
    }
    setPayingLoading(true);
    try {
      const res = await createLicensePay(newLicenseName, selectedDuration);
      if (res?.data?.code === 0) {
        const payData = res.data.data;
        setTransactionId(payData.transaction_id);
        setIsMockTx(payData.mock);
        setPurchaseStep('card');
      } else {
        message.error(res?.data?.message || t('setting.paymentInitFailed', 'Failed to initiate payment'));
      }
    } catch (err: any) {
      message.error(err?.response?.data?.message || t('setting.paymentInitFailed', 'Failed to initiate payment'));
    } finally {
      setPayingLoading(false);
    }
  };

  // Step 2: Submit Card Details
  const handleCardSubmit = async () => {
    const cleanCard = cardNumber.replace(/\s+/g, '');
    const cleanExpiry = cardExpiry.replace(/\s+/g, '');
    if (cleanCard.length !== 16 || cleanExpiry.length !== 4) {
      message.error(t('setting.invalidCardDetails', 'Please enter a valid 16-digit card number and 4-digit expiry date (YYMM)'));
      return;
    }

    setPayingLoading(true);
    try {
      const res = await preApplyLicensePay(transactionId, cleanCard, cleanExpiry);
      if (res?.data?.code === 0) {
        setPurchaseStep('otp');
      } else {
        message.error(res?.data?.message || t('setting.cardSubmissionFailed', 'Card submission failed'));
      }
    } catch (err: any) {
      message.error(err?.response?.data?.message || t('setting.cardSubmissionFailed', 'Card submission failed'));
    } finally {
      setPayingLoading(false);
    }
  };

  // Step 3: Verify OTP and generated key
  const handleOtpVerify = async () => {
    if (otpCode.length !== 6) {
      message.error(t('setting.invalidOtpCode', 'Please enter a valid 6-digit verification code'));
      return;
    }

    setPayingLoading(true);
    try {
      const res = await applyLicensePay(transactionId, otpCode);
      if (res?.data?.code === 0 && res.data.data?.success) {
        setGeneratedKey(res.data.data.license_key);
        setPurchaseStep('success');
        fetchLicenses();
      } else {
        message.error(res?.data?.message || t('setting.otpFailed', 'OTP verification failed'));
      }
    } catch (err: any) {
      message.error(err?.response?.data?.message || t('setting.otpFailed', 'OTP verification failed'));
    } finally {
      setPayingLoading(false);
    }
  };

  const handleRename = async () => {
    if (!selectedLicense || !renameValue.trim()) return;
    try {
      const res = await renameLicense(selectedLicense.id, renameValue);
      if (res?.data?.code === 0) {
        message.success(t('setting.licenseRenamed', 'License renamed successfully'));
        setIsRenameModalOpen(false);
        fetchLicenses();
      }
    } catch (err) {
      message.error(t('setting.renameFailed', 'Failed to rename license'));
    }
  };

  const handleRevoke = async () => {
    if (!selectedLicense) return;
    try {
      const res = await revokeLicense(selectedLicense.id);
      if (res?.data?.code === 0) {
        message.success(t('setting.licenseRevoked', 'License revoked successfully'));
        setIsRevokeModalOpen(false);
        fetchLicenses();
      }
    } catch (err) {
      message.error(t('setting.revokeFailed', 'Failed to revoke license'));
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="size-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Active
          </span>
        );
      case 'revoked':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">
            Revoked
          </span>
        );
      case 'expired':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
            Expired
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Pending Payment
          </span>
        );
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
    } catch (e) {
      return dateStr;
    }
  };

  const formatCardNumber = (value: string) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    const matches = v.match(/\d{4,16}/g);
    const match = (matches && matches[0]) || '';
    const parts = [];

    for (let i = 0, len = match.length; i < len; i += 4) {
      parts.push(match.substring(i, i + 4));
    }

    if (parts.length > 0) {
      return parts.join(' ');
    } else {
      return v;
    }
  };

  const formatExpiryDate = (value: string) => {
    const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    if (v.length >= 2) {
      return `${v.slice(0, 2)}/${v.slice(2, 4)}`;
    }
    return v;
  };

  return (
    <ProfileSettingWrapperCard
      header={
        <header className="flex flex-col gap-1 w-full">
          <div className="flex justify-between items-center w-full">
            <h2 className="text-2xl font-bold tracking-tight text-text-primary flex items-center gap-2">
              <Key className="text-accent-primary" size={24} />
              {t('setting.license', 'License & Billing')}
            </h2>
            <Button 
              className="bg-accent-primary hover:bg-accent-primary/80 text-white font-semibold flex items-center gap-2 shadow-lg shadow-accent-primary/20 transition-all duration-300"
              onClick={() => {
                setPurchaseStep('plan');
                setNewLicenseName('');
                setCardNumber('');
                setCardExpiry('');
                setOtpCode('');
                setIsPurchaseModalOpen(true);
              }}
            >
              <Sparkles size={16} />
              {t('setting.buyLicense', 'Purchase License Key')}
            </Button>
          </div>
          <p className="text-text-secondary text-sm">
            Purchase and manage license keys to activate Swipies AI on on-premise infrastructure.
          </p>
        </header>
      }
    >
      <Spotlight />

      <div className="h-full overflow-x-hidden overflow-y-auto space-y-6 pb-8 pr-1 mt-6">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-accent-primary"></div>
          </div>
        ) : licenses.length === 0 ? (
          <Card className="border border-border-default bg-bg-component/40 backdrop-blur-md relative overflow-hidden p-8 text-center">
            <div className="p-4 bg-accent-primary/5 rounded-full text-accent-primary size-16 mx-auto flex items-center justify-center mb-4">
              <Key size={32} />
            </div>
            <h3 className="text-lg font-bold text-text-primary mb-2">No License Keys Found</h3>
            <p className="text-sm text-text-secondary max-w-md mx-auto mb-6">
              You haven't purchased any commercial license keys yet. Purchase a key to deploy Swipies AI on your local or private clouds.
            </p>
            <Button
              className="bg-accent-primary hover:bg-accent-primary/90 text-white font-semibold"
              onClick={() => setIsPurchaseModalOpen(true)}
            >
              Get a License Key
            </Button>
          </Card>
        ) : (
          <div className="grid gap-4">
            {licenses.map((lic) => (
              <Card key={lic.id} className="border border-border-default bg-bg-component/20 backdrop-blur-sm hover:bg-bg-component/30 transition-all duration-300">
                <CardContent className="p-6">
                  <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <h4 className="font-bold text-text-primary text-lg">{lic.name}</h4>
                        {getStatusBadge(lic.status)}
                      </div>
                      <div className="flex items-center gap-4 text-xs text-text-secondary mt-1">
                        <span className="flex items-center gap-1">
                          <Calendar size={13} />
                          Expires: {formatDate(lic.expiry_date)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock size={13} />
                          {lic.duration_months} Months
                        </span>
                        <span>
                          Cost: {lic.amount.toLocaleString()} UZS
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-text-primary hover:bg-accent-primary/10 hover:text-accent-primary"
                        onClick={() => {
                          setSelectedLicense(lic);
                          setRenameValue(lic.name);
                          setIsRenameModalOpen(true);
                        }}
                      >
                        <Edit3 size={14} className="mr-1" />
                        Rename
                      </Button>
                      {lic.status !== 'revoked' && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-red-500 border-red-500/20 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30"
                          onClick={() => {
                            setSelectedLicense(lic);
                            setIsRevokeModalOpen(true);
                          }}
                        >
                          <Trash2 size={14} className="mr-1" />
                          Revoke
                        </Button>
                      )}
                    </div>
                  </div>

                  {lic.license_key && (
                    <div className="mt-4 pt-4 border-t border-border-default/50 flex gap-3 items-center">
                      <div className="bg-bg-base/50 border border-border-default rounded p-2 text-xs font-mono text-text-secondary flex-1 break-all select-all max-h-16 overflow-y-auto">
                        {lic.license_key}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-text-secondary hover:text-text-primary shrink-0"
                        onClick={() => handleCopy(lic.license_key!, lic.id)}
                      >
                        {copiedId === lic.id ? <Check className="text-emerald-400" size={16} /> : <Copy size={16} />}
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* PURCHASE FLOW MODAL */}
      <Modal
        title={
          purchaseStep === 'plan' ? 'Select License Plan' :
          purchaseStep === 'card' ? 'Enter Payment Details' :
          purchaseStep === 'otp' ? 'SMS Verification' :
          'Purchase Complete!'
        }
        open={isPurchaseModalOpen}
        showfooter={false}
        className="max-w-[480px]"
        onOpenChange={(open) => {
          if (!open) setIsPurchaseModalOpen(false);
        }}
      >
        <div className="mt-4 space-y-6">
          {purchaseStep === 'plan' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-text-secondary">License Name / Label</label>
                <Input
                  placeholder="e.g. Swipies Production Server"
                  value={newLicenseName}
                  onChange={(e) => setNewLicenseName(e.target.value)}
                  className="bg-bg-input border-border-default"
                />
              </div>

              <label className="text-sm font-medium text-text-secondary block">Select Subscription Period</label>
              <div className="grid grid-cols-2 gap-4">
                <div 
                  className={`border rounded-xl p-4 cursor-pointer transition-all duration-300 ${selectedDuration === 6 ? 'border-accent-primary bg-accent-primary/5 ring-1 ring-accent-primary' : 'border-border-default hover:border-border-default/80 bg-bg-component/20'}`}
                  onClick={() => setSelectedDuration(6)}
                >
                  <h4 className="font-bold text-text-primary">6 Months</h4>
                  <p className="text-xs text-text-secondary mt-1">Deploy on one local node</p>
                  <div className="text-lg font-extrabold text-accent-primary mt-3">300,000 UZS</div>
                </div>

                <div 
                  className={`border rounded-xl p-4 cursor-pointer transition-all duration-300 relative overflow-hidden ${selectedDuration === 12 ? 'border-accent-primary bg-accent-primary/5 ring-1 ring-accent-primary' : 'border-border-default hover:border-border-default/80 bg-bg-component/20'}`}
                  onClick={() => setSelectedDuration(12)}
                >
                  <div className="absolute top-0 right-0 bg-accent-primary text-white text-[9px] font-extrabold px-2 py-0.5 rounded-bl">BEST VALUE</div>
                  <h4 className="font-bold text-text-primary">12 Months</h4>
                  <p className="text-xs text-text-secondary mt-1">Enterprise updates & support</p>
                  <div className="text-lg font-extrabold text-accent-primary mt-3">500,000 UZS</div>
                </div>
              </div>

              <div className="flex gap-2 items-start bg-bg-base/50 p-3 rounded-lg border border-border-default/50 text-xs text-text-secondary">
                <Info size={16} className="text-accent-primary shrink-0 mt-0.5" />
                <p>Payments are securely processed via the Atmos Gateway. The commercial key is tied to the selected duration.</p>
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <Button variant="secondary" onClick={() => setIsPurchaseModalOpen(false)}>Cancel</Button>
                <Button 
                  className="bg-accent-primary text-white" 
                  onClick={handleInitiatePayment}
                  disabled={payingLoading}
                >
                  {payingLoading ? 'Processing...' : 'Continue to Payment'}
                </Button>
              </div>
            </div>
          )}

          {purchaseStep === 'card' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center text-sm text-text-secondary">
                <span>Paying:</span>
                <span className="font-bold text-accent-primary">{selectedDuration === 6 ? '300,000' : '500,000'} UZS</span>
              </div>

              <div className="border border-border-default/60 rounded-xl p-4 bg-gradient-to-br from-bg-component/60 to-bg-component/20 shadow-md relative overflow-hidden aspect-[1.586/1] flex flex-col justify-between text-text-primary">
                <div className="flex justify-between items-center">
                  <CreditCard size={28} className="text-accent-primary" />
                  <span className="text-[10px] tracking-widest opacity-60 font-bold">ATMOS GATEWAY</span>
                </div>
                <div className="space-y-2">
                  <div className="text-xs opacity-60 tracking-wider font-medium">CARD NUMBER</div>
                  <Input
                    placeholder="8600 0000 0000 0000"
                    value={cardNumber}
                    onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
                    maxLength={19}
                    className="bg-bg-input/60 border-border-default/40 font-mono text-base tracking-widest"
                  />
                </div>
                <div className="flex gap-4">
                  <div className="w-1/3 space-y-1">
                    <span className="text-[9px] opacity-60 font-medium">EXPIRY</span>
                    <Input
                      placeholder="YY/MM"
                      value={cardExpiry}
                      onChange={(e) => setCardExpiry(formatExpiryDate(e.target.value))}
                      maxLength={5}
                      className="bg-bg-input/60 border-border-default/40 font-mono text-sm tracking-wider text-center"
                    />
                  </div>
                </div>
              </div>

              {isMockTx && (
                <div className="flex gap-2 items-start bg-amber-500/10 p-3 rounded-lg border border-amber-500/20 text-xs text-amber-400">
                  <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                  <p><strong>Sandbox Mode Enabled:</strong> Atmos credentials are not configured. Enter any 16-digit card and 4-digit expiry date to initiate a mock payment.</p>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4">
                <Button variant="secondary" onClick={() => setPurchaseStep('plan')}>Back</Button>
                <Button 
                  className="bg-accent-primary text-white" 
                  onClick={handleCardSubmit}
                  disabled={payingLoading}
                >
                  {payingLoading ? 'Processing...' : 'Pay'}
                </Button>
              </div>
            </div>
          )}

          {purchaseStep === 'otp' && (
            <div className="space-y-4">
              <div className="space-y-2 text-center">
                <p className="text-sm text-text-secondary">A 6-digit verification code has been sent to your phone number connected to the card.</p>
              </div>

              <div className="flex flex-col items-center gap-3">
                <Input
                  placeholder="000 000"
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value.replace(/[^0-9]/g, ''))}
                  maxLength={6}
                  className="bg-bg-input border-border-default text-center text-xl tracking-widest font-bold max-w-[200px]"
                />
              </div>

              {isMockTx && (
                <div className="flex gap-2 items-start bg-amber-500/10 p-3 rounded-lg border border-amber-500/20 text-xs text-amber-400">
                  <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                  <p><strong>Sandbox Verification:</strong> Enter any 6-digit OTP code (e.g. 123456) to successfully approve this transaction.</p>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4">
                <Button variant="secondary" onClick={() => setPurchaseStep('card')}>Back</Button>
                <Button 
                  className="bg-accent-primary text-white" 
                  onClick={handleOtpVerify}
                  disabled={payingLoading}
                >
                  {payingLoading ? 'Verifying...' : 'Verify OTP'}
                </Button>
              </div>
            </div>
          )}

          {purchaseStep === 'success' && (
            <div className="space-y-5 text-center py-4">
              <div className="p-4 bg-emerald-500/10 rounded-full text-emerald-400 size-16 mx-auto flex items-center justify-center">
                <ShieldCheck size={36} />
              </div>
              <div className="space-y-1">
                <h3 className="text-lg font-bold text-text-primary">License Issued Successfully!</h3>
                <p className="text-xs text-text-secondary">Copy this key and paste it during deployment setup to activate Swipies AI Commercial Edition.</p>
              </div>

              <div className="space-y-2 text-left">
                <label className="text-xs font-semibold text-text-secondary">License Activation Key</label>
                <div className="flex gap-2 items-center bg-bg-base/80 border border-border-default rounded-lg p-3 font-mono text-xs text-text-primary break-all max-h-24 overflow-y-auto">
                  {generatedKey}
                </div>
              </div>

              <div className="flex gap-3 justify-center pt-4">
                <Button 
                  className="bg-accent-primary text-white flex items-center gap-2"
                  onClick={() => handleCopy(generatedKey, 'success-key')}
                >
                  <Copy size={14} /> Copy Key
                </Button>
                <Button variant="secondary" onClick={() => setIsPurchaseModalOpen(false)}>Close</Button>
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* RENAME MODAL */}
      <Modal
        title="Rename License"
        open={isRenameModalOpen}
        showfooter={false}
        className="max-w-[400px]"
        onOpenChange={(open) => {
          if (!open) setIsRenameModalOpen(false);
        }}
      >
        <div className="mt-4 space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-text-secondary">New Name</label>
            <Input
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              className="bg-bg-input border-border-default"
            />
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="secondary" onClick={() => setIsRenameModalOpen(false)}>Cancel</Button>
            <Button className="bg-accent-primary text-white" onClick={handleRename}>Save</Button>
          </div>
        </div>
      </Modal>

      {/* REVOKE CONFIRMATION MODAL */}
      <Modal
        title="Revoke License Key"
        open={isRevokeModalOpen}
        showfooter={false}
        className="max-w-[400px]"
        onOpenChange={(open) => {
          if (!open) setIsRevokeModalOpen(false);
        }}
      >
        <div className="mt-4 space-y-4">
          <div className="flex gap-3 bg-red-500/10 p-3 rounded-lg border border-red-500/20 text-sm text-red-400">
            <AlertTriangle size={20} className="shrink-0" />
            <p><strong>Warning:</strong> Revoking this license key will immediately deactivate any deployments running on it. This action cannot be undone.</p>
          </div>
          <p className="text-sm text-text-secondary">Are you sure you want to revoke the license key <strong>"{selectedLicense?.name}"</strong>?</p>
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="secondary" onClick={() => setIsRevokeModalOpen(false)}>Cancel</Button>
            <Button className="bg-red-500 hover:bg-red-600 text-white" onClick={handleRevoke}>Revoke License</Button>
          </div>
        </div>
      </Modal>
    </ProfileSettingWrapperCard>
  );
};

export default LicensePage;
