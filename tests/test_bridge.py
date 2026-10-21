import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'examples')]
import studio_bridge as bridge
import builder
from sheet_records import transform,column_properties

class GuardTests(unittest.TestCase):
    def test_account_change_blocks(self):
        with patch('settings.load',return_value={'binding':{'account_fingerprint':'old'}}),patch.object(bridge,'account_fingerprint',return_value='new'),patch.object(bridge,'cli_current') as current:
            with self.assertRaisesRegex(RuntimeError,'changed'): bridge.guard()
            current.assert_not_called()

    def test_wrong_app_and_unallowed_flow(self):
        config={'binding':{'account_fingerprint':'same','app_id':'a','allowed_flows':['safe']}}
        with patch('settings.load',return_value=config),patch.object(bridge,'account_fingerprint',return_value='same'),patch.object(bridge,'cli_current',return_value={'data':{'app':{'app_id':'b'}}}):
            with self.assertRaisesRegex(RuntimeError,'differs'): bridge.guard('safe')
        with patch('settings.load',return_value=config),patch.object(bridge,'account_fingerprint',return_value='same'),patch.object(bridge,'cli_current',return_value={'data':{'app':{'app_id':'a'}}}):
            with self.assertRaisesRegex(RuntimeError,'not enabled'): bridge.guard('other')

    def test_write_requires_explicit_flag(self):
        with patch.object(bridge,'rpc') as rpc:
            with self.assertRaisesRegex(ValueError,'--write'): bridge.invoke('app.run',{'flow_id':'a'})
            rpc.assert_not_called()

    def test_schema_and_bounded_wait(self):
        schema={'type':'object','required':['flow_id'],'properties':{'flow_id':{'type':'string'},'wait_timeout':{'type':'integer'}},'additionalProperties':False}
        with patch.object(bridge,'tool_schema',return_value=schema):
            with self.assertRaises(Exception): bridge.validate('app.run',{'flow_id':3,'wait_timeout':20})
            with self.assertRaisesRegex(ValueError,'Explicit wait'): bridge.validate('app.run',{'flow_id':'a','wait_timeout':60})

    def test_transport_timeout_is_not_retried(self):
        with tempfile.TemporaryDirectory() as temp,patch('settings.state_dir',return_value=Path(temp)),patch('settings.load',return_value={'binding':{'app_id':'a'}}),patch.object(bridge,'validate'),patch.object(bridge,'guard'),patch.object(bridge,'rpc',side_effect=TimeoutError('timed out')) as rpc:
            with self.assertRaisesRegex(RuntimeError,'timed out'): bridge.invoke('app.run',{'flow_id':'x','wait_timeout':20},True)
            self.assertEqual(rpc.call_count,1)
            evidence=json.loads(next(Path(temp).rglob('*.json')).read_text())
            self.assertEqual(evidence['status'],'uncertain')

    def test_insertion_validation_is_not_partial_failure(self):
        self.assertIn('validation_errors',bridge.checked({'structuredContent':{'validation_errors':['not filled yet']}}))
        for data in [{'failed_count':1},{'fill_errors':['bad value']},{'success':False}]:
            with self.assertRaises(RuntimeError): bridge.checked({'structuredContent':data})

class BuilderTests(unittest.TestCase):
    def test_resume_pending_fill_does_not_insert_again(self):
        import hashlib
        plan={'flow_id':'f','blocks':[{'prototype':'p','inputs':{'x':1}}]}
        digest=hashlib.sha256(json.dumps(plan,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            journal=Path(temp)/'j.json'
            journal.write_text(json.dumps({'plan_hash':digest,'app_id':'a','account_fingerprint':'h','stage':'fill_pending','inserted':[{'block_id':'b','slots':[]}],'filled':0}))
            with patch.object(builder,'preflight'),patch.object(bridge,'guard'),patch('settings.load',return_value={'binding':{'app_id':'a','account_fingerprint':'h'}}),patch.object(bridge,'inspect_flow',return_value={'blocks':[{'block_id':'b'}]}),patch.object(bridge,'invoke',return_value={'structuredContent':{'success':True}}) as invoke:
                builder.build_plan(plan,journal)
                self.assertEqual([call.args[0] for call in invoke.call_args_list],['flow.fill_blocks','app.save'])
                self.assertEqual(json.loads(journal.read_text())['stage'],'complete')

    def test_resume_uncertain_insertion_is_refused(self):
        import hashlib
        plan={'flow_id':'f','blocks':[{'prototype':'p'}]}
        digest=hashlib.sha256(json.dumps(plan,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            journal=Path(temp)/'j.json'; journal.write_text(json.dumps({'plan_hash':digest,'app_id':'a','account_fingerprint':'h','stage':'insert_uncertain'}))
            with patch.object(builder,'preflight'),patch.object(bridge,'guard'),patch('settings.load',return_value={'binding':{'app_id':'a','account_fingerprint':'h'}}),patch.object(bridge,'invoke') as invoke:
                with self.assertRaisesRegex(RuntimeError,'uncertain'): builder.build_plan(plan,journal)
                invoke.assert_not_called()

class DataTests(unittest.TestCase):
    header=['报名编号','姓名','报名项目','联系方式','确认状态']
    def test_column_attribute_order_is_not_a_width_change(self):
        import xml.etree.ElementTree as ET
        ns={'s':'urn:test'}
        first=ET.fromstring('<sheet xmlns="urn:test"><cols><col width="22" min="1" max="1"/></cols></sheet>')
        second=ET.fromstring('<sheet xmlns="urn:test"><cols><col max="1" min="1" width="22"/></cols></sheet>')
        self.assertEqual(column_properties(first,ns),column_properties(second,ns))
        second.find('s:cols/s:col',ns).set('width','23')
        self.assertNotEqual(column_properties(first,ns),column_properties(second,ns))
    def test_filter_deduplicate_and_keep_zero(self):
        row=['001','小林','绘画','000123','已确认']
        result=transform([self.header,row,row,['002','小陈','书法','','已确认'],['003','小周','摄影','000222','已取消']])
        self.assertEqual(result['rows'],[row[:4]])
        self.assertEqual(len(result['issues']),3)

    def test_conflicting_duplicate_is_not_silently_chosen(self):
        with self.assertRaisesRegex(ValueError,'Conflicting'): transform([self.header,['001','甲','绘画','0001','已确认'],['001','乙','绘画','0001','已确认']])

    def test_numeric_contact_is_not_guessed(self):
        with self.assertRaisesRegex(ValueError,'leading zeros'): transform([self.header,['001','甲','绘画',123,'已确认']])

if __name__=='__main__': unittest.main()
