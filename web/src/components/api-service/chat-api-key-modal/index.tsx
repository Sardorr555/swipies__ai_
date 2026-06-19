import CopyToClipboard from '@/components/copy-to-clipboard';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useTranslate } from '@/hooks/common-hooks';
import { IModalProps } from '@/interfaces/common';
import { formatDate } from '@/utils/date';
import { Check, Edit, Key, Plus, Trash2, X } from 'lucide-react';
import { useState } from 'react';
import { useOperateApiKey } from '../hooks';

const ChatApiKeyModal = ({
  dialogId,
  hideModal,
  idKey,
}: IModalProps<any> & { dialogId?: string; idKey: string }) => {
  const {
    createToken,
    removeToken,
    updateToken,
    tokenList,
    listLoading,
    creatingLoading,
  } = useOperateApiKey(idKey, dialogId);
  const { t } = useTranslate('chat');

  const [newKeyName, setNewKeyName] = useState('');
  const [editingToken, setEditingToken] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  const handleCreate = () => {
    createToken(newKeyName.trim() || undefined);
    setNewKeyName('');
  };

  const handleStartEdit = (token: string, currentName: string) => {
    setEditingToken(token);
    setEditingName(currentName);
  };

  const handleSaveEdit = async (token: string) => {
    await updateToken(token, editingName.trim());
    setEditingToken(null);
  };

  const handleToggleStatus = async (token: string, currentStatus: string) => {
    const nextStatus = currentStatus === '0' ? '1' : '0';
    await updateToken(token, undefined, nextStatus);
  };

  return (
    <>
      <Dialog open onOpenChange={hideModal}>
        <DialogContent className="max-w-[60vw] max-h-[85vh] flex flex-col p-6 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white/90 dark:bg-neutral-900/90 backdrop-blur-xl shadow-2xl transition-all duration-300">
          <DialogHeader className="pb-4 border-b border-neutral-100 dark:border-neutral-800">
            <DialogTitle className="flex items-center gap-3 text-xl font-bold tracking-tight text-neutral-800 dark:text-neutral-100">
              <div className="p-2 rounded-xl bg-primary-100 dark:bg-primary-950/50 text-primary-600 dark:text-primary-400">
                <Key className="h-5 w-5" />
              </div>
              {t('apiKey')}
            </DialogTitle>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto py-4 space-y-6 min-h-[300px]">
            {/* Create Key Area */}
            <div className="flex flex-col gap-2 p-4 rounded-xl border border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-950/20">
              <span className="text-sm font-semibold text-neutral-700 dark:text-neutral-300">
                {t('createNewKey')}
              </span>
              <div className="flex gap-3">
                <Input
                  className="flex-1 h-10 px-4 rounded-xl border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 focus-visible:ring-primary-500 focus-visible:border-primary-500 transition-all duration-200"
                  placeholder={t('keyNamePlaceholder') || 'Enter key name...'}
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleCreate();
                  }}
                />
                <Button
                  className="h-10 px-5 rounded-xl bg-primary-600 hover:bg-primary-700 text-white font-medium shadow-sm transition-all duration-200 flex items-center gap-2"
                  onClick={handleCreate}
                  loading={creatingLoading}
                >
                  <Plus className="h-4 w-4" />
                  {t('createNewKey')}
                </Button>
              </div>
            </div>

            {/* List Table */}
            {listLoading ? (
              <div className="flex flex-col items-center justify-center py-12 gap-3 text-neutral-400">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-neutral-300 border-t-primary-600" />
                <span className="text-sm">Loading keys...</span>
              </div>
            ) : !tokenList || tokenList.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-neutral-400 dark:text-neutral-500">
                <Key className="h-12 w-12 stroke-[1.5] mb-2 text-neutral-300 dark:text-neutral-700" />
                <span className="text-sm font-medium">No API Keys created yet</span>
                <span className="text-xs mt-1 text-neutral-400">Create one above to start integration.</span>
              </div>
            ) : (
              <div className="border border-neutral-100 dark:border-neutral-800 rounded-xl overflow-hidden shadow-sm bg-white dark:bg-neutral-950">
                <Table>
                  <TableHeader className="bg-neutral-50 dark:bg-neutral-900/50">
                    <TableRow>
                      <TableHead className="w-[200px] font-semibold text-neutral-700 dark:text-neutral-300">{t('keyName')}</TableHead>
                      <TableHead className="font-semibold text-neutral-700 dark:text-neutral-300">Token</TableHead>
                      <TableHead className="w-[100px] text-center font-semibold text-neutral-700 dark:text-neutral-300">{t('status')}</TableHead>
                      <TableHead className="w-[150px] font-semibold text-neutral-700 dark:text-neutral-300">{t('created')}</TableHead>
                      <TableHead className="w-[120px] text-right font-semibold text-neutral-700 dark:text-neutral-300">{t('action')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tokenList.map((tokenItem) => {
                      const isEditing = editingToken === tokenItem.token;
                      const isEnabled = tokenItem.status !== '0';

                      return (
                        <TableRow
                          key={tokenItem.token}
                          className="hover:bg-neutral-50/50 dark:hover:bg-neutral-900/20 transition-colors duration-150"
                        >
                          {/* Name Field */}
                          <TableCell className="font-medium">
                            {isEditing ? (
                              <div className="flex items-center gap-2">
                                <Input
                                  className="h-8 py-1 px-2 text-sm rounded-lg"
                                  value={editingName}
                                  onChange={(e) => setEditingName(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') handleSaveEdit(tokenItem.token);
                                    if (e.key === 'Escape') setEditingToken(null);
                                  }}
                                  autoFocus
                                />
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8 text-green-600 hover:text-green-700 hover:bg-green-50 dark:hover:bg-green-950/20"
                                  onClick={() => handleSaveEdit(tokenItem.token)}
                                >
                                  <Check className="h-4 w-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8 text-neutral-500 hover:text-neutral-600 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                                  onClick={() => setEditingToken(null)}
                                >
                                  <X className="h-4 w-4" />
                                </Button>
                              </div>
                            ) : (
                              <div className="flex items-center gap-2 group">
                                <span className={`text-sm truncate max-w-[160px] ${isEnabled ? 'text-neutral-900 dark:text-neutral-100' : 'text-neutral-400 line-through'}`}>
                                  {tokenItem.name || 'API Key'}
                                </span>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                                  onClick={() => handleStartEdit(tokenItem.token, tokenItem.name || 'API Key')}
                                >
                                  <Edit className="h-3 w-3" />
                                </Button>
                              </div>
                            )}
                          </TableCell>

                          {/* Token Field */}
                          <TableCell className="font-mono text-xs break-all text-neutral-600 dark:text-neutral-400 select-all">
                            {tokenItem.token}
                          </TableCell>

                          {/* Status Field */}
                          <TableCell className="text-center">
                            <div className="flex items-center justify-center">
                              <Switch
                                checked={isEnabled}
                                onCheckedChange={() => handleToggleStatus(tokenItem.token, tokenItem.status || '1')}
                              />
                            </div>
                          </TableCell>

                          {/* Created Field */}
                          <TableCell className="text-sm text-neutral-500 dark:text-neutral-400">
                            {formatDate(tokenItem.create_date)}
                          </TableCell>

                          {/* Action Field */}
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <CopyToClipboard text={tokenItem.token} />
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 rounded-lg transition-colors"
                                onClick={() => removeToken(tokenItem.token)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ChatApiKeyModal;
