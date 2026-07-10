import React, { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/modal/modal';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import message from '@/components/ui/message';
import request from '@/utils/request';
import { LucideZap, LucideCheck, LucideExternalLink } from 'lucide-react';
import { useTranslation } from 'react-i18next';

declare global {
  interface Window {
    showLicenseActivationModal?: (reason?: string) => void;
  }
}

export function LicenseActivationModal() {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [licenseKey, setLicenseKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [activationSuccess, setActivationSuccess] = useState<any>(null);
  const { t } = useTranslation();

  useEffect(() => {
    window.showLicenseActivationModal = (reasonText?: string) => {
      setReason(reasonText || '');
      setOpen(true);
      setErrorMsg('');
      setActivationSuccess(null);
    };
    return () => {
      window.showLicenseActivationModal = undefined;
    };
  }, []);

  const handleActivate = async () => {
    const trimmedKey = licenseKey.trim();
    if (!trimmedKey) {
      setErrorMsg('License key cannot be empty.');
      return;
    }
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await request.post('/api/v1/system/license', {
        data: { license_key: trimmedKey },
      });
      if (res && res.data && res.data.code === 0) {
        message.success('License activated successfully!');
        setActivationSuccess(res.data.data);
        setLicenseKey('');
      } else {
        setErrorMsg(res?.data?.message || 'Failed to activate license.');
      }
    } catch (err: any) {
      const errMsg = err?.response?.data?.message || err?.message || 'Error occurred during activation.';
      setErrorMsg(errMsg);
    } finally {
      setLoading(false);
    }
  };

  if (activationSuccess) {
    const payload = activationSuccess.payload || {};
    return (
      <Modal
        open={open}
        onOpenChange={(newOpen) => {
          if (!newOpen) {
            window.location.reload();
          }
          setOpen(newOpen);
        }}
        title={
          <div className="flex items-center gap-2 text-emerald-500 font-bold">
            <LucideCheck className="w-5 h-5" />
            <span>License Activated Successfully!</span>
          </div>
        }
        showfooter={false}
        maskClosable={false}
        size="default"
      >
        <div className="flex flex-col gap-5 py-4 text-center items-center">
          <div className="p-4 bg-emerald-500/10 rounded-full text-emerald-500 border border-emerald-500/20">
            <LucideCheck className="w-12 h-12" />
          </div>
          
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-text-primary">Premium Unlocked</h3>
            <p className="text-sm text-text-secondary">
              {activationSuccess.message || 'Your commercial license is now active.'}
            </p>
          </div>

          <div className="w-full bg-bg-card border border-border-default rounded-xl p-4 text-left space-y-3 text-sm">
            <div className="flex justify-between border-b border-border-default/60 pb-2">
              <span className="text-text-secondary font-medium">Licensed To:</span>
              <span className="text-text-primary font-semibold font-mono">{payload.owner || 'N/A'}</span>
            </div>
            <div className="flex justify-between border-b border-border-default/60 pb-2">
              <span className="text-text-secondary font-medium">License Type:</span>
              <span className="text-text-primary font-semibold capitalize">{payload.type || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary font-medium">Expiration Date:</span>
              <span className="text-text-primary font-semibold">{payload.expiry || 'N/A'}</span>
            </div>
          </div>

          <div className="w-full pt-2">
            <Button
              className="w-full bg-emerald-500 hover:bg-emerald-600 text-white font-bold h-11 animate-bounce"
              onClick={() => window.location.reload()}
            >
              Restart & Apply Changes
            </Button>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal
      open={open}
      onOpenChange={setOpen}
      title={
        <div className="flex items-center gap-2 text-accent-primary font-bold">
          <LucideZap className="w-5 h-5 fill-accent-primary text-accent-primary animate-pulse" />
          <span>Unlock Swipies Premium / License Required</span>
        </div>
      }
      showfooter={false}
      maskClosable={true}
      size="default"
    >
      <div className="flex flex-col gap-4 py-2">
        {reason && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-500">
            {reason}
          </div>
        )}

        <div className="text-sm text-text-secondary leading-relaxed">
          You are currently running the <strong>Free / Base version</strong> of Swipies. To continue and unlock full capability, please activate a valid commercial license key.
        </div>

        <div className="bg-bg-card border border-border-default rounded-xl p-4 flex flex-col gap-3">
          <h4 className="text-sm font-semibold text-text-primary">Commercial License Benefits:</h4>
          <ul className="text-xs text-text-secondary space-y-2">
            <li className="flex items-center gap-2">
              <LucideCheck className="w-4 h-4 text-green-500 shrink-0" />
              <span>Unlimited Knowledge Bases / Datasets</span>
            </li>
            <li className="flex items-center gap-2">
              <LucideCheck className="w-4 h-4 text-green-500 shrink-0" />
              <span>Unlimited Active AI Agents and Canvas Workflows</span>
            </li>
            <li className="flex items-center gap-2">
              <LucideCheck className="w-4 h-4 text-green-500 shrink-0" />
              <span>Connect any custom LLM providers (DeepSeek, Llama, Qwen, etc.)</span>
            </li>
            <li className="flex items-center gap-2">
              <LucideCheck className="w-4 h-4 text-green-500 shrink-0" />
              <span>Enterprise deployment support and scaling limits</span>
            </li>
          </ul>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
            Enter Commercial License Key:
          </label>
          <Textarea
            placeholder="Paste your base64-encoded Swipies License Key here..."
            value={licenseKey}
            onChange={(e) => setLicenseKey(e.target.value)}
            disabled={loading}
            className="font-mono text-xs"
            rows={4}
          />
        </div>

        {errorMsg && (
          <div className="text-xs text-red-500 font-medium">
            {errorMsg}
          </div>
        )}

        <div className="flex items-center justify-between gap-4 mt-2">
          <a
            href="https://api.swipies.app/user-setting/license"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-accent-primary hover:underline flex items-center gap-1"
          >
            <span>Buy License Key</span>
            <LucideExternalLink className="w-3.5 h-3.5" />
          </a>

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              className="bg-accent-primary hover:bg-accent-primary/95 text-white"
              onClick={handleActivate}
              loading={loading}
            >
              Activate Key
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
