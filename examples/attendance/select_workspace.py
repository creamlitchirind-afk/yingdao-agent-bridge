"""Folder selection entry for the Yingdao attendance workflow."""
from pathlib import Path
import json,sys,os
sys.path.insert(0,str(Path(__file__).resolve().parent))
from inbox import run

def validate_workspace(value):
    base=Path(value).resolve()
    for relative in ('本周周表','基础模板/01_起始总表/演示学期学生课堂纪律总表_空白.xlsx','基础模板/01_起始总表/周汇总空白模板.xlsx','基础模板/课时分组.json'):
        if not (base/relative).exists():raise ValueError('请选择解压后的“考勤工作区”根目录，缺少：'+relative)
    return base

def main(progress=None):
    import tkinter as tk
    from tkinter import filedialog
    window=tk.Tk();window.withdraw();window.attributes('-topmost',True)
    try:value=filedialog.askdirectory(title='请选择考勤工作区（包含本周周表、基础模板）',mustexist=True,parent=window)
    finally:window.destroy()
    if not value:return {'status':'cancelled','message':'已取消，未导入或修改材料。'}
    result=run(validate_workspace(value),progress=progress)
    if result.get('current'):
        try:
            os.startfile(result['current']['output'])
            result['result_open_requested']=True
        except OSError as exc:
            result['result_open_requested']=False
            result['open_warning']=str(exc)
    return result

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--base');parser.add_argument('--progress',action='store_true');parser.add_argument('--graphical-evidence',action='store_true');opts=parser.parse_args()
    if opts.graphical_evidence and not opts.base:parser.error('图形核验必须使用主流程已选择的工作区')
    notify=(lambda message: print(message,flush=True)) if opts.progress else None
    result=run(validate_workspace(opts.base),progress=notify,graphical_evidence=opts.graphical_evidence) if opts.base else main(progress=notify)
    if opts.progress:
        print('[业务结束] '+result['status'],flush=True)
        if result.get('open_warning'):print('[警告汇总] 无法自动打开结果：'+result['open_warning'],flush=True)
    else: print(json.dumps(result,ensure_ascii=False))
