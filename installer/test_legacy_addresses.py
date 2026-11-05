"""Synthetic ARM64 functions prove conservative cross-version alias selection."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
import legacy_addresses as legacy
import plugin_runtime

MOV = 0xd28000e0
RET = 0xd65f03c0
NOP = 0xd503201f
BODY = [MOV, NOP, NOP, NOP, NOP, NOP, NOP, RET]

class Image:
    def __init__(self, funcs, shift=0):
        self.bodies=funcs;self.functions={a:len(w)*4 for a,w in funcs.items()};self.trusted={}
        self.segments=[(0,0,0x2000,0x2000,5),(0x4000+shift,0,0x1000,0x1000,4),(0x6000+shift,0,0x1000,0x1000,6)]
    def words(self,a):return self.bodies[a]
    def normalized(self,a):
        words=[legacy.pc_reference(w,a+4*i) for i,w in enumerate(self.bodies[a])]
        return struct.pack('<'+'I'*len(words),*[r[2] if r else w for r,w in zip(words,self.bodies[a])])
    def plt(self,a):return None

def branch(pc,target):return 0x94000000|(((target-pc)>>2)&0x3ffffff)
def adrp(pc,target):
    imm=((target>>12)-(pc>>12))&0x1fffff
    return 0x90000000|((imm&3)<<29)|((imm>>2)<<5)

class LegacyAddressTests(unittest.TestCase):
    def test_unique_unchanged_function_only(self):
        old,new=Image({0x100:BODY}),Image({0x200:BODY})
        self.assertEqual({legacy.BASE+0x100:legacy.BASE+0x200},legacy.aliases(old,new))
        changed=BODY.copy();changed[0]=MOV+32
        self.assertFalse(legacy.aliases(old,Image({0x200:changed})))

    def test_ambiguous_or_existing_current_entry_never_remapped(self):
        self.assertFalse(legacy.aliases(Image({0x100:BODY,0x140:BODY}),Image({0x200:BODY})))
        self.assertFalse(legacy.aliases(Image({0x100:BODY}),Image({0x200:BODY,0x240:BODY})))
        self.assertFalse(legacy.aliases(Image({0x100:BODY}),Image({0x100:BODY})))

    def test_pc_relative_data_reference_uses_verified_segment_movement(self):
        old=Image({0x100:[adrp(0x100,0x4000),*BODY[1:]]})
        new=Image({0x200:[adrp(0x200,0x5000),*BODY[1:]]},shift=0x1000)
        self.assertTrue(legacy.aliases(old,new))
        wrong=Image({0x200:[adrp(0x200,0x6000),*BODY[1:]]},shift=0x1000)
        self.assertFalse(legacy.aliases(old,wrong))

    def test_external_call_must_keep_callee_semantics(self):
        old=Image({0x100:[branch(0x100,0x300),*BODY[1:]],0x300:BODY})
        new=Image({0x200:[branch(0x200,0x700),*BODY[1:]],0x700:BODY})
        self.assertIn(legacy.BASE+0x100,legacy.aliases(old,new))
        changed=BODY.copy();changed[0]=MOV+32
        new=Image({0x200:[branch(0x200,0x700),*BODY[1:]],0x700:changed})
        self.assertNotIn(legacy.BASE+0x100,legacy.aliases(old,new))

    def test_existing_runtime_boundary_still_requires_instruction_match(self):
        old,new=Image({0x100:BODY}),Image({0x200:BODY})
        old.trusted[0x100]=0x200
        self.assertTrue(legacy.equivalent(old,new,0x100,0x200))
        new.bodies[0x200]=[MOV+32,*BODY[1:]]
        self.assertFalse(legacy.equivalent(old,new,0x100,0x200))

    def test_alias_cache_tracks_both_private_images_and_missing_is_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp);(repo/'build').mkdir();(repo/'build/state.json').write_text(json.dumps(dict(game_version='13.0.5')))
            self.assertEqual({},legacy.inputs(repo))
            for v in ('13.0.4','13.0.5'):
                p=repo/'build/binaries'/v/'main.elf';p.parent.mkdir(parents=True);p.write_bytes(('owned fixture '+v).encode())
            first=legacy.inputs(repo)
            (repo/'build/binaries/13.0.4/main.elf').write_bytes(b'changed owned fixture')
            self.assertNotEqual(first,legacy.inputs(repo))
            import runtime_cache
            with self.assertRaisesRegex(ValueError,'Spielabbilder'):
                runtime_cache.plugin(repo,dict(legacy_alias_inputs=first))

    def test_no_nintendo_or_unrecognized_elf_is_required_by_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'own.elf';p.write_bytes(b'owned fixture')
            with self.assertRaises(ValueError):legacy.Elf(p)

if __name__=='__main__':unittest.main()
