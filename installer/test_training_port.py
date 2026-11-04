"""Source cache invalidation and exact release identification, no game data."""
import json, tempfile, unittest
from pathlib import Path
import arc_backend, arc_import, plugin_runtime, runtime_cache
import test_modmanager as fixture
from unittest.mock import patch

class PortTests(unittest.TestCase):
    def test_missing_function_reports_symbol(self):
        with self.assertRaisesRegex(ValueError, 'GetLastOpenedUser'):
            plugin_runtime.validate_log('module sky_training_modpack calls _ZN2nn7account17GetLastOpenedUserEPNS0_3UidE, which nothing provides\nGUEST TRAP: unresolved')
    def test_sources_change_without_native_binary_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, work = Path(tmp) / 'repo', Path(tmp) / 'private'
            path = repo / 'runtime/nnfs.c'
            path.parent.mkdir(parents=True)
            path.write_text('old')
            a = arc_backend.source_inputs(repo)
            path.write_text('new')
            self.assertNotEqual(a, arc_backend.source_inputs(repo))
            arc_backend.stage_sources(repo, work)
            self.assertEqual((work / 'nnfs.c').read_text(), 'new')
            nro = repo / 'tools/nro/recomp_nro.py'
            nro.parent.mkdir(parents=True)
            nro.write_text('nro source')
            arc_backend.stage_sources(repo, work)
            self.assertEqual((work / 'ro_study/recomp_nro.py').read_text(), 'nro source')
            # Changing generated data or saves must not alter source identity.
            before = arc_backend.source_inputs(repo)
            (repo / 'save.bin').write_text('save')
            self.assertEqual(before, arc_backend.source_inputs(repo))

    def test_rejects_old_plugin_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'Buildquellen'):
                plugin_runtime.valid(Path(tmp), {'app': plugin_runtime.APP})

    def test_fast_cache_does_not_bypass_source_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            src = repo / 'runtime/nnfs.c'
            src.parent.mkdir(); src.write_text('first')
            exe = repo / 'build/work/modmanager_plugins/0123456789abcdef0123/ssbu_modmanager.exe'
            exe.parent.mkdir(parents=True); exe.write_bytes(b'synthetic unchanged executable')
            record = dict(app=plugin_runtime.APP, key='0123456789abcdef0123',
                exe='modmanager_plugins/0123456789abcdef0123/ssbu_modmanager.exe',
                plugin_bin='plugin_bin', nro_bin='../../nro_bin_eh_o2',
                files={arc_backend.file_key(repo,exe):arc_backend.base.digest(exe)},
                source_inputs=arc_backend.source_inputs(repo),
                plugin_builder=plugin_runtime.base.digest(Path(plugin_runtime.__file__)))
            with patch.object(runtime_cache.catalog, 'digest', side_effect=lambda repo,p:arc_backend.base.digest(p)):
                self.assertEqual(runtime_cache.plugin(repo, record), record)
                src.write_text('second')
                with self.assertRaisesRegex(ValueError, 'Buildquellen'):
                    runtime_cache.plugin(repo, record)
            with self.assertRaisesRegex(ValueError, 'Buildquellen'):
                plugin_runtime.valid(repo, record)

    def test_original_package_name_requires_all_hashes(self):
        hashes = {
            'libnro_hook.nro': 'ca7aec03aee49fea539dcb92569fea5bc5389f77377ba2a30e4d0b7ebd0255e6',
            'libparam_hook.nro': '3ed7a2945084176cbb7742d99878f1e8d3a0992feb0fef74be2cfbc68ac8fb88',
            'libtraining_modpack.nro': '38260daeb8f917c99ea3443b7d533ce2bffd8bae4890fc4baca9b317d9fcf829',
        }
        entries = [dict(path=p, sha256=s) for p, s in hashes.items()]
        self.assertEqual(arc_import.known_package_name(entries), 'Ultimate Training Modpack v7.1.1')
        self.assertIsNone(arc_import.known_package_name(entries[:-1]))
        entries[0]['sha256'] = '0' * 64
        self.assertIsNone(arc_import.known_package_name(entries))

class TrainingDataTests(unittest.TestCase):
    setUp = fixture.ManagerTests.setUp
    mod = fixture.ManagerTests.mod

    def test_settings_and_states_survive_disable_enable(self):
        m = fixture.m
        result = m.install(self.repo, self.mod('Asset', 'ui/replace/a.bntx', 'asset'))
        key = result['state']['mods'][-1]['id']
        folder = m.root(self.repo) / 'profile/ultimate/TrainingModpack'
        folder.mkdir(parents=True)
        expected = {'training_modpack_menu.conf': b'{"settings":"test"}', 'save_states.toml': b'x = 12.5\n'}
        for name, data in expected.items(): (folder / name).write_bytes(data)
        for enabled in (False, True):
            m.change(self.repo, key, 'enable', enabled)
            for name, data in expected.items(): self.assertEqual((folder / name).read_bytes(), data)
            m.profile_valid(self.repo, force=True)

if __name__ == '__main__': unittest.main()
