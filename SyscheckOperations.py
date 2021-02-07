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
    CIOS_D2X = 2
    CIOS_HERMES = 3
    CIOS_WANIKOKO = 4
    CIOS_UNKNOWN = 5


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
    r"d2x-(v\d{1,2})(beta|final)?(\d{0,2}(-alt)?)"
)  # Group 1 d2x version "v10" Group 2 beta or final Group 3 beta version
re_lazy_full_info = re.compile(r"Info: (.*)\)")  # Group 1 the full "info" line from syscheck
re_sysmenu = re.compile(r"System Menu (.\..)")
sysmenu_ios_map = {
    "4.3": 80,
    "4.2": 70,
    "4.1": 60,
    "4.0": 60,
    "3.5": 52,
    "3.4": 50,
    "3.3": 30,
    "3.2": 30,
    "3.1": 30,
    "3.0": 30,
    "2.2": 20,
    "2.1": 11,
    "2.0": 11,
    "1.0": 9,
}
re_hbc = re.compile(r"Homebrew Channel (.*) running on IOS(\d{1,3})")


def process_syscheck(syscheck_lines: Iterator[str]) -> Tuple[dict, int]:
    # one time checks
    sysmenu_found = False
    hbc_found = False
    results = dict()
    for entry in syscheck_lines:
        if not sysmenu_found:
            match = re_sysmenu.search(entry)
            if match:
                results.update({"SYSMENU": match.group(1)})
                sysmenu_found = True
                continue
        if not hbc_found:
            match = re_hbc.search(entry)
            if match:
                results.update({"HBC": (match.group(1), match.group(2))})
                hbc_found = True
                continue
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
            results.update({ios_tid: cios_detect(entry)})
    return (results, ReturnCodes.NORMAL)


def cios_detect(syscheck_entry: str):
    if "d2x" in syscheck_entry:
        return (IOSType.CIOS_D2X, process_d2x(syscheck_entry))
    if cios_hermes_detect in syscheck_entry:
        return (IOSType.CIOS_HERMES, re_lazy_full_info.search(syscheck_entry).group(1))
    if cios_wanikoko_detect in syscheck_entry:
        return (IOSType.CIOS_WANIKOKO, re_lazy_full_info.search(syscheck_entry).group(1))
    else:
        return (IOSType.CIOS_UNKNOWN, "Generic cIOS")


def process_d2x(syscheck_entry: str) -> dict:
    base = re_cios_title_base_detect.search(syscheck_entry).group(2)
    d2x_info = re_d2x_detect.search(syscheck_entry)
    d2x_ver = d2x_info.group(1)
    d2x_release = d2x_info.group(2)
    d2x_beta_ver = d2x_info.group(3)
    return {
        "base": base,
        "d2x_ver": d2x_ver,
        "d2x_release": d2x_release,
        "d2x_beta_ver": d2x_beta_ver,
    }


def gen_report_for_ios(ios: int, lut: dict):
    if ios not in lut:
        return f"IOS {ios} not found in sysCheck"
    entry = lut[ios]
    if entry[0] == IOSType.ACTIVE:
        return f"IOS {ios} : Active Unmodified IOS"
    if entry[0] == IOSType.STUB:
        return f"IOS {ios} : Stubbed IOS"
    if (
        entry[0] == IOSType.CIOS_UNKNOWN
        or entry[0] == IOSType.CIOS_HERMES
        or entry[0] == IOSType.CIOS_WANIKOKO
    ):
        return f"IOS {ios} : cIOS {entry[1]}"
    if entry[0] == IOSType.CIOS_D2X:
        d2x_base = entry[1]["base"]
        d2x_ver = entry[1]["d2x_ver"]
        d2x_release = entry[1]["d2x_release"]
        d2x_beta_ver = entry[1]["d2x_beta_ver"]
        return f"IOS {ios} : d2x cIOS Base: {d2x_base} Version: {d2x_ver} Release: {d2x_release}{d2x_beta_ver}"


def interactive(infile: pathlib.Path) -> int:
    result, ret = process_syscheck((line for line in open(infile)))
    try:
        sysmenu = result["SYSMENU"]
        sysmenu_ios = sysmenu_ios_map[sysmenu]
    except KeyError:
        sysmenu = "?"
        sysmenu_ios = None
    try:
        hbc = result["HBC"][0]
        hbc_ios = int(result["HBC"][1])
    except KeyError:
        hbc = "?"
        hbc_ios = None
    print("---- Quick Report ----")
    print(f"System Menu version {sysmenu}")
    print(f"Homebrew Channel version {hbc}")
    if sysmenu_ios:
        print(gen_report_for_ios(sysmenu_ios, result))
    if hbc_ios != 58:
        print(gen_report_for_ios(hbc_ios, result))
    print(gen_report_for_ios(58, result))
    [print(gen_report_for_ios(n, result)) for n in range(249, 252)]
    return ret


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("syscheck_file", help="syscheck.csv to process")
    infile = pathlib.Path(parser.parse_args().syscheck_file).absolute()
    ret = interactive(infile)
    sys.exit(ret)
