#!/usr/bin/env python3
"""Text rewrite helper using configurable chat-completions API.

Priority:
1. config.yaml text_api.*
2. fallback to current chat/manual model outside script
"""
import argparse, json, os, ssl, sys
from urllib import request

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

def load_config():
    p=os.path.join(SKILL_DIR,'config.yaml')
    out={}; sec=None
    with open(p,'r',encoding='utf-8') as f:
        for line in f:
            s=line.strip()
            if not s or s.startswith('#'): continue
            if not line.startswith(' ') and s.endswith(':'):
                sec=s[:-1]; continue
            if ':' in s:
                k,v=s.split(':',1)
                v=v.strip().strip('"').strip("'")
                out[f'{sec}.{k.strip()}' if sec else k.strip()] = v
    return out

def call_api(prompt, system='你是中文内容改写助手。输出自然、有人味、结构清晰，避免AI腔。'):
    c=load_config()
    base=c.get('text_api.base_url','').rstrip('/')
    key=c.get('text_api.api_key','')
    model=c.get('text_api.model','claude-sonnet-4-6')
    if not base or not key:
        print('ERROR: missing text_api config', file=sys.stderr); sys.exit(2)
    payload={
      'model': model,
      'messages': [
        {'role':'system','content':system},
        {'role':'user','content':prompt}
      ],
      'stream': False
    }
    req=request.Request(base + '/v1/chat/completions', data=json.dumps(payload).encode('utf-8'), headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'}, method='POST')
    with request.urlopen(req, timeout=180, context=_ssl_ctx) as resp:
        obj=json.loads(resp.read().decode('utf-8'))
    print(obj['choices'][0]['message']['content'])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--prompt', required=True)
    ap.add_argument('--system', default='你是中文内容改写助手。输出自然、有人味、结构清晰，避免AI腔。')
    args=ap.parse_args()
    call_api(args.prompt, args.system)

if __name__=='__main__':
    main()
