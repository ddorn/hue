#!/usr/bin/python3

import os
import json
import requests
import click
import colorsys

IP = '192.168.1.110'
KEY = ''

with open(os.path.expanduser('~/prog/hue/KEY')) as f:
    KEY = f.read()


def rgb2hsl(r, g, b):
    h, s, l = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return int(65535 * h), int(255 * s), int(255 * l)


def clamp(x, min=0, max=255):
    if x < min:
        return min
    if x > max:
        return max
    return x


def ressource_to_url(*ressource):
    return '/'.join(('http:/', IP, 'api', KEY) + tuple(map(str, ressource)))


def get(*ressource):
    url = ressource_to_url(*ressource)
    r = requests.get(url)

    r.raise_for_status()
    return r.json()


def put(*ressource, **kwargs):
    url = ressource_to_url(*ressource)
    js = json.dumps(kwargs)
    r = requests.put(url, js)

    j = r.json()
    if 'error' in str(j):
        print(j)


def post(*ressource, **kwargs):
    url = ressource_to_url(*ressource)
    js = json.dumps(kwargs)
    r = requests.post(url, js)

    j = r.json()
    if 'error' in str(j):
        print(j)


class Light:
    def __init__(self, id, update=False):
        self.id = id
        self.name = ''
        self._on = False
        self._bri = 0
        self._hue = 0
        self._sat = 0
        if update:
            self.update()

    def update(self):
        light = get('lights', self.id)
        self.name = light['name']
        state = light['state']
        self._on = state['on']
        self._bri = state['bri']
        self._hue = state['hue']
        self._sat = state['sat']

    @property
    def address(self):
        return 'lights/{}'.format(self.id)

    @property
    def state_addr(self):
        return self.address + '/state'

    # On
    @property
    def on(self):
        return self._on

    @on.setter
    def on(self, on):
        on = bool(on)
        self._on = on
        put(self.state_addr, 'state', on=on)

    @property
    def hsl(self):
        return self.hue, self.sat, self.bri

    @hsl.setter
    def hsl(self, hsl):
        put(self.state_addr, hue=hsl[0], sat=hsl[1], bri=hsl[2])

    # Brightness
    @property
    def bri(self):
        return self._bri

    @bri.setter
    def bri(self, bri):
        bri = clamp(bri)
        self._bri = bri
        put(self.state_addr, bri=bri)

    # Saturation
    @property
    def sat(self):
        return self._sat

    @sat.setter
    def sat(self, sat):
        sat = clamp(sat)
        self._sat = sat
        put(self.state_addr, 'state', sat=sat)

    # Hue
    @property
    def hue(self):
        return self._hue

    @hue.setter
    def hue(self, hue):
        hue = clamp(hue, 0, 65535)
        self._hue = hue
        put(self.state_addr, 'state', hue=hue)


def schedule(name, time, *address, **action):
    """
    time: as specified on https://developers.meethue.com/documentation/datatypes-and-time-patterns#16_time_patterns
    """

    address = '/'.join(('/api', KEY) + tuple(map(str, address)))
    command = dict(address=address, method='PUT', body=action)

    post('schedules', name=name, command=command, localtime=time, autodelete=True, recycle=True)


def main():
    import curses
    from curses import wrapper
    import ansimarkup

    def loop(screen):
        curses.curs_set(False)
        assert curses.can_change_color()
        n_lights = len(get('lights'))
        cur_light = 0

        lights = [Light(i) for i in range(1, 1 + n_lights)]
        for l in lights: l.update()

        stop = False
        char = ''
        while not stop:

            screen.clear()
            for i, l in enumerate(lights):
                y = curses.LINES // 2
                x = int(curses.COLS // len(lights) * (i + 0.3))

                attr = curses.A_BOLD if cur_light == i else 0
                screen.addstr(y, x, str(l.hsl), attr)

            l = lights[cur_light]
            char = screen.getkey()
            if char == curses.KEY_ENTER or char == '\n':
                stop = True
            elif char == 'KEY_LEFT':
                cur_light -= 1
            elif char == 'KEY_RIGHT':
                cur_light += 1
            elif char in 'qa':  # Brightness
                l.bri += 10 if char == 'q' else -10
            elif char in 'ws':  # Hue
                l.hue += 200 if char == 'w' else -200
            elif char in 'ed':  # Saturation
                l.sat += 10 if char == 'e' else -10
            elif char == ' ':
                l.on = not l.on

            cur_light %= n_lights
            screen.refresh()

    wrapper(loop)


def toggle():
    first_light = Light(1, update=True)

    for i in range(1, 4):
        l = Light(i)
        l.on = not first_light.on


def build_scenes():
    scenes = {}
    def add_scene(name, *states):
        """add_scene(name, {on: 0}, {'bri': 124, ...}, ...)"""

        def apply():
            for i in range(0, len(states)):
                l = Light(i + 1)
                state = {on: True}; state.update(states[i])
                put(l.state_addr, **state)

        scenes[name] = apply


    bri = 'bri'
    hue = 'hue'
    sat = 'sat'
    on = 'on'
    hsl = lambda h, s, l: {hue: h, sat: s, bri: l}

    add_scene('off', {on: False}, {on: False})
    add_scene('on', {on: True}, {on: True})
    add_scene('algebre', *(hsl(4000, 255, 255),) * 2)
    add_scene('analyse', *(hsl(0, 255, 255),) * 2)
    add_scene('geo', *(hsl(47135, 255, 135),) * 2)
    add_scene('physique', *(hsl(51130, 250, 105),) * 2)
    add_scene('info', *(hsl(58585, 255, 85),) * 2)
    add_scene('bright', *(hsl(5000, 25, 255),) * 2)
    add_scene('dim', *(hsl(4000, 255, 0),) * 2)
    scenes['toggle'] = toggle

    return scenes


@click.group(invoke_without_command=True)
@click.pass_context
def cmd(ctx):
    if ctx.invoked_subcommand is None:
        main()


@cmd.command()
@click.argument('scene')
def set(scene):
    scenes = build_scenes()
    nop = lambda: print('Not a valid scene. Choose from :', *scenes.keys())
    conf = scenes.get(scene, nop)
    conf()

@cmd.command()
@click.argument('time', default=5)
@click.argument('unit', default='m', type=click.Choice('smh'))
def timer(time, unit):
    if unit == 'h':
        time *= 3600
    elif unit == 'm':
        time *= 60

    hours = time // 3600 % 24
    minutes = time // 60 % 60
    seconds = time % 60
    time_str = 'PT{:02}:{:02}:{:02}'.format(hours, minutes, seconds)

    address = 'groups', 0, 'action'
    command = dict(on=True, effect='colorloop', bri=255, sat=255)

    schedule(f'timer {time}', time_str, *address, **command)

    print('Timer will go off in', f'{hours}h{minutes}m{seconds}s')


if __name__ == '__main__':
        cmd()
