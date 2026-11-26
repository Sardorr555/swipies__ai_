"""Trusted Telegram multipart delivery. Tokens never enter CodeExec or its output."""
import json
import requests
from api.db.services.codeexec_service import attachment

def authorized_channel(tenant_id,channel_id):
    from api.db.services.chat_channel_service import ChatChannelService
    found,channel=ChatChannelService.get_by_id(channel_id)
    # Credentials used by a scenario must belong to its owner, not an arbitrary caller.
    if not found or channel.tenant_id!=tenant_id or channel.channel!='telegram':
        raise PermissionError('Telegram integration is not available for this account')
    return channel

def deliver(channel,recipient_id,spec,transport=None):
    if not isinstance(spec,dict): return {'ok':False,'error':'invalid_delivery_request'}
    try:
        raw,name,mime=attachment(spec.get('attachment'),spec.get('filename','receipt.bin'))
        caption=str(spec.get('caption',''))
        if not caption or len(caption)>1024: raise ValueError('Invalid caption')
        from api.utils.key_crypto import decrypt_connector_config
        cred=decrypt_connector_config(channel.config or {}).get('credential',{})
        token=cred.get('token') or cred.get('bot_token')
        if not token: return {'ok':False,'error':'credential_unavailable'}
        # Only this fixed HTTPS origin is reachable; no URL from a model is used.
        method='sendPhoto' if spec.get('kind')=='photo' and mime.startswith('image/') else 'sendDocument'
        field='photo' if method=='sendPhoto' else 'document'
        send=transport or requests.post
        r=send('https://api.telegram.org/bot'+token+'/'+method,
              data={'chat_id':str(recipient_id),'caption':caption},
              files={field:(name,raw,mime)},timeout=(5,25),allow_redirects=False)
        if r.status_code!=200: return {'ok':False,'error':'telegram_rejected','status':r.status_code}
        data=r.json(); msg=data.get('result') or {}
        if data.get('ok') is not True or not msg.get('message_id'):
            return {'ok':False,'error':'telegram_rejected'}
        return {'ok':True,'message_id':msg['message_id'],'payment_status':'pending_manual_review'}
    except (ValueError,TypeError): return {'ok':False,'error':'invalid_attachment'}
    except requests.Timeout: return {'ok':False,'error':'telegram_timeout','delivery_status':'unknown'}
    except Exception: return {'ok':False,'error':'delivery_failed'}
