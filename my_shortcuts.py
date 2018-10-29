#!/usr/bin/python3

import os
import hue

scenes = hue.build_scenes()
SHORTCUTS = {
    'esc': hue.toggle,
    'b': scenes['bright'],
    'i': scenes['info'],
    'o': scenes['algebre'],
    'a': scenes['analyse'],
    'd': scenes['dim']
}

def hotkey(hotkey):
    def wrapper(f):
        SHORTCUTS[hotkey] = f
        return f
    return wrapper


@hotkey('z')
def zulip():
    os.system('~/.appImage/Zulip-2.3.82-x86_64.AppImage')
