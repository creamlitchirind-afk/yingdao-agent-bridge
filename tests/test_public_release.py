import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'examples')]
import shop_orders
import studio_bridge as bridge

spec=importlib.util.spec_from_file_location('skill_installer',ROOT/'tools/install_kunar_skill.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
spec=importlib.util.spec_from_file_location('release_packager',ROOT/'tools/package_release.py')
packager=importlib.util.module_from_spec(spec);spec.loader.exec_module(packager)

class PublicReleaseTests(unittest.TestCase):
    def test_shop_without_binding_stops_before_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=Path(tmp)/'config.json';cfg.write_text('{}',encoding='utf-8')
            with patch.dict(os.environ,{'YINGDAO_SHOP_CONFIG':str(cfg)}),patch.object(shop_orders.settings,'load',return_value={}),patch.object(bridge,'endpoint') as endpoint,patch.object(shop_orders,'TARGET_APP',None):
                with self.assertRaisesRegex(RuntimeError,'setup'):shop_orders.configure()
                endpoint.assert_not_called()

    def test_setup_wrong_app_does_not_bind_or_write(self):
        with patch.object(shop_orders,'configure'),patch.object(shop_orders,'TARGET_APP',None),patch.object(bridge,'cli_current',return_value={'data':{'app':{'app_id':'another-app'}}}),patch.object(shop_orders.settings,'save') as save:
            with self.assertRaisesRegex(RuntimeError,'currently open'):shop_orders.setup('user-chosen-app')
            save.assert_not_called()

    def test_installer_backup_and_runtime_are_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo';skills=Path(tmp)/'workspace/skills'
            for folder in ['.venv/Scripts','scripts','docs','skills/yingdao-shop-orders']:(root/folder).mkdir(parents=True,exist_ok=True)
            for name,content in {'SKILL.md':'bridge','README.md':'readme','scripts/agent_entry.py':'launcher','docs/guide.md':'guide','.venv/Scripts/python.exe':'fixture','skills/yingdao-shop-orders/SKILL.md':'shop-v1'}.items():(root/name).write_text(content,encoding='utf-8')
            unrelated=skills/'user-skill';unrelated.mkdir(parents=True);(unrelated/'SKILL.md').write_text('keep',encoding='utf-8')
            result=installer.install(root,skills,'yingdao-shop-orders')
            destination=Path(result['installed'])
            self.assertEqual(json.loads((destination/'.local/runtime.json').read_text())['repo'],str(root.resolve()))
            with self.assertRaises(SystemExit):installer.install(root,skills,'yingdao-shop-orders')
            (root/'skills/yingdao-shop-orders/SKILL.md').write_text('shop-v2',encoding='utf-8')
            result=installer.install(root,skills,'yingdao-shop-orders',True)
            self.assertEqual((Path(result['backup'])/'SKILL.md').read_text(),'shop-v1')
            self.assertEqual((destination/'SKILL.md').read_text(),'shop-v2')
            self.assertEqual((unrelated/'SKILL.md').read_text(),'keep')
            self.assertNotIn('skills',Path(result['backup']).relative_to(skills.parent).parts)

    def test_flow_cleanup_rejects_main_and_forcing(self):
        with patch.object(bridge,'validate'),patch.object(bridge,'rpc') as rpc:
            with self.assertRaisesRegex(ValueError,'main'):bridge.invoke('app.delete_flow',{'flow_ids':['main']},True)
            with self.assertRaisesRegex(ValueError,'Forced'):bridge.invoke('app.rename_flow',{'flow_id':'owned','force':True},True)
            rpc.assert_not_called()

    def test_flow_cleanup_checks_every_requested_flow(self):
        def guard(flow):
            if flow=='unallowed':raise RuntimeError('not enabled')
        with patch.object(bridge,'validate'),patch.object(bridge,'guard',side_effect=guard),patch.object(bridge,'rpc') as rpc:
            with self.assertRaisesRegex(RuntimeError,'not enabled'):bridge.invoke('app.delete_flow',{'flow_ids':['allowed','unallowed']},True)
            rpc.assert_not_called()

    def test_release_includes_assets_but_excludes_private_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ['skills/demo/.local/runtime.json','skills/demo/config.json','skills/demo/SKILL.md','examples/shop_orders.cmd','examples/assets/shop-report-empty.xlsx']:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('fixture',encoding='utf-8')
            files={p.relative_to(root).as_posix() for p in packager.source_files(root)}
            self.assertIn('examples/shop_orders.cmd',files)
            self.assertIn('examples/assets/shop-report-empty.xlsx',files)
            self.assertIn('skills/demo/SKILL.md',files)
            self.assertNotIn('skills/demo/.local/runtime.json',files)
            self.assertNotIn('skills/demo/config.json',files)

if __name__=='__main__':unittest.main()
