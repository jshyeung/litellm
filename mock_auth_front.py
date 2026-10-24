import json, secrets, time, os
from pathlib import Path
from urllib.parse import urlencode
from aiohttp import web, ClientSession

ROOT=Path(__file__).resolve().parent
STATE={'approved':False,'device_code':secrets.token_urlsafe(24),'user_code':'GATE-WAY1'}
PREFIX='/claude_code_gateway'
async def handle(request):
    path=request.path
    if path==PREFIX+'/.well-known/oauth-authorization-server':
        return web.json_response({'issuer':'http://localhost:4002'+PREFIX,'device_authorization_endpoint':'http://localhost:4002'+PREFIX+'/oauth/device_authorization','token_endpoint':'http://localhost:4002'+PREFIX+'/oauth/token','grant_types_supported':['urn:ietf:params:oauth:grant-type:device_code']})
    if path==PREFIX+'/oauth/device_authorization':
        STATE['approved']=False
        return web.json_response({'device_code':STATE['device_code'],'user_code':STATE['user_code'],'verification_uri':'http://localhost:4002/verify','verification_uri_complete':'http://localhost:4002/verify','expires_in':600,'interval':1})
    if path=='/verify' and request.method=='GET':
        return web.Response(text='<html><body style="font:20px sans-serif;padding:48px"><h1>Local mock identity provider</h1><p>Approve the synthetic Claude Code test session. This is not production SSO.</p><form method="post"><button style="font:20px sans-serif;padding:15px">Approve local test sign-in</button></form></body></html>',content_type='text/html')
    if path=='/verify' and request.method=='POST':
        STATE['approved']=True
        return web.Response(text='<html><body><h1>Local test sign-in approved</h1><p>Return to Claude Code.</p></body></html>',content_type='text/html')
    if path==PREFIX+'/oauth/token':
        form=await request.post()
        if form.get('device_code')!=STATE['device_code']:
            return web.json_response({'error':'expired_token'},status=400)
        if not STATE['approved']:
            return web.json_response({'error':'authorization_pending'},status=400)
        return web.json_response({'access_token':os.environ['LITELLM_MASTER_KEY'],'token_type':'Bearer','expires_in':3600})
    body=await request.read()
    headers={k:v for k,v in request.headers.items() if k.lower() not in ('host','content-length','connection','accept-encoding')}
    async with ClientSession() as session:
        async with session.request(request.method,'http://127.0.0.1:4000'+str(request.rel_url),headers=headers,data=body) as upstream:
            payload=await upstream.read()
            record={'method':request.method,'path':str(request.rel_url),'status':upstream.status}
            if path.endswith('/v1/models'):
                record['body']=json.loads(payload)
            with (ROOT/'gateway-wire.jsonl').open('a') as log:log.write(json.dumps(record)+'\n')
            return web.Response(body=payload,status=upstream.status,headers={k:v for k,v in upstream.headers.items() if k.lower() not in ('content-length','transfer-encoding','connection','content-encoding')})
app=web.Application();app.router.add_route('*','/{path:.*}',handle)
web.run_app(app,host='127.0.0.1',port=4002,print=None)
