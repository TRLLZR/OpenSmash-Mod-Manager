"""Conservative callable aliases from the user's own two ELF builds.

Only unique, same-size functions with instruction-equivalent bodies and checked
PC-relative references qualify. No game bytes or offset table are distributed.
This does not port arbitrary hooks, data offsets or a changed function ABI.
"""
import collections
import hashlib
import json
import re
from pathlib import Path
import struct

BASE = 0x7100000000

def inputs(repo):
    import drybowser as base
    build=base.build_dir(Path(repo))
    files=[build/'binaries'/v/'main.elf' for v in ('13.0.4','13.0.5')]
    if not all(p.is_file() and not p.is_symlink() and not p.is_junction() for p in files):return {}
    if json.loads((build/'state.json').read_text()).get('game_version')!='13.0.5':return {}
    return {v:base.digest(p) for v,p in zip(('13.0.4','13.0.5'),files)}

def signed(value,bits):return value-(1<<bits) if value&(1<<(bits-1)) else value

def pc_reference(word,pc):
    if word&0x7c000000==0x14000000:
        return ('code',pc+(signed(word&0x3ffffff,26)<<2),word&~0x3ffffff)
    if word&0xff000010==0x54000000 or word&0x7e000000==0x34000000:
        return ('code',pc+(signed((word>>5)&0x7ffff,19)<<2),word&~0xffffe0)
    if word&0x7e000000==0x36000000:
        return ('code',pc+(signed((word>>5)&0x3fff,14)<<2),word&~0x7ffe0)
    if word&0x1f000000==0x10000000:
        imm=signed(((word>>5)&0x7ffff)<<2|((word>>29)&3),21)
        page=bool(word&0x80000000)
        return ('page' if page else 'address',(pc&~0xfff)+(imm<<12) if page else pc+imm,word&~0x60ffffe0)
    if word&0x3b000000==0x18000000:
        return ('address',pc+(signed((word>>5)&0x7ffff,19)<<2),word&~0xffffe0)
    return None

class Elf:
    def __init__(self,path):
        self.trusted = {}
        self.data=Path(path).read_bytes()
        if self.data[:6]!=b'\x7fELF\x02\x01':raise ValueError('Unsupported ELF encoding')
        off=struct.unpack_from('<Q',self.data,32)[0];count=struct.unpack_from('<H',self.data,56)[0]
        self.segments=[]
        for i in range(count):
            kind,flags,file,va,_,size,mem,_=struct.unpack_from('<IIQQQQQQ',self.data,off+56*i)
            if kind==1:self.segments.append((va,file,size,mem,flags))
        if len(self.segments)!=3:raise ValueError('Unexpected ELF segments')
        mod=self.u32(4)
        if self.read(mod,4)!=b'MOD0':raise ValueError('No MOD0')
        dynamic=mod+struct.unpack('<i',self.read(mod+4,4))[0]
        tags={}
        for i in range(4096):
            tag,value=struct.unpack('<qQ',self.read(dynamic+16*i,16))
            if not tag:break
            tags.setdefault(tag,value)
        else:raise ValueError('Unterminated ELF dynamic table')
        self.import_slots={}
        for i in range(tags.get(2,0)//24):
            slot,info,_=struct.unpack('<QQq',self.read(tags[23]+24*i,24))
            sym=self.read(tags[6]+24*(info>>32),24)
            name,_,_,section,value,_=struct.unpack('<IBBHQQ',sym)
            self.import_slots[slot]=(self.cstring(tags[5]+name),section,value)
        eh=mod+struct.unpack('<i',self.read(mod+16,4))[0]
        if self.read(eh+1,3)!=b'\x1b\x03\x3b':raise ValueError('Unknown unwind encoding')
        self.functions={}
        count=self.u32(eh+8)
        if count>300000:raise ValueError('Unwind table too large')
        for i in range(count):
            start,fde=struct.unpack('<ii',self.read(eh+12+8*i,8));start+=eh;fde+=eh
            size=self.u32(fde+12)
            if start%4 or size%4 or not 0<size<1024**2:continue
            if start+size<=self.segments[0][2]:self.functions[start]=size
    def read(self,va,size):
        for start,file,length,_,_ in self.segments:
            if start<=va and va+size<=start+length:return self.data[file+va-start:file+va-start+size]
        raise ValueError('ELF reference outside file segments')
    def u32(self,va):return struct.unpack('<I',self.read(va,4))[0]
    def cstring(self,va):
        for start,file,size,_,_ in self.segments:
            if start<=va<start+size:
                begin=file+va-start;end=self.data.find(b'\0',begin,min(begin+16384,file+size))
                if end>=0:return self.data[begin:end]
        raise ValueError('Invalid ELF string')
    def plt(self,addr):
        try:a,b,c,d=struct.unpack('<IIII',self.read(addr,16))
        except ValueError:return None
        if a&0x9f00001f!=0x90000010 or b&0xffc003ff!=0xf9400211 or d!=0xd61f0220:return None
        ref=pc_reference(a,addr)
        return self.import_slots.get(ref[1]+((b>>10)&0xfff)*8)
    def words(self,start):
        size=self.functions[start]
        return struct.unpack('<'+'I'*(size//4),self.read(start,size))
    def normalized(self,start):
        words=[]
        for i,w in enumerate(self.words(start)):
            ref=pc_reference(w,start+4*i)
            words.append(ref[2] if ref else w)
        return struct.pack('<'+'I'*len(words),*words)

def equivalent(old,new,a,b,memo=None,depth=0):
    memo={} if memo is None else memo
    if (a,b) in memo:return memo[a,b]
    op,np=old.plt(a),new.plt(b)
    if op or np:
        if not op or not np or op[:2]!=np[:2]:return False
        if op[1]==0:return True  # same external SDK import, not a guessed code target
        return equivalent(old,new,op[2],np[2],memo,depth+1)
    if depth>48 or old.functions.get(a)!=new.functions.get(b) or a not in old.functions:return False
    # Existing OpenSmash GA ports are independently maintained ABI boundaries
    # (for example the game's allocator). Still require the local function's
    # complete normalized instruction stream to match before trusting the edge.
    if old.trusted.get(a)==b and old.normalized(a)==new.normalized(b):return True
    ow,nw=old.words(a),new.words(b)
    if len(ow)!=len(nw):return False
    # Optimistic only for a recursive edge; every nonrecursive instruction is
    # still checked before its caller can qualify.
    memo[a,b]=True
    for i,(x,y) in enumerate(zip(ow,nw)):
        r,s=pc_reference(x,a+4*i),pc_reference(y,b+4*i)
        ok=x==y if r is None and s is None else bool(r and s and r[0]==s[0] and r[2]==s[2])
        if ok and r:
            kind,ot,_=r;nt=s[1]
            if a<=ot<a+old.functions[a]:ok=nt-b==ot-a
            elif kind=='code':ok=equivalent(old,new,ot,nt,memo,depth+1)
            else:
                matches=[]
                for os,ns in zip(old.segments[1:],new.segments[1:]):
                    if os[0]<=ot<os[0]+os[3] and os[2:]==ns[2:]:
                        matches.append(nt==ot+ns[0]-os[0])
                ok=bool(matches) and all(matches)
        if not ok:
            memo[a,b]=False;return False
    return True

def aliases(old,new):
    groups=[]
    for image in (old,new):
        group=collections.defaultdict(list)
        for start in image.functions:
            if image.functions[start]<32:continue
            group[hashlib.sha256(image.normalized(start)).digest()].append(start)
        groups.append(group)
    result={}
    for key,starts in groups[0].items():
        candidates=groups[1].get(key,[])
        if len(starts)!=1 or len(candidates)!=1:continue
        a,b=starts[0],candidates[0]
        if a==b or a in new.functions:continue
        if equivalent(old,new,a,b):result[BASE+a]=BASE+b
    return result

def generate(repo,work):
    import drybowser as base
    selected=inputs(repo);mapping={}
    if selected:
        folder=base.build_dir(Path(repo))/'binaries'
        old,new=Elf(folder/'13.0.4/main.elf'),Elf(folder/'13.0.5/main.elf')
        runtime=(Path(repo)/'runtime/hostrt.c').read_text(encoding='utf-8-sig')
        match=re.search(r'g_code_13_0_5\[\]\[2\]\s*=\s*\{(.*?)\};',runtime,re.S)
        if match:
            old.trusted={int(a,16):int(b,16) for a,b in re.findall(r'\{0x([0-9a-fA-F]+),\s*0x([0-9a-fA-F]+)\}',match[1])}
        mapping=aliases(old,new)
        if selected!=inputs(repo):raise ValueError('ELF inputs changed during compatibility scan')
    entries=',\n'.join('{0x%xULL,0x%xULL}'%(a,b) for a,b in sorted(mapping.items()))
    text='''/* Generated locally from verified instruction-equivalent functions. */
static const uint64_t arc_legacy_pairs[][2] = { ENTRIES {0,0} };
static uint64_t arc_legacy_target(Ctx *c, uint64_t address) {
    /* An unresolved main call originating in a registered plugin range only.
     * Ordinary game calls and every already-known 13.0.5 entry are untouched. */
    if (c->x[30] < 0x7280000000ULL || c->x[30] >= 0x7300000000ULL) return address;
    size_t lo=0,hi=COUNT;
    while(lo<hi){size_t mid=lo+(hi-lo)/2;uint64_t old=arc_legacy_pairs[mid][0];
        if(address<old)hi=mid;else if(address>old)lo=mid+1;else {
            static volatile LONG reports;
            if(InterlockedIncrement(&reports)<=16) printf("[compat] verified 13.0.4 plugin call %llx -> 13.0.5 %llx\\n",
                (unsigned long long)address,(unsigned long long)arc_legacy_pairs[mid][1]);
            return arc_legacy_pairs[mid][1];}}
    return address;
}
'''.replace('ENTRIES',entries+',\n' if entries else '').replace('COUNT',str(len(mapping)))
    (Path(work)/'legacy_main_aliases.h').write_text(text,encoding='utf-8',newline='\n')
    print('Legacy callable compatibility: %d verified aliases'%len(mapping),flush=True)
    return selected
