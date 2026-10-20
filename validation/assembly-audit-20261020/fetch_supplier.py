"""Archive publicly linked LCSC/EasyEDA footprint previews; no account access."""
from pathlib import Path
import urllib.request,re,concurrent.futures,json,csv
OUT=Path(__file__).resolve().parent/'supplier';OUT.mkdir(exist_ok=True)
codes=sorted({r['LCSC Part #'] for r in csv.DictReader(open('production/abx-motion-jlcpcb-bom.csv'))})
def get(code):
 try:
  html=OUT/(code+'.html')
  if not html.exists():
   req=urllib.request.Request('https://www.lcsc.com/product-detail/'+code+'.html',headers={'User-Agent':'Mozilla/5.0'})
   html.write_bytes(urllib.request.urlopen(req,timeout=25).read())
  urls=list(dict.fromkeys(re.findall(r'(?:https:)?//image\.easyeda\.com/component_svgs/prod/[^"<> ]+',html.read_text())))
  ans=[]
  for i,url in enumerate(urls):
   if not url.startswith('https:'):url='https:'+url
   url=url.replace('&amp;','&');fn=OUT/(code+'-'+str(i)+'.svg')
   if not fn.exists():fn.write_bytes(urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=25).read())
   ans.append({'url':url,'file':fn.name,'bytes':fn.stat().st_size})
  return {'code':code,'page':'https://www.lcsc.com/product-detail/'+code+'.html','models':ans}
 except Exception as e:return {'code':code,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
 results=list(ex.map(get,codes))
(OUT/'downloads.json').write_text(json.dumps(results,indent=2)+'\n')
print('Supplier pages:',len(results),'footprints:',sum(len(r.get('models',[]))>1 for r in results))
for r in results:
 if 'error' in r or len(r.get('models',[]))<2:print(r)
