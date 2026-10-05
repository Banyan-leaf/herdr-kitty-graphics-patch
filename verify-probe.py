"""Check what a herdr pane tells an image-drawing program.

Run it inside a herdr pane (any shell) and read the `repr:` line:

    python3 verify-probe.py

It sends the capability query a probing TUI sends - one transparent RGBA
pixel as zlib-compressed direct data (`a=q`), followed by the DA1 sentinel -
and prints the terminal's raw reply.

Expected results
----------------
Outer terminal without Kitty graphics (Windows Terminal, GNOME Terminal,
Alacritty, an unfixed multiplexer, ...):
    repr: b'\x1b[?62;22c'                <- DA1 only, no OK  => correct
    repr: b'\x1b_Gi=31;OK\x1b\\...'      <- OK               => the bug

Outer terminal with Kitty graphics (kitty, Ghostty, WezTerm):
    repr: b'\x1b_Gi=31;OK\x1b\\...'      <- OK               => correct
"""
import binascii
import os
import select
import termios
import time
import tty

QUERY = b'\x1b_Gi=31,s=1,v=1,a=q,t=d,f=32,o=z;eAFjYGBgAAAABAAB\x1b\\\x1b[c'

fd = os.open('/dev/tty', os.O_RDWR)
previous = termios.tcgetattr(fd)
try:
    tty.setraw(fd)
    os.write(fd, QUERY)
    time.sleep(0.5)
    reply = b''
    while select.select([fd], [], [], 0.2)[0]:
        reply += os.read(fd, 65536)
finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, previous)
    os.close(fd)

print('reply:', binascii.hexlify(reply).decode())
print('repr: ', repr(reply))
print('kitty graphics claimed:', b'a=q' in QUERY and b';OK' in reply)
