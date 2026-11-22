#!/usr/bin/env python3
"""Fix the self-reference LC_LOAD_DYLIB in roothide tweak dylibs.

The Theos roothide build materializes a bogus dependency
    @loader_path/.jbroot/Library/MobileSubstrate/DynamicLibraries/<name>.dylib
(basically the tweak depending on itself). On device dyld fails to resolve
it and the whole tweak is silently skipped, so SpringBoard shows nothing.
This script rewrites each FAT slice's load commands, replacing that entry
with the real substrate load path, then re-signs.
"""
import shutil, subprocess, sys, os, tarfile, io, struct

SELF_PREFIX = "@loader_path/.jbroot/Library/MobileSubstrate/DynamicLibraries/"
SUBSTRATE = "@loader_path/.jbroot/usr/lib/libsubstrate.dylib"

def get_macho(b, off):
    return b[off:]

def rewrite_load_cmds(data):
    """Replace self-ref LC_LOAD_DYLIB with SUBSTRATE. Returns new bytes."""
    magic = struct.unpack_from('>I', data)[0]
    if magic == 0xcafebabe:
        # FAT: process each slice
        n = struct.unpack_from('>I', data, 4)[0]
        out = bytearray(data)
        for i in range(n):
            off = struct.unpack_from('>I', data, 16 + i*20)[0]
            size = struct.unpack_from('>I', data, 20 + i*20)[0]
            slice_bytes = bytes(out[off:off+size])
            fixed = rewrite_one_slice(slice_bytes)
            if fixed != slice_bytes:
                out[off:off+size] = fixed
        return bytes(out)
    return rewrite_one_slice(data)

def rewrite_one_slice(d):
    ncmds = struct.unpack_from('<I', d, 16)[0]
    p = 32
    cmds = []
    for _ in range(ncmds):
        cmd, size = struct.unpack_from('<II', d, p)
        cmds.append((cmd, size, p))
        p += size
    # Build new load command list with replacement
    new = bytearray(d[:32])
    replaced = False
    for cmd, size, pos in cmds:
        if cmd in (0xc, 0xd):
            rel = struct.unpack_from('<I', d, pos+8)[0]
            full = d[pos+rel:pos+size].split(b'\0')[0].decode()
            if full.startswith(SELF_PREFIX) or full.endswith('MowangDaFeiYuPet.dylib') and 'Library/MobileSubstrate' in full:
                # replace string, keep size (pad with zeros)
                new_cmd = bytearray(d[pos:pos+size])
                # only rewrite if string fits
                if len(SUBSTRATE.encode()) < size - rel:
                    new_cmd[rel:rel+len(SUBSTRATE.encode())] = SUBSTRATE.encode()
                    new_cmd[rel+len(SUBSTRATE.encode()):] = b'\0' * (size - rel - len(SUBSTRATE.encode()))
                    replaced = True
                new += new_cmd
            else:
                new += d[pos:pos+size]
        else:
            new += d[pos:pos+size]
    # update ncmds (size unchanged, count same)
    struct.pack_into('<I', new, 16, ncmds)
    return bytes(new)

def main():
    deb_path = sys.argv[1]
    tmp = '/tmp/fixdebs'
    os.makedirs(tmp, exist_ok=True)
    # extract
    subprocess.run(['dpkg-deb', '-x', deb_path, tmp], check=True)
    # locate dylib
    dylibs = []
    for root, _dirs, files in os.walk(tmp):
        for f in files:
            if f == 'MowangDaFeiYuPet.dylib':
                dylibs.append(os.path.join(root, f))
    if not dylibs:
        print('no dylib found', file=sys.stderr)
        sys.exit(2)
    for dylib in dylibs:
        orig = open(dylib, 'rb').read()
        fixed = rewrite_load_cmds(orig)
        if fixed != orig:
            open(dylib, 'wb').write(fixed)
            subprocess.run(['ldid', '-S', dylib], check=True)
            print('fixed', dylib)
        else:
            print('unchanged', dylib)
    # repack with same control
    script = subprocess.run(['dpkg-deb', '-b', tmp, deb_path], capture_output=True, text=True)
    # move temp deb to packages? keep same filename
    shutil.rmtree(tmp)

if __name__ == '__main__':
    main()
