from pathlib import Path
import json,re,urllib.request,concurrent.futures,datetime,html
O=Path(__file__).resolve().parent;D=O/'supplier';D.mkdir(exist_ok=True)
rows=json.loads((O/'inventory.json').read_text())
codes={r['props'].get('LCSC','') for r in rows}-{''}
codes.update(['C5930226','C702145','C7481','C7642','C6761','C91875','C162275','C77058','C97890','C492402','C492403','C59782','C88747'])
def req(u):return urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=25).read()
def get(c):
 ans={'code':c,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'jlc_url':f'https://jlcpcb.com/partdetail/Component/{c}','lcsc_url':f'https://www.lcsc.com/product-detail/Component_{c}.html'}
 for kind,url in [('jlc',ans['jlc_url']),('lcsc',ans['lcsc_url'])]:
  fn=D/f'{c}-{kind}.html'
  try:
   if not fn.exists():fn.write_bytes(req(url))
   s=fn.read_text();title=re.search(r'<title>(.*?)</title>',s,re.S);ans[kind+'_title']=html.unescape(title.group(1)) if title else ''
   if kind=='lcsc':
    urls=list(dict.fromkeys(re.findall(r'(?:https:)?//image\.easyeda\.com/component_svgs/prod/[^"<> ]+',s)))
    ans['models']=[]
    for i,u in enumerate(urls[:2]):
     u=html.unescape(('https:'+u) if u.startswith('//') else u);fn=D/f'{c}-{i}.svg'
     if not fn.exists():fn.write_bytes(req(u))
     ans['models'].append({'url':u,'file':fn.name})
   else:
    # Preserve full source for reproducible extraction; avoid confusing recommendation stock with selected-part stock.
    desc=re.search(r'<meta name="description" content="(.*?)"',s,re.S);ans['description']=html.unescape(desc.group(1)) if desc else ''
  except Exception as e:ans[kind+'_error']=str(e)
 return ans
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:res=list(ex.map(get,sorted(codes)))
(D/'catalog.json').write_text(json.dumps(res,indent=2)+'\n')
print('Fetched',len(res),'parts;',sum('jlc_title' in r for r in res),'JLC pages;',sum(len(r.get('models',[]))>1 for r in res),'footprints')
for r in res:
 if r.get('jlc_error') or r.get('lcsc_error') or len(r.get('models',[]))<2:print(r['code'],r.get('jlc_error',''),r.get('lcsc_error',''),'models',len(r.get('models',[])))
