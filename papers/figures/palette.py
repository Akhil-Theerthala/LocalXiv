"""The colours a Figure render draws with. Light is the export palette; dark follows the reader's theme."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    text: str
    muted: str
    accent: str
    hairline: str
    page: str
    card: str
    sunk: str
    cell_masked: str
    cell_hot: str
    bar: str
    # fill, stroke, text for each tone. The plain card is the page colour; ``muted`` is the sunk surface.
    tones: dict


ACCENT_TONES = ('blue', 'green', 'peach')

LIGHT = Palette(
    name='light', text='#243b32', muted='#627168', accent='#2f6f5e', hairline='#dce1d8',
    page='#ffffff', card='#fbfcfa', sunk='#f3f6f0', cell_masked='#eef1ea', cell_hot='#dce8cf', bar='#c3ccbd',
    tones={'blue': ('#e1ebf1', '#7f9fb5', '#2b5876'), 'green': ('#dce8cf', '#8aa87a', '#2f5d3a'),
           'peach': ('#f1e3d8', '#c9a08a', '#7a4a2e'), 'muted': ('#f3f6f0', '#dce1d8', '#243b32'),
           'plain': ('#ffffff', '#c3ccbd', '#243b32')})

DARK = Palette(
    name='dark', text='#e6ebe4', muted='#a9b3a8', accent='#8fc7b0', hairline='#3a463f',
    page='#10120f', card='#171b16', sunk='#1d231c', cell_masked='#1a201b', cell_hot='#2f4a3a', bar='#4a5a4e',
    tones={'blue': ('#1f2c36', '#5f7f95', '#b9d3e6'), 'green': ('#22301f', '#6f8f62', '#c5dcb8'),
           'peach': ('#332822', '#a07a62', '#ebcdb9'), 'muted': ('#1d231c', '#3a463f', '#e6ebe4'),
           'plain': ('#10120f', '#4a5a4e', '#e6ebe4')})
