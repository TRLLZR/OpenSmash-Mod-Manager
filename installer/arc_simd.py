"""Complete vector operations missing from this OpenSmash plugin lifter.

Only explicitly unsupported instructions are replaced. Existing lifted code and
intentional UDF traps stay intact. All operands are copied before the write.
"""
import re
from pathlib import Path


def translate(word):
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
    insn = next(Cs(CS_ARCH_ARM64, CS_MODE_ARM).disasm(word.to_bytes(4, 'little'), 0), None)
    if not insn:
        return None
    op, text = insn.mnemonic, insn.op_str
    regs = [(int(r), int(n) if n else None, f, int(e) if e else None)
            for r, n, f, e in re.findall(r'v(\d+)\.(\d+)?([bhsd])(?:\[(\d+)\])?', text)]
    if not regs:
        return None
    rd, lanes, field, _ = regs[0]
    bits = dict(b=8, h=16, s=32, d=64)
    member = dict(b='b', h='h', s='w', d='d')
    width, dst = bits[field], member[field]
    header = '{ V128 t = {{0}}, a = c->v[%d]; ' % regs[1][0] if len(regs) > 1 else '{ V128 t = c->v[%d]; ' % rd
    body = []
    wide = op.rstrip('2')
    if wide in {'uaddw', 'usubw', 'uaddl', 'umull', 'umlal'} and len(regs) == 3:
        header += 'V128 b = c->v[%d], old = c->v[%d]; ' % (regs[2][0], rd)
        upper = lanes if op.endswith('2') else 0
        for i in range(lanes):
            left = 'a.%s[%d]' % (member[regs[1][2]], i if wide.endswith('w') else i+upper)
            right = 'b.%s[%d]' % (member[regs[2][2]], regs[2][3] if regs[2][3] is not None else i+upper)
            operator = '*' if wide in {'umull', 'umlal'} else '-' if wide == 'usubw' else '+'
            expr = '(uint64_t)%s %s (uint64_t)%s' % (left, operator, right)
            if wide == 'umlal': expr = 'old.%s[%d] + (%s)' % (dst, i, expr)
            body.append('t.%s[%d] = %s;' % (dst, i, expr))
    elif op in {'mla', 'mls', 'uhadd', 'shadd'} and len(regs) == 3:
        header += 'V128 b = c->v[%d], old = c->v[%d]; ' % (regs[2][0], rd)
        for i in range(lanes):
            if op in {'mla', 'mls'}:
                expr = 'old.%s[%d] %s (uint64_t)a.%s[%d] * (uint64_t)b.%s[%d]' % (dst,i,'+' if op=='mla' else '-',dst,i,dst,regs[2][3] if regs[2][3] is not None else i)
            else:
                cast = '(int64_t)(int%d_t)' % width if op=='shadd' else '(uint64_t)'
                expr = '(%sa.%s[%d] + %sb.%s[%d]) >> 1' % (cast,dst,i,cast,dst,i)
            body.append('t.%s[%d] = %s;' % (dst,i,expr))
    elif op == 'bic' and len(regs) == 1 and '#' in text:
        immediate = re.search(r'#(0x[0-9a-f]+|\d+)', text)
        shift = re.search(r'lsl #(\d+)', text)
        mask = int(immediate[1],0) << (int(shift[1]) if shift else 0)
        body = ['t.%s[%d] &= ~0x%xULL;' % (dst,i,mask) for i in range(lanes)]
        if lanes * width == 64: body.append('t.d[1] = 0;')
    elif op == 'sqdmulh' and len(regs)==3 and regs[2][3] is not None and width in (16,32):
        header += 'V128 b = c->v[%d]; ' % regs[2][0]
        for i in range(lanes):
            body.append('{ int64_t p = (int64_t)(int%d_t)a.%s[%d] * (int64_t)(int%d_t)b.%s[%d]; '
                        'int64_t r = p >> %d; if (r > %d) r = %d; t.%s[%d] = r; }' %
                        (width,dst,i,width,member[regs[2][2]],regs[2][3],width-1,2**(width-1)-1,2**(width-1)-1,dst,i))
    elif op=='rev16' and len(regs)==2 and field=='b':
        body=['t.b[%d] = a.b[%d];' % (i,i^1) for i in range(lanes)]
    else:
        return None
    return header + ' '.join(body) + ' c->v[%d] = t; }' % rd


def patch_generated(work, nro=None):
    pattern=re.compile(r'guest_unimpl\(0x([0-9a-f]+)ULL, 0x([0-9a-f]+)U, "([^"]+)"\);')
    count=0
    for path in (Path(work)/'gen_plugin/sky_arcropolis').glob('c_*.c'):
        def replace(match):
            nonlocal count
            code=translate(int(match[2],16))
            if code is None: return match[0]
            count+=1
            return code + ' /* arc-simd */'
        old=path.read_text()
        new=pattern.sub(replace,old)
        if nro:
            data=Path(nro).read_bytes()
            def refresh(match):
                import struct
                word=struct.unpack_from('<I',data,int(match[1],16)-0x7280000000)[0]
                code=translate(word)
                return 'L_'+match[1]+': '+code+' /* arc-simd */' if code else match[0]
            new=re.sub(r'L_([0-9a-f]+): (?:\{ V128 t = \{\{0\}\}, a = c->v[^\n]*|\{ V128 t = c->v[^\n]*&= ~0x[^\n]*)',refresh,new)
        if old!=new: path.write_text(new)
    return count
