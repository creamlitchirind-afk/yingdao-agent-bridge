"""Fixed text-PDF order template -> native Yingdao PDF extraction and Excel export."""
import argparse
import datetime
import json
from pathlib import Path
import re
import sys
import uuid
from pypdf import PdfReader
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_bridge as bridge
import settings
from builder import build_plan
from excel_common import excel_blocks, disk_rows
from studio_bridge import checked

HEADERS=['订单编号','供应商','日期','金额']
PATTERN=r'订单编号\s*[:：]\s*([^\r\n]+)\s*供应商\s*[:：]\s*([^\r\n]+)\s*日期\s*[:：]\s*(\d{4}-\d{2}-\d{2})\s*金额\s*[:：]\s*(\d+(?:\.\d{1,2})?)(?![\d.])'


def inspect(path):
    path=Path(path).resolve(strict=True)
    if path.suffix.lower()!='.pdf': raise ValueError('Expected a local PDF')
    reader=PdfReader(path)
    if reader.is_encrypted: raise ValueError('Encrypted PDFs are not supported by this template')
    expected=[]
    for index,page in enumerate(reader.pages):
        text=page.extract_text() or ''
        if not text.strip(): raise ValueError(f'Page {index+1} has no text; scanned PDF needs OCR, not this template')
        fields={}; order=[]
        for line in text.splitlines():
            parts=re.split('[:：]',line,maxsplit=1)
            if len(parts)==2 and parts[0].strip() in HEADERS:
                key,value=(p.strip() for p in parts)
                if key in fields: raise ValueError(f'Page {index+1} repeats {key}; one order per page required')
                fields[key]=value;order.append(key)
        if order!=HEADERS: raise ValueError(f'Page {index+1} must contain these labels in order: {HEADERS}')
        if not fields['订单编号'] or not fields['供应商']: raise ValueError('Missing order number or supplier')
        datetime.date.fromisoformat(fields['日期'])
        if not re.fullmatch(r'\d+(?:\.\d{1,2})?',fields['金额']): raise ValueError('Amount must be a nonnegative decimal with up to two places')
        expected.append([fields['订单编号'],fields['供应商'],fields['日期'],float(fields['金额'])])
    if not expected: raise ValueError('No order pages')
    return path,expected


def make_plan(path, output, flow):
    tail=excel_blocks(output)
    blocks=[
        {'prototype':'pdf.extract_text','label':'影刀原生提取PDF全部页面文本','inputs':{'path':str(path),'page_scope':'all','use_password':False},'output':'pdf_text'},
        {'prototype':'programing.variable','label':'按固定订单字段识别记录','inputs':{'value_type':'list','value':{'expression':"__import__('re').findall("+repr(PATTERN)+", pdf_text)"}},'output':'order_matches'},
        {'prototype':'programing.variable','label':'检查遗漏并转换金额','inputs':{'value_type':'list','value':{'expression':"[[a.strip(),b.strip(),c,float(d)] for a,b,c,d in order_matches] if order_matches and len(order_matches) == pdf_text.count('订单编号') else (_ for _ in ()).throw(ValueError('PDF字段缺失或格式不匹配，停止导出'))"}},'output':'extracted_rows'}
    ]+tail
    blocks[3]['inputs']['value']={'expression':'['+repr(HEADERS)+'] + extracted_rows'}
    blocks[3]['label']='构造订单表头和数据行'
    return {'flow_id':flow,'blocks':blocks,'out_parameters':[{'name':'extracted_rows','type':'any'},{'name':'verified_rows','type':'any'}]}


def create(path):
    path,expected=inspect(path)
    bridge.guard()
    stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8]
    directory=settings.state_dir()/'outputs'/'pdf-orders'/stamp;directory.mkdir(parents=True,exist_ok=False)
    output=directory/'订单提取结果.xlsx'
    record={'status':'prepared','source':str(path),'expected':expected}
    def save(): (directory/'verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    save()
    try:
        result=bridge.create_flow('PDF订单提取_'+stamp)
        record['create_result']=result
        flow=result['flow_id'];record['flow_id']=flow;save()
        plan=make_plan(path,output,flow)
        (directory/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
        record['build']=build_plan(plan);save()
        run=checked(bridge.invoke('app.run',{'flow_id':flow,'wait_timeout':20},True));record['run']=run;save()
        if not run.get('run_succeeded'): raise RuntimeError('Run not confirmed successful; inspect same run_id')
        outputs=run.get('result',{}).get('outputs',{})
        disk=disk_rows(output);record['disk_rows']=disk
        if outputs.get('extracted_rows')!=expected or outputs.get('verified_rows')!=[HEADERS]+expected or disk!=[HEADERS]+expected:
            raise RuntimeError('Native extraction or saved Excel differs from independent page-by-page PDF check')
        record['status']='verified';save()
        return {'status':'verified','flow_id':flow,'block_count':len(plan['blocks']),'source':str(path),'headers':HEADERS,'actual':outputs['extracted_rows'],'output':str(output),'evidence':str(directory/'verification.json'),'scope':'固定字段顺序、每页一单的文本PDF；不支持扫描件和任意版式'}
    except Exception as exc:
        record['status']='incomplete';record['error']=str(exc);save()
        raise RuntimeError(f'{exc}; inspect {directory}; do not blindly recreate') from exc


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('action',choices=['inspect','create']);p.add_argument('--pdf',required=True)
    p.add_argument('--write',action='store_true')
    a=p.parse_args()
    if a.action=='create' and not a.write: p.error('--write required')
    if a.action=='create': result=create(a.pdf)
    else:
        path,rows=inspect(a.pdf);result={'source':str(path),'headers':HEADERS,'record_count':len(rows),'preview':rows,'note':'只读检查；尚未生成影刀流程或Excel'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
