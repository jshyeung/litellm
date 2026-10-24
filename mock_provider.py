import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG = Path(__file__).resolve().parent / 'provider-requests.jsonl'
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or '{}')
        with LOG.open('a') as out:
            out.write(json.dumps({'method':'POST','path':self.path,'model':body.get('model'),'stream':body.get('stream'), 'message_count':len(body.get('messages', []))})+'\n')
        if 'count_tokens' in self.path:
            payload = json.dumps({'input_tokens':32}).encode()
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(payload); return
        message = {'id':'msg_gateway_demo','type':'message','role':'assistant','model':body.get('model'), 'content':[{'type':'text','text':'GATEWAY_OK: the interactive request reached the local mock provider through LiteLLM.'}], 'stop_reason':'end_turn','stop_sequence':None,'usage':{'input_tokens':32,'output_tokens':16}}
        self.send_response(200)
        self.send_header('Content-Type','text/event-stream' if body.get('stream') else 'application/json')
        self.end_headers()
        if not body.get('stream'):
            self.wfile.write(json.dumps(message).encode());return
        events=[('message_start', {'type':'message_start','message':{**message,'content':[],'stop_reason':None,'usage':{'input_tokens':32,'output_tokens':0}}}),('content_block_start',{'type':'content_block_start','index':0,'content_block':{'type':'text','text':''}}),('content_block_delta',{'type':'content_block_delta','index':0,'delta':{'type':'text_delta','text':message['content'][0]['text']}}),('content_block_stop',{'type':'content_block_stop','index':0}),('message_delta',{'type':'message_delta','delta':{'stop_reason':'end_turn','stop_sequence':None},'usage':{'output_tokens':16}}),('message_stop',{'type':'message_stop'})]
        for event,data in events:
            self.wfile.write(('event: '+event+'\ndata: '+json.dumps(data)+'\n\n').encode()); self.wfile.flush()
ThreadingHTTPServer(('127.0.0.1',4010),Handler).serve_forever()
