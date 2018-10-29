#!/usr/bin/python3 

import importlib
from time import sleep
import threading
import keyboard
import my_shortcuts

shortcut_runned = threading.Event()
exit = threading.Event()

def main():
    while not exit.is_set():
        keyboard.wait('esc', suppress=True)
        keyboard.hook(hook, suppress=True)
        shortcut_runned.wait(timeout=1)
        keyboard.unhook(hook)
        shortcut_runned.clear()

def reload():
    global my_shortcuts
    my_shortcuts = importlib.reload(my_shortcuts)
    print('Shortcuts reloaded')
    

def hook(event):

    if event.event_type == keyboard.KEY_UP:
        pass
    elif event.name == 'delete':
        print('Shotcuts stopped !')
        exit.set()
    elif event.name == 'f5':
        reload()
    else:
        func = my_shortcuts.SHORTCUTS.get(event.name, lambda: 0)
        try:
            func()
        except BaseException as e:
            print('Fail to execute', event, ':', e, '\nFunction:', func)

        shortcut_runned.set()


if __name__ == '__main__':
    main()
