"""PNG cards rendered from the same explicit aggregate projection as a public widget."""
import io
from functools import lru_cache
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

LABELS={'users_total':'Всего пользователей','users_active':'Активные за период','users_new':'Новые пользователи',
    'messages_in':'Сообщения пользователей','messages_out':'Ответы бота','payers':'Оплатившие пользователи',
    'payments':'Успешные платежи','revenue':'Выручка до возвратов','refunds':'Возвраты'}

@lru_cache(maxsize=64)
def _font(size):
    bundled=Path(__file__).parents[2]/'channels'/'telegram'/'assets'/'NotoSans.ttf'
    for path in [str(bundled),'/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                 '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf','C:/Windows/Fonts/arial.ttf']:
        if Path(path).exists(): return ImageFont.truetype(path,size)
    raise RuntimeError('Для PNG требуется установленный шрифт с кириллицей (DejaVu Sans)')

def metric_text(data,key):
    if key in data.get('metrics',{}):
        value=data['metrics'][key]
        return 'Нет данных' if value is None else f'{int(value):,}'.replace(',',' ')
    payment=data.get('payments_period')
    if data.get('payment_tracking')!='connected': return 'Не подключено'
    if payment is None: return 'Нет данных'
    if key in ('payers','payments'): return str(payment.get(key,'—'))
    field='amount' if key=='revenue' else 'refund_amount'
    rows=payment.get('currencies',[])
    return '\n'.join(f'{row.get(field,"0")} {row["currency"]}' for row in rows) or '0'

def render_png(data,format='square',link=None):
    if format not in ('square','story'): raise ValueError('Формат должен быть square или story')
    width,height=1080,1920 if format=='story' else 1080
    image=Image.new('RGB',(width,height),'#0c1222'); draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((34,34,width-34,height-34),radius=34,fill='#101c32',outline='#283650',width=2)
    draw.rounded_rectangle((72,72,238,119),radius=14,fill='#2463eb')
    draw.text((90,79),'Swipies AI',font=_font(24),fill='white')
    title=' '.join(str(data.get('title') or data['bot']['name']).split())[:60]
    title_font=_font(44 if format=='story' else 38)
    while draw.textlength(title,font=title_font)>936 and len(title)>8: title=title[:-2]+'…'
    draw.text((72,153),title,font=title_font,fill='white')
    username=data['bot'].get('username')
    if username: draw.text((72,216),'@'+username[:60],font=_font(25),fill='#93a8cb')
    period=data['period']
    draw.text((72,261),period['start']+' — '+period['end'],font=_font(25),fill='#c8d4e9')
    draw.text((72,300),period['timezone'],font=_font(22),fill='#93a8cb')
    keys=data.get('selected_metrics') or list(data.get('metrics',{}))
    columns=2 if format=='story' else 3
    rows=(len(keys)+columns-1)//columns
    start=365 if format=='story' else 350
    footer=270 if link else 130
    card_height=min(240,(height-start-footer-48)//max(rows,1))
    gap=18; card_width=(936-gap*(columns-1))//columns
    for index,key in enumerate(keys):
        x=72+(index%columns)*(card_width+gap); y=start+(index//columns)*(card_height+gap)
        draw.rounded_rectangle((x,y,x+card_width,y+card_height),radius=20,fill='#192843',outline='#31445f')
        label=LABELS.get(key,key)
        font=_font(22 if format=='story' else 18)
        words=label.split(); line=''; lines=[]
        for word in words:
            if line and draw.textlength(line+' '+word,font=font)>card_width-32:
                lines.append(line); line=word
            else: line=(line+' '+word).strip()
        lines.append(line)
        draw.multiline_text((x+18,y+16),'\n'.join(lines[:2]),font=font,fill='#afc0dd',spacing=5)
        text=metric_text(data,key)
        values=text.splitlines()
        size=40 if format=='story' else 27
        if len(values)>2: size=24 if format=='story' else 19
        value_font=_font(size)
        available_height=max(24,card_height-28-len(lines[:2])*(font.size+5))
        # Fit the complete value block inside its card, including font bearings.
        while size>12:
            bounds=draw.multiline_textbbox((0,0),text,font=value_font,spacing=4)
            if bounds[2]-bounds[0]<=card_width-36 and bounds[3]-bounds[1]<=available_height: break
            size-=1; value_font=_font(size)
        bounds=draw.multiline_textbbox((0,0),text,font=value_font,spacing=4)
        if bounds[3]-bounds[1]>available_height:
            capacity=max(1,int(available_height//(size+6)))
            extra=len(values)-max(0,capacity-1)
            text='\n'.join(values[:max(0,capacity-1)]+[f'+ ещё {extra} валют · см. виджет'])
            bounds=draw.multiline_textbbox((0,0),text,font=value_font,spacing=4)
        value_y=y+card_height-18-(bounds[3]-bounds[1])-bounds[1]
        draw.multiline_text((x+18,value_y),text,font=value_font,fill='white',spacing=4)
    footer_y=height-footer
    draw.text((72,footer_y),'Замеченные ботом пользователи, не участники групп',font=_font(19),fill='#93a8cb')
    if data.get('coverage')!='available':
        draw.text((72,footer_y+32),'Период содержит время до начала сбора данных',font=_font(19),fill='#f3be62')
    if link:
        draw.text((72,footer_y+77),'Живая аналитика',font=_font(22),fill='white')
        # Text link is deliberately included without fetching remote images/fonts.
        chunks=[link[i:i+85] for i in range(0,len(link),85)]
        draw.multiline_text((72,footer_y+112),'\n'.join(chunks[:3]),font=_font(17),fill='#91b8ff',spacing=5)
    draw.text((72,height-72),'Снимок '+data['updated_at'][:16].replace('T',' ')+' UTC',font=_font(18),fill='#93a8cb')
    output=io.BytesIO(); image.save(output,format='PNG',optimize=True)
    return output.getvalue()
