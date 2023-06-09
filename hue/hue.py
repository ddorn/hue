#!/usr/bin/env python3

import os
import json
import requests
import re
import click
import colorsys

IP = os.environ.get("HUE_IP", '192.168.1.101')
KEY = os.environ.get('HUE_KEY', '')
ALL = (1, 2, 3)


def rgb2hsl(r, g, b):
    h, s, l = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return int(65535 * h), int(255 * s), int(255 * l)


def hsl2rgb(h, s, l):
    r, g, b = colorsys.hsv_to_rgb(h / 65535, s / 255, l / 255)
    return int(255 * r), int(255 * g), int(255 * b)


def rgb2hex(r, g, b):
    return '#' + ''.join(map(lambda x: '0' * (x < 16) + hex(x)[2:], (r, g, b)))


def clamp(x, min=0, max=255):
    if x < min:
        return min
    if x > max:
        return max
    return x


def ressource_to_url(*ressource):
    assert KEY, 'Something is wrong, there\'s no KEY. Check your env.'
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

    @property
    def rgb(self):
        return hsl2rgb(*self.hsl)

    @property
    def hex(self):
        return rgb2hex(*self.rgb)


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

    add_scene('off', *({on: False},) * len(ALL))
    add_scene('on', *({on: True},) * len(ALL))
    add_scene('algebre', *(hsl(4000, 255, 255),) * len(ALL))
    add_scene('analyse', *(hsl(0, 255, 255),) * len(ALL))
    add_scene('geo', *(hsl(47135, 255, 135),) * len(ALL))
    add_scene('physique', *(hsl(51130, 250, 105),) * len(ALL))
    add_scene('info', *(hsl(58585, 255, 85),) * len(ALL))
    add_scene('bright', *(hsl(5000, 25, 255),) * len(ALL))
    add_scene('dim', *(hsl(4000, 255, 0),) * len(ALL))
    scenes['toggle'] = toggle

    return scenes


class Time(click.ParamType):
    name = 'time'

    def convert(self, value, param, ctx):
        if isinstance(value, str):
            found = re.match(r'^((\d{1,2})h)?(([0-5]?\d)m)?(([0-5]\d)s)?$', value)

            if found and value:
                h = found.group(2)
                m = found.group(4)
                s = found.group(6)
                h = 0 if h is None else int(h) % 24
                m = 0 if m is None else int(m)
                s = 0 if s is None else int(s)

                return h, m, s
        elif isinstance(value, tuple) and len(value) == 3:
            return value

        self.fail(f'{value} is not a time', param, ctx)


def set_key(ctx, value, param):
    global KEY
    if not param:
        ctx.fail("You need to pass the hue key")
    KEY = param

@click.group(invoke_without_command=True, context_settings=dict(help_option_names=['-h', '--help']))
@click.option('--key', envvar='HUE_KEY', callback=set_key, expose_value=0)
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
@click.argument('time', type=Time(), default=(0, 5, 0))
def timer(time):
    """Set a visual timer."""
    hours, minutes, seconds = time
    time_str = 'PT{:02}:{:02}:{:02}'.format(hours, minutes, seconds)

    address = 'groups', 0, 'action'
    command = dict(on=True, effect='colorloop', bri=255, sat=255)

    schedule(f'timer {time}', time_str, *address, **command)

    print('Timer will go off in', f'{hours}h{minutes}m{seconds}s')


@cmd.command()
@click.argument('time', type=Time(), default=(0, 15, 0))
def ssnooze(time):
    """Snooze the motion detector."""

    hours, minutes, seconds = time
    time_str = 'PT{:02}:{:02}:{:02}'.format(hours, minutes, seconds)

    address = 'sensors', 19, 'config'
    command = dict(on=True)

    # Desactivate it
    put(*address, on=False)

    # Scedule when it will turn on again
    schedule(f'sensor-snooze {time}', time_str, *address, **command)

    print('Motion detector is snoozed for ', f'{hours}h{minutes}m{seconds}s')


class HexColorType(click.ParamType):
    name = 'hex color'

    def convert(self, value, param, ctx):
        if isinstance(value, str):
            found = re.match(r'^#?[0-9A-Fa-f]{6}$', value)
            if value[0] != '#':
                value = '#' + value

            return value

        self.fail(f'{value} is not a color in hexadecimal form (#RRGGBB)', param, ctx)

@cmd.command(name='put')
@click.argument('lights', nargs=-1)
@click.option('--on/--off', '-1/-0', is_flag=True, default=None, help='Switch the light on or off')
@click.option('--hue', '-h', type=click.IntRange(0, 65535), help='Set the light\'s hue')
@click.option('--sat', '-s', type=click.IntRange(0, 255), help='Set the saturation')
@click.option('--brightness', '-b', type=click.IntRange(0, 255), help='Set the brightness')
@click.option('--rgb', '-c', type=click.IntRange(0, 255), nargs=3, help='Set color to thw given RGB')
@click.option('--hex', '-x', type=HexColorType(), help='Set the color to html color')
@click.option('--toggle', '-t', is_flag=True, help='Toggle the light on/off')
def put_cmd(lights, on, hue, sat, brightness, rgb, hex, toggle):
    """
    Set a light (or more) with the given params.

    The hue, saturation, value has a higher priority than rgb and hex.
    Toggle will override the on or off flag.
    """

    if 'all' in lights:
        lights = ALL
    if '0' in lights:
        lights = ALL

    for light in lights:
        l = Light(light)

        if toggle:
            l.update()
            on = not l.on

        d = {}
        if on is not None:
            d['on'] = on
        if hue is not None or sat is not None or brightness is not None:
            if hue is not None:
                d['hue'] = hue
            if sat is not None:
                d['sat'] = sat
            if brightness is not None:
                d['bri'] = brightness
        elif rgb:
            h, s, b = rgb2hsl(*rgb)
            d['hue'] = h
            d['sat'] = s
            d['bri'] = b
        elif hex is not None:
            h, s, b = rgb2hsl(int(hex[1:3], 16), int(hex[3:5], 16), int(hex[5:], 16))
            d['hue'] = h
            d['sat'] = s
            d['bri'] = b

        put(l.state_addr, **d)


@cmd.command(name='get')
@click.argument('lights', default=0)
@click.argument('what', default='all')
@click.option('-p', '--porcelain', is_flag=True, help='Show the output in a parsable way')
def get_cmd(lights, what, porcelain):
    """
    Get the current state of the lights.
    """

    if lights == 0:
        lights = ALL
    else:
        lights = [lights]

    for light in lights:
        l = Light(light, True)
        if what == 'on':
            print(l.on)
        elif what == 'bri':
            print(l.bri)
        elif what == 'sat':
            print(l.sat)
        elif what == 'hue':
            print(l.hue)
        elif what == 'rgb':
            print(l.rgb)
        elif what == 'hex':
            print(l.hex)
        else:
            print('-', l.id)
            print('on:', l.on)
            print('bri:', l.bri)
            print('sat:', l.sat)
            print('hue:', l.hue)
            print('rgb:', ';'.join(map(str, l.rgb)))
            print('hex:', l.hex)


    # TODO : Add a sexy output if not porcelain




if __name__ == '__main__':
        cmd()
