import uuid,pytz
from datetime import datetime
IST=pytz.timezone('Asia/Kolkata')

def parse_message(message):
    data={}
    for part in message.split():
        if '=' in part:
            k,v=part.split('=')
            data[k]=v
    return data

def generate_order_id(p='ORD'):
    return f"{p}_{uuid.uuid4().hex[:10]}"

def current_ist_time():
    return datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')

def should_ignore(last,current):
    return last and last.get('trade_type')==current
