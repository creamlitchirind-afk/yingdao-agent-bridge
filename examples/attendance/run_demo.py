"""Portable three-week example; outputs stay in local state by default."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from engine import run

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--input',type=Path,default=Path(__file__).parent/'data')
 p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[2]/'.local/attendance-output')
 a=p.parse_args()
 for week in (1,2,3):
  result=run(a.input,a.output,week)
  print(json.dumps({k:result[k] for k in ('output','imported_week','total_hours','abnormal_students')},ensure_ascii=False))
if __name__=='__main__':main()
