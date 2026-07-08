import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal/modal';
import message from '@/components/ui/message';
import {
  Key,
  Search,
  Plus,
  Trash2,
  Copy,
  Check,
  Calendar,
  User,
  ShieldAlert,
  ChevronLeft,
  ChevronRight,
  Clock
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { adminListLicenses, adminIssueLicense, adminRevokeLicense } from '@/services/license-service';

interface AdminLicenseItem {
  id: string;
  name: string;
  user_id: string;
  user_email: string;
  license_key: string | null;
  amount: number;
  duration_months: number;
  expiry_date: string | null;
  status: 'pending' | 'active' | 'revoked' | 'expired';
}

const AdminLicensesPage = () => {
  const { t } = useTranslation();
  const [licenses, setLicenses] = useState<AdminLicenseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Modals state
  const [isIssueModalOpen, setIsIssueModalOpen] = useState(false);
  const [isRevokeModalOpen, setIsRevokeModalOpen] = useState(false);
  const [selectedLicense, setSelectedLicense] = useState<AdminLicenseItem | null>(null);

  // Issue form state
  const [issueEmail, setIssueEmail] = useState('');
  const [issueName, setIssueName] = useState('');
  const [issueDuration, setIssueDuration] = useState<number>(12);
  const [issueLoading, setIssueLoading] = useState(false);
  const [issuedKey, setIssuedKey] = useState<string | null>(null);

  const fetchLicenses = async () => {
    setLoading(true);
    try {
      const res = await adminListLicenses({ page, size: 10, search });
      if (res?.data?.code === 0) {
        setLicenses(res.data.data.licenses || []);
        setTotal(res.data.data.total || 0);
      }
    } catch (err) {
      console.error(err);
      message.error(t('admin.failedToFetchLicenses', 'Failed to load licenses list'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLicenses();
  }, [page, search]);

  const handleCopy = (keyText: string, id: string) => {
    navigator.clipboard.writeText(keyText);
    setCopiedId(id);
    message.success(t('setting.copiedToClipboard', 'Copied to clipboard'));
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleIssueLicense = async () => {
    if (!issueEmail.trim() || !issueName.trim()) {
      message.error(t('admin.allFieldsRequired', 'Please fill in user email and license name'));
      return;
    }

    setIssueLoading(true);
    try {
      const res = await adminIssueLicense(issueEmail, issueName, issueDuration);
      if (res?.data?.code === 0) {
        setIssuedKey(res.data.data.license_key);
        message.success(t('admin.licenseIssuedSuccessfully', 'License issued successfully'));
        fetchLicenses();
      } else {
        message.error(res?.data?.message || t('admin.issueFailed', 'Failed to issue license key'));
      }
    } catch (err: any) {
      message.error(err?.response?.data?.message || t('admin.issueFailed', 'Failed to issue license key'));
    } finally {
      setIssueLoading(false);
    }
  };

  const handleRevokeLicense = async () => {
    if (!selectedLicense) return;
    try {
      const res = await adminRevokeLicense(selectedLicense.id);
      if (res?.data?.code === 0) {
        message.success(t('admin.licenseRevokedSuccessfully', 'License revoked successfully'));
        setIsRevokeModalOpen(false);
        fetchLicenses();
      } else {
        message.error(res?.data?.message || t('admin.revokeFailed', 'Failed to revoke license'));
      }
    } catch (err) {
      message.error(t('admin.revokeFailed', 'Failed to revoke license'));
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Active
          </span>
        );
      case 'revoked':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">
            Revoked
          </span>
        );
      case 'expired':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
            Expired
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Pending
          </span>
        );
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6 p-6 h-full overflow-y-auto">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-text-primary tracking-tight">License Keys Manager</h1>
          <p className="text-text-secondary text-sm">Monitor commercial license sales, activation states, and manually issue/revoke keys.</p>
        </div>
        <Button
          className="bg-accent-primary hover:bg-accent-primary/95 text-white font-semibold flex items-center gap-2"
          onClick={() => {
            setIssueEmail('');
            setIssueName('');
            setIssuedKey(null);
            setIsIssueModalOpen(true);
          }}
        >
          <Plus size={16} />
          Issue Manual License
        </Button>
      </div>

      <Card className="border border-border-default bg-bg-component/20 backdrop-blur-sm">
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <CardTitle className="text-lg">All Licenses</CardTitle>
          <div className="relative w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary size-4" />
            <Input
              placeholder="Search by email or name..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="pl-9 bg-bg-input border-border-default"
            />
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center h-48">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-accent-primary"></div>
            </div>
          ) : licenses.length === 0 ? (
            <div className="text-center py-12 text-text-secondary">No license keys found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border-default/60 text-xs font-semibold text-text-secondary uppercase">
                    <th className="py-3 px-4">License / Owner</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4">Expires</th>
                    <th className="py-3 px-4">License Key</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default/40 text-sm">
                  {licenses.map((lic) => (
                    <tr key={lic.id} className="hover:bg-bg-component/10 transition-colors">
                      <td className="py-4 px-4">
                        <div className="font-bold text-text-primary">{lic.name}</div>
                        <div className="text-xs text-text-secondary flex items-center gap-1 mt-0.5">
                          <User size={12} /> {lic.user_email}
                        </div>
                      </td>
                      <td className="py-4 px-4 font-medium text-text-primary">
                        {lic.duration_months} Months
                      </td>
                      <td className="py-4 px-4 text-text-secondary">
                        {formatDate(lic.expiry_date)}
                      </td>
                      <td className="py-4 px-4 max-w-xs">
                        {lic.license_key ? (
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs text-text-secondary bg-bg-base/40 border border-border-default rounded px-1.5 py-0.5 truncate select-all block max-w-[200px]">
                              {lic.license_key}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-7 text-text-secondary hover:text-text-primary"
                              onClick={() => handleCopy(lic.license_key!, lic.id)}
                            >
                              {copiedId === lic.id ? <Check className="text-emerald-400" size={14} /> : <Copy size={14} />}
                            </Button>
                          </div>
                        ) : (
                          <span className="text-xs italic text-text-secondary">Unpaid/Pending</span>
                        )}
                      </td>
                      <td className="py-4 px-4 text-center">
                        {getStatusBadge(lic.status)}
                      </td>
                      <td className="py-4 px-4 text-right">
                        {lic.status !== 'revoked' && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-red-500 hover:text-red-400 hover:bg-red-500/10 size-8"
                            onClick={() => {
                              setSelectedLicense(lic);
                              setIsRevokeModalOpen(true);
                            }}
                          >
                            <Trash2 size={16} />
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination */}
              <div className="flex justify-between items-center pt-4 border-t border-border-default/60 mt-4 text-sm text-text-secondary">
                <span>Total: {total} records</span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 1}
                    onClick={() => setPage(p => p - 1)}
                  >
                    <ChevronLeft size={16} />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page * 10 >= total}
                    onClick={() => setPage(p => p + 1)}
                  >
                    <ChevronRight size={16} />
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ISSUE MANUAL LICENSE MODAL */}
      <Modal
        title="Issue Manual License Key"
        open={isIssueModalOpen}
        showfooter={false}
        className="max-w-[450px]"
        onOpenChange={(open) => {
          if (!open) setIsIssueModalOpen(false);
        }}
      >
        <div className="mt-4 space-y-4">
          {!issuedKey ? (
            <>
              <div className="space-y-2">
                <label className="text-sm font-medium text-text-secondary">User Email (Target)</label>
                <Input
                  placeholder="user@example.com"
                  value={issueEmail}
                  onChange={(e) => setIssueEmail(e.target.value)}
                  className="bg-bg-input border-border-default"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-text-secondary">License Label / Name</label>
                <Input
                  placeholder="e.g. Enterprise Node A"
                  value={issueName}
                  onChange={(e) => setIssueName(e.target.value)}
                  className="bg-bg-input border-border-default"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-text-secondary">Duration</label>
                <div className="grid grid-cols-3 gap-2">
                  {[3, 6, 12].map((m) => (
                    <Button
                      key={m}
                      variant={issueDuration === m ? 'default' : 'outline'}
                      onClick={() => setIssueDuration(m)}
                      className="w-full font-semibold"
                    >
                      {m} Months
                    </Button>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button variant="secondary" onClick={() => setIsIssueModalOpen(false)}>Cancel</Button>
                <Button
                  className="bg-accent-primary text-white"
                  onClick={handleIssueLicense}
                  disabled={issueLoading}
                >
                  {issueLoading ? 'Generating...' : 'Issue License'}
                </Button>
              </div>
            </>
          ) : (
            <div className="space-y-4 text-center py-2">
              <div className="p-3 bg-emerald-500/10 rounded-full text-emerald-400 size-12 mx-auto flex items-center justify-center">
                <Key size={24} />
              </div>
              <h4 className="font-bold text-text-primary">License Issued Successfully!</h4>
              <p className="text-xs text-text-secondary">Here is the manually generated license key. Copy and send it to the client.</p>

              <div className="bg-bg-base/80 border border-border-default rounded p-3 text-left font-mono text-xs text-text-primary break-all max-h-24 overflow-y-auto">
                {issuedKey}
              </div>

              <div className="flex gap-2 justify-center pt-4">
                <Button
                  className="bg-accent-primary text-white flex items-center gap-1.5"
                  onClick={() => handleCopy(issuedKey, 'manual-key')}
                >
                  <Copy size={14} /> Copy Key
                </Button>
                <Button variant="secondary" onClick={() => setIsIssueModalOpen(false)}>Done</Button>
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* REVOKE CONFIRM MODAL */}
      <Modal
        title="Revoke License Confirmation"
        open={isRevokeModalOpen}
        showfooter={false}
        className="max-w-[400px]"
        onOpenChange={(open) => {
          if (!open) setIsRevokeModalOpen(false);
        }}
      >
        <div className="mt-4 space-y-4">
          <div className="flex gap-3 bg-red-500/10 p-3 rounded-lg border border-red-500/20 text-sm text-red-400">
            <ShieldAlert size={24} className="shrink-0" />
            <p><strong>Warning:</strong> Revoking this license key will immediately disable it across all client environments. This action cannot be reverted.</p>
          </div>
          <p className="text-sm text-text-secondary">
            Are you sure you want to revoke <strong>"{selectedLicense?.name}"</strong> owned by <strong>{selectedLicense?.user_email}</strong>?
          </p>
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="secondary" onClick={() => setIsRevokeModalOpen(false)}>Cancel</Button>
            <Button className="bg-red-500 hover:bg-red-600 text-white" onClick={handleRevokeLicense}>
              Confirm Revoke
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default AdminLicensesPage;
