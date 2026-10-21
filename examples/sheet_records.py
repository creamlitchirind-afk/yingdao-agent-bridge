"""Fixed registration extraction and column-mapped template fill through native Excel blocks."""
import argparse,datetime,hashlib,inspect,json,shutil,sys,uuid,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import studio_bridge as bridge
import settings
from builder import build_plan
from studio_bridge import checked


HEADERS=['编号','姓名','项目','联系电话']


def transform(rows):
    required=['报名编号','姓名','报名项目','联系方式','确认状态']
    if not rows: raise ValueError('No source rows')
    header=rows[0]
    if len(set(header))!=len(header) or any(h not in header for h in required): raise ValueError('Missing or duplicate source headers')
    ix=[header.index(h) for h in required]; accepted=[]; issues=[]; seen={}
    for row_number,row in enumerate(rows[1:],2):
        row=list(row)+[None]*max(0,len(header)-len(row))
        if all(v in (None,'') for v in row): continue
        if row[ix[4]]!='已确认':
            issues.append({'row':row_number,'reason':'非已确认'});continue
        values=[row[i] for i in ix[:4]]
        if any(v is None or (isinstance(v,str) and not v.strip()) for v in values):
            issues.append({'row':row_number,'reason':'缺少必填字段'});continue
        if any(not isinstance(v,str) for v in values): raise ValueError('Identifiers and contact fields must be stored as text; do not guess lost leading zeros')
        values=[v.strip() for v in values]
        if any(v.startswith('=') for v in values): raise ValueError('Formula-like source text requires an explicit handling rule')
        key=values[0]
        if key in seen:
            if seen[key]!=values: raise ValueError('Conflicting duplicate registration ID: '+key)
            issues.append({'row':row_number,'reason':'完全重复编号'});continue
        seen[key]=values;accepted.append(values)
    return {'rows':accepted,'issues':issues,'source_count':len(rows)-1,'accepted_count':len(accepted)}


def colnum(label):
    n=0
    for c in label: n=n*26+ord(c)-64
    return n


def column_properties(tree,ns):
    # XML attribute order may change across openpyxl versions; compare properties.
    return sorted(tuple(sorted(column.attrib.items())) for column in tree.findall('s:cols/s:col',ns))


def grid(path):
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    cells={}
    with zipfile.ZipFile(path) as z:
        sheets=[n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
        if sheets!=['xl/worksheets/sheet1.xml']: raise ValueError('This fixed module requires one worksheet')
        wb=ET.fromstring(z.read('xl/workbook.xml'))
        if wb.find('s:sheets/s:sheet',ns).get('name')!='Sheet': raise ValueError('This version expects worksheet named Sheet')
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist(): shared=[''.join(n.text or '' for n in x.findall('.//s:t',ns)) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
        tree=ET.fromstring(z.read(sheets[0]))
        if tree.find('s:mergeCells',ns) is not None: raise ValueError('Merged cells not supported in this fixed template')
        for cell in tree.findall('s:sheetData/s:row/s:c',ns):
            ref=cell.get('r');typ=cell.get('t');v=cell.find('s:v',ns)
            if cell.find('s:f',ns) is not None: raise ValueError('Formula workbook not supported by this fixed module')
            if typ=='inlineStr': value=''.join(n.text or '' for n in cell.findall('.//s:t',ns))
            elif typ=='s': value=shared[int(v.text)]
            elif v is None: value=None
            elif typ in ('n',None): value=float(v.text)
            else: value=v.text
            if value not in (None,''): cells[ref]=value
        return cells,column_properties(tree,ns)


def rows_from_grid(cells):
    import re
    maxrow=max((int(re.search(r'\d+',r)[0]) for r in cells),default=0)
    maxcol=max((colnum(re.match(r'[A-Z]+',r)[0]) for r in cells),default=0)
    rows=[[None]*maxcol for _ in range(maxrow)]
    for ref,val in cells.items(): rows[int(re.search(r'\d+',ref)[0])-1][colnum(re.match(r'[A-Z]+',ref)[0])-1]=val
    return rows


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def create(source,template=None):
    source=Path(source).resolve(strict=True)
    if source.suffix.lower()!='.xlsx': raise ValueError('Expected .xlsx')
    source_cells,_=grid(source);expected=transform(rows_from_grid(source_cells));source_hash=digest(source)
    if not expected['rows']: raise ValueError('No eligible records; no output created')
    target_columns={h:chr(65+i) for i,h in enumerate(HEADERS)};before={};before_width=b'';start=2
    template_hash=None
    if template:
        template=Path(template).resolve(strict=True)
        if template.suffix.lower()!='.xlsx': raise ValueError('Expected .xlsx template')
        before,before_width=grid(template);template_hash=digest(template)
        header={ref[:-1]:v for ref,v in before.items() if ref.endswith('3') and ref[:-1].isalpha()}
        if any(list(header.values()).count(h)!=1 for h in HEADERS): raise ValueError('Template row 3 must contain unique 编号/姓名/项目/联系电话 headers')
        target_columns={h:next(c for c,v in header.items() if v==h) for h in HEADERS};start=4
        if len(expected['rows'])>10: raise ValueError('Template data area is rows 4..13 (10 records)')
        if any(f'{c}{r}' in before for c in target_columns.values() for r in range(4,14)): raise ValueError('Template mapped data area is not empty; refusing overwrite')
    bridge.guard()
    stamp=datetime.datetime.now().strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8]
    directory=settings.state_dir()/'outputs'/'sheet-records'/stamp;directory.mkdir(parents=True)
    output=directory/('已填名单.xlsx' if template else '提取名单.xlsx')
    if template: shutil.copy2(template,output)
    record={'status':'prepared','source':str(source),'template':str(template) if template else None,'expected':expected,'output':str(output)}
    def save(): (directory/'verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    save()
    try:
        result=bridge.create_flow(('表格填报_' if template else '表格提取_')+stamp)
        record['create_result']=result;flow=result['flow_id'];record['flow_id']=flow;save()
        v=lambda n:{'variable':n}
        function=inspect.getsource(transform)
        expression="(lambda ns: (exec("+repr(function)+",ns), ns['transform'](ns['rows']))[1])({'rows':source_rows})"
        blocks=[
            {'prototype':'excel.launch','label':'打开来源表（不保存）','inputs':{'launch_way':'open','driver_way':'openpyxl','open_filename':str(source),'isvisible':False},'output':'source_book'},
            {'prototype':'excel.read_data_from_workbook','label':'读取实际来源表','inputs':{'workbook':v('source_book'),'read_way':'used_range','sheet_name':'Sheet','has_header_row':False},'output':'source_rows'},
            {'prototype':'excel.close','label':'关闭来源不保存','inputs':{'operation':'close_specified','excel_instance':v('source_book'),'close_way':'notsave','close_process':'office','task_kill':False}},
            {'prototype':'programing.variable','label':'按表头筛选、检查和去重','inputs':{'value_type':'dict','value':{'expression':expression}},'output':'extraction'},
            {'prototype':'excel.launch','label':'打开模板副本' if template else '新建提取结果','inputs':dict(launch_way='open' if template else 'create',driver_way='openpyxl',isvisible=False,**({'open_filename':str(output)} if template else {'save_filename':str(output)})),'output':'target_book'}]
        if not template:
            blocks.append({'prototype':'excel.write_data_to_workbook','label':'写入结果表头','inputs':{'workbook':v('target_book'),'write_range':'area','row_num':1,'column_name':'A','content':{'expression':repr([HEADERS])},'sheet_name':'Sheet'}})
        for i,h in enumerate(HEADERS):
            blocks.append({'prototype':'excel.write_data_to_workbook','label':'按列填写'+h,'inputs':{'workbook':v('target_book'),'write_range':'area','row_num':start,'column_name':target_columns[h],'content':{'expression':"[[r["+str(i)+"]] for r in extraction['rows']]"},'sheet_name':'Sheet'}})
        blocks.extend([
            {'prototype':'excel.read_data_from_workbook','label':'读取输出核对','inputs':{'workbook':v('target_book'),'read_way':'used_range','sheet_name':'Sheet','has_header_row':False},'output':'output_rows'},
            {'prototype':'excel.save','label':'保存结果副本','inputs':{'excel_instance':v('target_book'),'save_way':'save','is_close_after_save':True}}])
        plan={'flow_id':flow,'blocks':blocks,'out_parameters':[{'name':'extraction','type':'any'},{'name':'output_rows','type':'any'}]}
        (directory/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
        record['build']=build_plan(plan);save()
        run=checked(bridge.invoke('app.run',{'flow_id':flow,'wait_timeout':20},True));record['run']=run;save()
        if not run.get('run_succeeded'): raise RuntimeError('Run failed or pending; inspect same run_id')
        actual=run['result']['outputs']['extraction']
        if actual!=expected: raise RuntimeError('Source extraction mismatch')
        after,width=grid(output);target=dict(before)
        if not template: target.update({f'{target_columns[h]}1':h for h in HEADERS})
        for rownum,row in enumerate(expected['rows'],start):
            for i,h in enumerate(HEADERS): target[f'{target_columns[h]}{rownum}']=row[i]
        if after!=target: raise RuntimeError('Filled cells or protected content differ from expected')
        if template and width!=before_width: raise RuntimeError('Template column widths changed')
        if digest(source)!=source_hash or (template and digest(template)!=template_hash): raise RuntimeError('Original input changed')
        record.update(status='verified',actual=actual,preserved_originals=True,preserved_unmapped_cells=True);save()
        return {'status':'verified','flow_id':flow,'block_count':len(blocks),'actual':actual,'output':str(output),'evidence':str(directory/'verification.json')}
    except Exception as exc:
        record.update(status='incomplete',error=str(exc));save();raise RuntimeError(f'{exc}; inspect {directory}') from exc


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');p=argparse.ArgumentParser();p.add_argument('action',choices=['inspect','extract','fill']);p.add_argument('--source',required=True);p.add_argument('--template');p.add_argument('--write',action='store_true');a=p.parse_args()
    if a.action!='inspect' and not a.write: p.error('--write required')
    if a.action=='inspect': result=transform(rows_from_grid(grid(a.source)[0]))
    else:
        if a.action=='fill' and not a.template: p.error('--template required')
        result=create(a.source,a.template if a.action=='fill' else None)
    print(json.dumps(result,ensure_ascii=False,indent=2))
