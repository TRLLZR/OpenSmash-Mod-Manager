"""Execute the real read-only overlay helper against real temporary files."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

CLANG = os.environ.get('OPENSMASH_TEST_CLANG') or shutil.which('clang')

@unittest.skipUnless(sys.platform == 'win32' and CLANG, 'Windows Clang required')
class PluginRomfsTests(unittest.TestCase):
    def test_real_file_visibility_and_namespace_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            plugins=root/'atmosphere/contents/01006A800016E000/romfs/skyline/plugins'
            plugins.mkdir(parents=True)
            (plugins/'own.nro').write_bytes(b'owned synthetic bytes')
            header=Path(__file__).with_name('arc_fs_support.h').as_posix()
            source=r'''
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
enum {MK_ROM=1,MK_SAVE=2};
#define RESULT_PATH_NOT_FOUND 0x202
typedef struct {int kind;} Mount;
typedef struct {uint64_t x[32];} Ctx;
static void fs_lock(void) {} static void fs_unlock(void) {}
static int view_path(Mount*m,const char*r,char*out) {return 0;}
static uint32_t split_path(const char*p,Mount**m,char*r) {return 1;}
static void wr64(uint64_t p,uint64_t v) {memcpy((void*)(uintptr_t)p,&v,8);}
static void wr8(uint64_t p,uint8_t v) {memcpy((void*)(uintptr_t)p,&v,1);}
#include HEADER
#define CHECK(x) do { if (!(x)) {fprintf(stderr,"failed line %d\n",__LINE__);return 1;} } while(0)
int main(int argc,char**argv) {
    Mount rom={MK_ROM},save={MK_SAVE}; char out[MAX_PATH],bytes[32]={0};
    _putenv_s("SSBU_SD",argv[1]);_putenv_s("SSBU_SKYLINE","1");
    CHECK(arc_plugin_view(&rom,"skyline\\plugins\\own.nro",out)==1);
    FILE*f=fopen(out,"rb");CHECK(f);CHECK(fread(bytes,1,21,f)==21);fclose(f);
    CHECK(!memcmp(bytes,"owned synthetic bytes",21));
    CHECK(arc_plugin_view(&rom,"skyline\\plugins",out)==1);
    CHECK(GetFileAttributesA(out)&FILE_ATTRIBUTE_DIRECTORY);
    CHECK(arc_plugin_view(&rom,"skyline\\plugins\\missing.nro",out)==0);
    CHECK(arc_plugin_view(&save,"skyline\\plugins\\own.nro",out)==-1);
    CHECK(arc_plugin_view(&rom,"skyline\\plugins_extra\\own.nro",out)==-1);
    CHECK(arc_plugin_view(&rom,"data.arc",out)==-1);
    CHECK(arc_plugin_view(&rom,"skyline\\plugins\\..\\secret",out)==0);
    CHECK(arc_plugin_view(&rom,"skyline\\plugins\\.. \\secret",out)==0);
    CHECK(arc_plugin_view(&rom,"skyline\\plugins\\own.nro:stream",out)==0);
    _putenv_s("SSBU_SKYLINE","0");
    CHECK(arc_plugin_view(&rom,"skyline\\plugins\\own.nro",out)==-1);
    _putenv_s("SSBU_SKYLINE","1");_putenv_s("SSBU_SD","");
    CHECK(arc_plugin_view(&rom,"skyline\\plugins\\own.nro",out)==-1);
    return 0;
}
'''.replace('HEADER',json.dumps(header))
            file=root/'probe.c';file.write_text(source)
            exe=root/'probe.exe'
            build=subprocess.run([CLANG,'-O2',str(file),'-o',str(exe)],capture_output=True,text=True,timeout=60)
            self.assertEqual(0,build.returncode,build.stderr)
            run=subprocess.run([str(exe),str(root)],capture_output=True,text=True,timeout=15)
            self.assertEqual(0,run.returncode,run.stderr)

if __name__=='__main__':unittest.main()
