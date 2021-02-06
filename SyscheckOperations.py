import sys
import re
import pathlib
from enum import Enum, auto
from typing import Iterator, Tuple


class ReturnCodes(Enum):
    NORMAL = 0
    VWII_NOT_SUPPORTED = 1


class IOSType(Enum):
    STUB = 0
    ACTIVE = 1
    CUSTOM = 2


# These are simple substring matches, no reason to bother with regex
vwii_detect = "vIOS"
stub_detect = "Stub"
patch_usb_2_detect = "USB 2.0"
patch_nand_access_detect = "NAND Access"
patch_trucha_patch_detect = "Trucha Bug"
patch_eticket_services_detect = "ES Identify"
patch_no_patches_detect = "No Patches"
cios_hermes_detect = "hermes"
cios_wanikoko_detect = "wanikoko"
# big boy time
re_ios_tid = re.compile(r"IOS(\d{1,3})")
re_cios_title_base_detect = re.compile(
    r"IOS(\d{1,3})\[(\d{1,3})\]"
)  # Group 1 = tid Group 2 = Base IOS
re_d2x_detect = re.compile(
    r"d2x-(v\d{1,2})(beta|final)(\d{0,2}(-alt)?)"
)  # Group 1 d2x version "v10" Group 2 beta or final Group 3 beta version
re_lazy_full_info = re.compile(r"Info: (.*)\)")  # Group 1 the full "info" line from syscheck


def process_syscheck(syscheck_lines: Iterator[str]) -> Tuple[dict, int]:
    results = dict()
    for entry in syscheck_lines:
        match = re_ios_tid.search(entry)
        if match:
            ios_tid = int(match.group(1))
        else:
            continue
        if vwii_detect in entry:
            return (None, ReturnCodes.VWII_NOT_SUPPORTED)
        if stub_detect in entry:
            results.update({ios_tid: (IOSType.STUB, None)})
            continue
        if patch_no_patches_detect in entry:
            results.update({ios_tid: (IOSType.ACTIVE, None)})
            continue
        if (
            patch_usb_2_detect in entry and ios_tid == 58
        ):  # Special case, IOS 58 has USB 2.0 "Patch" normally, but don't continue immediately because it may have other patches making it a cIOS
            results.update({ios_tid: (IOSType.ACTIVE, None)})
        if (
            (patch_nand_access_detect in entry)
            or (patch_eticket_services_detect in entry)
            or (patch_trucha_patch_detect in entry)
            or (patch_usb_2_detect in entry and ios_tid != 58)
        ):
            results.update({ios_tid: (IOSType.CUSTOM, re_lazy_full_info.search(entry).group(1))})
    return (results, ReturnCodes.NORMAL)


def interactive(infile: pathlib.Path) -> int:
    from pprint import pprint

    result, ret = process_syscheck((line for line in open(infile)))
    pprint(result)
    return ret


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("syscheck_file", help="syscheck.csv to process")
    infile = pathlib.Path(parser.parse_args().syscheck_file).absolute()
    ret = interactive(infile)
    sys.exit(ret)
