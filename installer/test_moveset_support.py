"""Moveset dependency evidence, version choice and reversible visual overlays."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import batch_import
import catalog
import moveset_support as support
import plugin_dependencies as dependencies
import plugin_runtime
import test_modmanager as fixture

m = fixture.m
BASE, SKIN, THIRD = ['mod-' + c * 16 for c in 'abc']

def record(name, value, plugin=False):
    entry = dict(path='plugin.nro' if plugin else 'ui/replace/a.bntx', sha256=value)
    if plugin: entry.update(kind='plugin', module='sky_own')
    return dict(name=name, entries=[entry])

class EvidenceTests(unittest.TestCase):
    def test_alias_claims_use_explicit_destinations_and_validate_config_bytes(self):
        import drybowser
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'assets/config.json';path.parent.mkdir()
            path.write_text(json.dumps({'share-to-added':{'source':['0xabc',123,True]},
                                        'new-dir-files':{'directory':['0xdef']}}))
            entry=dict(path='config.json',sha256=drybowser.digest(path))
            with patch('catalog.location',return_value=root):
                self.assertEqual({0xabc,123},support.shared_destinations(root,SKIN,entry))
                path.write_text('{}')
                with self.assertRaisesRegex(ValueError,'veraendert'):support.shared_destinations(root,SKIN,entry)

    def test_marker_requires_matching_gameplay_code_not_just_any_plugin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'assets/own.nro';path.parent.mkdir();path.write_bytes(b'own unrelated plugin')
            records = {SKIN: dict(name='Unknown future skin', entries=[dict(path='fighter/own/model/body/c120/future.marker')]),
                       BASE: dict(name='Any plugin',entries=[dict(path='own.nro',kind='plugin')])}
            with patch('catalog.location', return_value=root):
                self.assertIn(SKIN, support.diagnostics(root, records))
                path.write_bytes(b'own /fighter/own/model/body/cfuture.marker')
                self.assertEqual({},support.diagnostics(root,records))

    def test_marker_diagnostic_and_plain_costume_hint(self):
        skin = dict(name='Ordinary skin', entries=[dict(path='fighter/example/model/body/c01/model.numdlb')])
        self.assertIn('2. Kostuem', support.selection_hint(skin))
        self.assertEqual({}, support.diagnostics(Path('.'), {SKIN:skin}))
        self.assertIn('120',support.selection_hint(dict(entries=[dict(path='fighter/example/model/body/c120/model.numdlb')])))

    def test_versions_and_fingerprints_follow_game_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp);(repo/'build').mkdir()
            for game,expected in [('13.0.4','5.0.6'),('13.0.5','6.0.0')]:
                (repo/'build/state.json').write_text(json.dumps(dict(game_version=game)))
                selected=dependencies.definition(repo,'csk')
                self.assertEqual(expected,selected['version'])
                self.assertEqual(selected['sha256'],dependencies.fingerprint(['csk'],repo)['csk'])
            (repo/'build/state.json').write_text(json.dumps(dict(game_version='future')))
            with self.assertRaisesRegex(ValueError,'future'): dependencies.definition(repo,'csk')

    def test_extended_assets_require_framework_without_a_bundled_plugin(self):
        self.assertEqual(['csk'],dependencies.required([],['fighter/future/model/body/c120/model.numdlb']))
        self.assertEqual([],dependencies.required([],['fighter/future/model/body/c01/model.numdlb']))

    def test_boot_library_names_are_kept_and_collisions_rejected(self):
        self.assertEqual('libfuture.nro',plugin_runtime.boot_name(dict(path='ultimate/mods/own/libfuture.nro',module='sky_future')))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a=root/'a.nro';b=root/'b.nro';dest=root/'boot.nro'
            a.write_bytes(b'own one');b.write_bytes(b'own two')
            plugin_runtime.copy_boot_plugin(a,dest)
            plugin_runtime.copy_boot_plugin(a,dest)
            with self.assertRaisesRegex(ValueError,'gleichem Dateinamen'):
                plugin_runtime.copy_boot_plugin(b,dest)
            self.assertEqual(b'own one',dest.read_bytes())

    def test_new_smashline_api_requires_explicit_matching_framework(self):
        item=dict(path='ultimate/mods/own/plugin.nro',module='sky_own',smashline=True,smashline_api='2.0')
        with self.assertRaisesRegex(ValueError,'2.0-APIs'):
            plugin_runtime.core_dependencies([item],[])
        supplied=dict(path='ultimate/mods/framework/libsmashline_plugin.nro',module='sky_smashline',smashline=True)
        self.assertEqual(['nro_hook'],plugin_runtime.core_dependencies([item,supplied],[]))
        self.assertIn('/v1.6.8/',plugin_runtime.DEPENDENCIES['smashline'][1])

    def test_cache_rejects_a_changed_framework_definition(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp);(repo/'build').mkdir();(repo/'build/state.json').write_text(json.dumps(dict(game_version='13.0.5')))
            import runtime_cache
            with self.assertRaisesRegex(ValueError,'Gameplay-Bibliotheken'):
                runtime_cache.plugin(repo,dict(dependencies=['csk'],dependency_fingerprint={'csk':'old'}))

    def test_only_explicit_asset_override_wins(self):
        records={BASE:record('Base','base'),SKIN:record('Skin','skin')}
        with self.assertRaises(ValueError):support.overlay_groups(records,{BASE:{},SKIN:{}})
        groups=support.overlay_groups(records,{BASE:{},SKIN:dict(overlays=[BASE])})
        self.assertNotIn(BASE,groups)
        self.assertEqual('skin',groups[SKIN]['ui/replace/a.bntx'])

    def test_transitive_precedence_cycle_and_unrelated_conflicts(self):
        records={BASE:record('Base','base'),SKIN:record('Skin','skin'),THIRD:record('Patch','patch')}
        status={BASE:{},SKIN:dict(overlays=[BASE]),THIRD:dict(overlays=[SKIN])}
        self.assertIn(THIRD,support.overlay_groups(records,status))
        status[BASE]=dict(overlays=[THIRD])
        with self.assertRaisesRegex(ValueError,'Zyklische'):support.overlay_groups(records,status)
        status[BASE]={};status[THIRD]={}
        with self.assertRaisesRegex(ValueError,'Konflikt'):support.overlay_groups(records,status)

    def test_overlay_cannot_hide_plugin_version_conflict(self):
        with self.assertRaisesRegex(ValueError,'Konflikt'):
            support.overlay_groups({BASE:record('Base','a',True),SKIN:record('Patch','b',True)},
                                   {BASE:{},SKIN:dict(overlays=[BASE])})

    def test_overlay_replaces_root_archive_config_without_affecting_unrelated_mods(self):
        records={BASE:dict(name='Base',entries=[dict(path='config.json',sha256='base',metadata=True)]),
                 SKIN:dict(name='Skin',entries=[dict(path='config.json',sha256='skin',metadata=True)]),
                 THIRD:dict(name='Other',entries=[dict(path='config.json',sha256='other',metadata=True)])}
        groups=support.overlay_groups(records,{BASE:{},SKIN:dict(overlays=[BASE]),THIRD:{}})
        self.assertNotIn(BASE,groups)
        self.assertEqual('skin',groups[SKIN]['config.json'])
        self.assertEqual('other',groups[THIRD]['config.json'])

class TransactionTests(unittest.TestCase):
    setUp=fixture.ManagerTests.setUp
    mod=fixture.ManagerTests.mod

    def test_independent_text_patches_survive_normal_batch_install(self):
        name='ui/message/msg_name.xmsbt'
        first=self.mod('First future fighter',name,'<xmsbt><entry label="first"><text>One</text></entry></xmsbt>')
        lower=m.install(self.repo,first)['state']['mods'][0]['id']
        second=self.mod('Second future fighter',name,'<xmsbt><entry label="second"><text>Two</text></entry></xmsbt>')
        (second/name).write_text((second/name).read_text(),encoding='utf-16')
        plan=m.batch_preview(self.repo,[second])
        self.assertEqual('ready',plan['items'][0]['status'],plan)
        result=m.batch_install(self.repo,plan['job_id'],plan['token'])
        self.assertEqual(1,result['installed'],result)
        state=m.load(self.repo);higher=next(k for k in state['mods'] if k!=lower)
        profile=m.root(self.repo)/'profile/ultimate/mods'
        self.assertTrue((profile/lower/name).is_file())
        self.assertTrue((profile/higher/name).is_file())
        m.profile_valid(self.repo,force=True)
        third=self.mod('Conflicting text',name,'<xmsbt><entry label="second"><text>Changed</text></entry></xmsbt>')
        conflict=m.batch_preview(self.repo,[third])
        self.assertEqual('conflict',conflict['items'][0]['status'])
        self.assertIn(higher,conflict['items'][0]['conflict_ids'])
        conflict=batch_import.configure(SimpleNamespace(**vars(m)),self.repo,conflict['job_id'],conflict['token'],{'0':'overlay'})
        result=m.batch_install(self.repo,conflict['job_id'],conflict['token'])
        self.assertEqual(1,result['installed'],result)
        newest=next(k for k in m.load(self.repo)['mods'] if k not in (lower,higher))
        self.assertTrue((profile/lower/name).is_file())
        self.assertFalse((profile/higher/name).exists())
        self.assertTrue((profile/newest/name).is_file())
        m.profile_valid(self.repo,force=True)

    def test_xml_entities_cannot_enter_a_shared_text_patch(self):
        name='ui/message/msg_name.xmsbt'
        m.install(self.repo,self.mod('First text',name,'<xmsbt><entry label="first"><text>One</text></entry></xmsbt>'))
        bad=self.mod('Unsafe text',name,'<!DOCTYPE xmsbt [<!ENTITY e "x">]><xmsbt><entry label="second"><text>&e;</text></entry></xmsbt>')
        plan=m.batch_preview(self.repo,[bad])
        self.assertEqual('invalid',plan['items'][0]['status'])
        self.assertIn('XML-Entitaeten',plan['items'][0]['message'])

    def test_archive_alias_claim_masks_old_base_asset_and_disable_restores_it(self):
        alias='fighter/example/model/spear2/c00/model.numdlb'
        base=self.mod('Future base',content='base')
        target=base/alias;target.parent.mkdir(parents=True);target.write_bytes(b'old physical model')
        lower=m.install(self.repo,base)['state']['mods'][0]['id']
        skin=self.mod('Future visual patch',content='patch')
        (skin/'config.json').write_text(json.dumps({'share-to-added':{
            'fighter/example/model/spear/c00/model.numdlb':[alias]}}))
        plan=m.batch_preview(self.repo,[skin])
        plan=batch_import.configure(SimpleNamespace(**vars(m)),self.repo,plan['job_id'],plan['token'],{'0':'overlay'})
        m.batch_install(self.repo,plan['job_id'],plan['token'])
        higher=next(k for k in m.load(self.repo)['mods'] if k!=lower)
        profile=m.root(self.repo)/'profile/ultimate/mods'
        self.assertFalse((profile/lower/alias).exists())
        self.assertEqual(b'old physical model',(catalog.location(self.repo,lower)/'assets'/alias).read_bytes())
        m.profile_valid(self.repo,force=True)
        m.change(self.repo,higher,'enable',False)
        self.assertEqual(b'old physical model',(profile/lower/alias).read_bytes())
        m.undo(self.repo);m.profile_valid(self.repo,force=True)
        self.assertFalse((profile/lower/alias).exists())

    def test_base_can_be_added_below_an_existing_skin(self):
        skin=self.mod('Existing skin',content='skin')
        higher=m.install(self.repo,skin)['state']['mods'][0]['id']
        base=self.mod('Missing base',content='base')
        (base/'ui/replace/b.bntx').write_text('base extra')
        plan=m.batch_preview(self.repo,[base])
        plan=batch_import.configure(SimpleNamespace(**vars(m)),self.repo,plan['job_id'],plan['token'],{'0':'underlay'})
        result=m.batch_install(self.repo,plan['job_id'],plan['token'])
        self.assertEqual(1,result['installed'],result)
        state=m.load(self.repo);lower=next(k for k in state['mods'] if k!=higher)
        profile=m.root(self.repo)/'profile/ultimate/mods'
        self.assertEqual('skin',(profile/higher/'ui/replace/a.bntx').read_text())
        self.assertEqual('base extra',(profile/lower/'ui/replace/b.bntx').read_text())
        self.assertEqual([lower],state['mods'][higher]['overlays'])
        self.assertFalse(next(r for r in m.listing(self.repo)['mods'] if r['id']==higher)['known_conflicts'])
        m.profile_valid(self.repo,force=True)
        m.undo(self.repo)
        self.assertEqual(1,len(m.load(self.repo)['mods']))

    def test_overlay_retains_base_files_disable_restores_and_undo_is_valid(self):
        base=self.mod('Base moveset visual assets',content='base')
        (base/'ui/replace/unique.bntx').write_text('base unique')
        first=m.install(self.repo,base)['state']['mods'][0]['id']
        skin=self.mod('Visual patch',content='patched')
        plan=m.batch_preview(self.repo,[skin])
        plan=batch_import.configure(SimpleNamespace(**vars(m)),self.repo,plan['job_id'],plan['token'],{'0':'overlay'})
        result=m.batch_install(self.repo,plan['job_id'],plan['token'])
        self.assertEqual(1,result['installed'],result)
        status=m.load(self.repo);second=next(k for k in status['mods'] if k!=first)
        profile=m.root(self.repo)/'profile/ultimate/mods'
        self.assertEqual('patched',(profile/second/'ui/replace/a.bntx').read_text())
        self.assertEqual('base unique',(profile/first/'ui/replace/unique.bntx').read_text())
        self.assertFalse((profile/first/'ui/replace/a.bntx').exists())
        self.assertTrue(status['mods'][first]['enabled'])
        m.change(self.repo,second,'enable',False)
        self.assertEqual('base',(profile/first/'ui/replace/a.bntx').read_text())
        m.undo(self.repo);m.profile_valid(self.repo,force=True)
        self.assertEqual('patched',(profile/second/'ui/replace/a.bntx').read_text())

    def test_orphan_marker_is_visible_and_blocks_gameplay_before_build(self):
        source=self.mod('Future moveset skin','fighter/example/model/body/c120/future.marker','')
        with patch('plugin_runtime.ensure',return_value=None):
            result=m.install(self.repo,source)
        row=m.listing(self.repo)['mods'][0]
        self.assertEqual('NeedsDependencies',row['compatibility'])
        self.assertIn('future.marker',row['dependency_issue'])
        with self.assertRaisesRegex(ValueError,'Basismod fehlt'):
            m.prepare_gameplay(self.repo)

if __name__=='__main__':unittest.main()
