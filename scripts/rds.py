"""Lecteur minimal de fichiers .rds (sérialisation R, format XDR v2/v3) pour objets sf."""
import gzip, struct, sys

class Sym(str): pass

class R:
    def __init__(self, data):
        self.d = data; self.i = 0; self.refs = []
    def int(self):
        v = struct.unpack('>i', self.d[self.i:self.i+4])[0]; self.i += 4; return v
    def length(self):
        n = self.int()
        if n == -1:
            a = self.int(); b = self.int(); n = (a << 32) + b
        return n
    def read(self):
        flags = self.int() & 0xFFFFFFFF
        t = flags & 0xFF
        has_attr = bool(flags & 512); has_tag = bool(flags & 1024)
        if t == 254 or t == 0: return None          # NILVALUE / NILSXP
        if t in (253, 242, 241, 251, 252): return None  # envs, missing, unbound
        if t == 247: return None
        if t == 255:
            idx = flags >> 8
            if idx == 0: idx = self.int()
            return self.refs[idx - 1]
        if t == 1:  # SYMSXP
            s = Sym(self.read()); self.refs.append(s); return s
        if t in (249, 250):  # namespace/package
            self.read_strvec(); v = ('ns',); self.refs.append(v); return v
        if t == 4:  # ENVSXP
            env = {}; self.refs.append(env)
            self.int(); self.read(); self.read(); self.read(); self.read()
            return env
        if t == 9:  # CHARSXP
            n = self.int()
            if n == -1: return None
            s = self.d[self.i:self.i+n].decode('utf-8', 'replace'); self.i += n; return s
        if t in (2, 6, 3, 5, 17):  # pairlists, lang, closure, promise, dotdot
            items = []; attrs = None
            while True:
                if has_attr: a = self.read(); attrs = attrs or a
                tag = self.read() if has_tag else None
                car = self.read()
                items.append((tag, car))
                # cdr
                flags = self.int() & 0xFFFFFFFF
                t2 = flags & 0xFF
                if t2 in (254, 0): break
                if t2 != t:
                    self.i -= 4; rest = self.read(); items.append((None, rest)); break
                has_attr = bool(flags & 512); has_tag = bool(flags & 1024)
            return {'__pairlist__': items, '__attr__': attrs}
        if t in (10, 13):  # LGL / INT
            n = self.length(); v = list(struct.unpack('>%di' % n, self.d[self.i:self.i+4*n])); self.i += 4*n
            return self.wrap(v, has_attr)
        if t == 14:  # REAL
            n = self.length(); v = list(struct.unpack('>%dd' % n, self.d[self.i:self.i+8*n])); self.i += 8*n
            return self.wrap(v, has_attr)
        if t == 15:
            n = self.length(); self.i += 16*n; return self.wrap([], has_attr)
        if t == 24:
            n = self.length(); v = self.d[self.i:self.i+n]; self.i += n; return self.wrap(v, has_attr)
        if t == 16:  # STRSXP
            n = self.length(); v = [self.read() for _ in range(n)]; return self.wrap(v, has_attr)
        if t in (19, 20):  # VECSXP
            n = self.length(); v = [self.read() for _ in range(n)]; return self.wrap(v, has_attr)
        if t == 25:  # S4
            return self.wrap(None, has_attr)
        if t == 238:  # ALTREP
            info = self.read(); state = self.read(); attr = self.read()
            cls = info['__pairlist__'][0][1] if isinstance(info, dict) else None
            v = self.altrep(str(cls), state)
            return {'v': v, 'a': self.attrs(attr)} if attr else v
        raise ValueError('type non géré %d à %d' % (t, self.i))
    def altrep(self, cls, st):
        if cls in ('compact_intseq', 'compact_realseq'):
            vals = st['v'] if isinstance(st, dict) else st
            n, a, b = int(vals[0]), vals[1], vals[2]
            return [a + b*k for k in range(n)]
        if cls.startswith('wrap_'):
            x = st[0] if isinstance(st, list) else st
            return x
        if cls == 'deferred_string':
            arg = st['__pairlist__'][0][1] if isinstance(st, dict) and '__pairlist__' in st else st
            vals = arg['v'] if isinstance(arg, dict) else arg
            return [str(int(x)) if isinstance(x, float) and x == int(x) else str(x) for x in vals]
        return st
    def read_strvec(self):
        self.int(); n = self.int(); return [self.read() for _ in range(n)]
    def attrs(self, a):
        if not a or '__pairlist__' not in a: return {}
        return {str(k): v for k, v in a['__pairlist__']}
    def wrap(self, v, has_attr):
        if has_attr:
            return {'v': v, 'a': self.attrs(self.read())}
        return v

def load(path):
    d = gzip.open(path).read()
    assert d[:2] == b'X\n'
    r = R(d); r.i = 2
    ver = r.int(); r.int(); r.int()
    if ver == 3:
        n = r.int(); r.i += n
    return r.read()

def val(x):
    return x['v'] if isinstance(x, dict) and 'v' in x else x

def dataframe(obj):
    names = obj['a']['names']; names = val(names)
    cols = {n: c for n, c in zip(names, obj['v'])}
    return cols

if __name__ == '__main__':
    o = load(sys.argv[1])
    cols = dataframe(o)
    for k, c in cols.items():
        v = val(c)
        print(k, type(v).__name__, (v[:3] if isinstance(v, list) else v), (c['a'].keys() if isinstance(c, dict) and 'a' in c else ''))
