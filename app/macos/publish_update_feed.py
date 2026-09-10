"""Stage a newer signed appcast without allowing an older release to roll it back."""
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

SPARKLE = '{http://www.andymatuschak.org/xml-namespaces/sparkle}'


def version(path):
    items = ET.parse(path).findall('./channel/item')
    if not items or any(item.find('enclosure') is None or
                        not item.find('enclosure').get(SPARKLE + 'edSignature') for item in items):
        raise ValueError('Update feed must contain signed update archives.')
    return max(int(item.findtext(SPARKLE + 'version')) for item in items)


def stage(source, destination):
    incoming = version(source)
    if destination.exists() and version(destination) >= incoming:
        return False
    shutil.copyfile(source, destination)
    return True


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
