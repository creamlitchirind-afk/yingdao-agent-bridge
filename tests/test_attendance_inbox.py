import json,sys,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'examples/attendance'))
import inbox
DATA=ROOT/'examples/attendance/data'

class InboxTests(unittest.TestCase):
 def test_graphical_disagreement_does_not_publish(self):
  with tempfile.TemporaryDirectory() as tmp:
   b=Path(tmp);self.setup_base(b);self.add(b,1)
   for name in ('图形课堂事件.json','图形晚点名事件.json'):
    (b/name).write_text('[]',encoding='utf-8')
   with self.assertRaisesRegex(ValueError,'图形计算与快照核验不一致'):
    inbox.run(b,graphical_evidence=True)
   self.assertFalse((b/'当前总表.json').exists())
   self.assertTrue((b/'本周周表/第一周').exists())
   self.assertFalse((b/'本周周表/第一周-已导入').exists())
 def test_graphical_match_is_by_person_not_only_total(self):
  with tempfile.TemporaryDirectory() as tmp:
   b=Path(tmp);source=b/'本周周表/第一周';source.mkdir(parents=True)
   attendance=source/'考勤表/a.xlsx';late=source/'晚点名/b.xlsx'
   rows=[['学院甲','一班','张一',0.5,str(attendance)],['学院甲','一班','李二',1,str(attendance)]]
   (b/'图形课堂事件.json').write_text(json.dumps(rows),encoding='utf-8')
   (b/'图形晚点名事件.json').write_text(json.dumps([['学院甲','一班','张一',3,str(late)]]),encoding='utf-8')
   events=[dict(college='学院甲',**{'class':'一班'},name=n,hours=h,file=f,kind=k) for n,h,f,k in [('张一',0.5,'snapshot/a.xlsx','课堂'),('李二',1,'snapshot/a.xlsx','课堂'),('张一',3,'snapshot/b.xlsx','晚点名')]]
   week=dict(week=1,events=events)
   self.assertTrue(all(x['matched'] for x in inbox.verify_graphical_outputs(b,source,week)))
   rows[0][3]=1;rows[1][3]=0.5
   (b/'图形课堂事件.json').write_text(json.dumps(rows),encoding='utf-8')
   with self.assertRaisesRegex(ValueError,'不一致'):inbox.verify_graphical_outputs(b,source,week)
 def test_real_windows_locked_preview(self):
  import ctypes
  from ctypes import wintypes
  kernel=ctypes.WinDLL('kernel32',use_last_error=True)
  kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
  kernel.CreateFileW.restype=wintypes.HANDLE
  kernel.CloseHandle.argtypes=[wintypes.HANDLE]
  with tempfile.TemporaryDirectory() as tmp:
   b=Path(tmp);self.setup_base(b)
   for n in (1,2,3):self.add(b,n)
   latest=b/'当前总表/最新总表.xlsx';latest.parent.mkdir();latest.write_bytes(b'opened preview')
   h=kernel.CreateFileW(str(latest),0x80000000,1,None,3,0,None)
   self.assertNotEqual(h,ctypes.c_void_p(-1).value)
   try:
    result=inbox.run(b)
    self.assertEqual(result['current']['week'],3)
    self.assertFalse(result['latest_preview']['updated'])
    self.assertEqual(latest.read_bytes(),b'opened preview')
    self.assertEqual(inbox.run(b)['status'],'no_pending')
    self.assertEqual(len(list((b/'总表版本').iterdir())),3)
   finally:kernel.CloseHandle(h)
   self.assertTrue(inbox.run(b)['latest_preview']['updated'])
   self.assertEqual(latest.read_bytes(),Path(result['current']['output']).read_bytes())
 def setup_base(self,base):
  shutil.copytree(DATA/'01_起始总表',base/'基础模板/01_起始总表')
  shutil.copy2(DATA/'课时分组.json',base/'基础模板/课时分组.json')
  (base/'本周周表').mkdir()
 def add(self,base,n):shutil.copytree(DATA/'02_已提交材料'/f'第{n}周',base/'本周周表'/inbox.NAMES[n])
 def test_sequential_versions_recovery_and_no_repeat(self):
  with tempfile.TemporaryDirectory() as tmp:
   b=Path(tmp);self.setup_base(b);self.add(b,1)
   first=inbox.run(b);self.assertEqual(first['current']['week'],1)
   old=Path(first['current']['output']).read_bytes()
   self.add(b,2);self.add(b,3)
   # Simulate crash after publication but before the marking rename.
   original_archive=inbox.archive_committed
   def crash(b,c,*args):
    if c and c.get('week')==2:raise OSError('rename interrupted')
    return original_archive(b,c,*args)
   with patch.object(inbox,'archive_committed',side_effect=crash):
    with self.assertRaises(OSError):inbox.run(b)
   self.assertEqual(inbox.read_json(b/'当前总表.json')['week'],2)
   result=inbox.run(b);self.assertEqual(result['current']['week'],3)
   self.assertEqual(old,Path(first['current']['output']).read_bytes())
   self.assertTrue(all((b/'本周周表'/(inbox.NAMES[n]+'-已导入')).is_dir() for n in (1,2,3)))
   self.assertEqual(inbox.run(b)['status'],'no_pending')
   self.assertEqual(len(list((b/'总表版本').iterdir())),3)
   checks=result['imported'][0]['checks']
   self.assertEqual((checks[0]['students'],checks[0]['hours']),(124,483.5))
 def test_gap_and_failure_preserve_current(self):
  with tempfile.TemporaryDirectory() as tmp:
   b=Path(tmp);self.setup_base(b);self.add(b,3)
   with self.assertRaises(ValueError):inbox.run(b)
   self.assertFalse((b/'当前总表.json').exists())
  with tempfile.TemporaryDirectory() as tmp:
   b=Path(tmp);self.setup_base(b);self.add(b,1);inbox.run(b);before=(b/'当前总表.json').read_bytes();self.add(b,2)
   with patch.object(inbox.engine,'run',side_effect=ValueError('bad material')):
    with self.assertRaises(ValueError):inbox.run(b)
   self.assertEqual(before,(b/'当前总表.json').read_bytes())
   self.assertTrue((b/'本周周表/第二周').exists())
   self.assertFalse((b/'本周周表/第二周-已导入').exists())

if __name__=='__main__':unittest.main()
