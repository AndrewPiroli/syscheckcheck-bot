import sys
import re
import pathlib
from enum import Enum, auto
from typing import Iterator, Tuple


class IOSType(Enum):
    STUB = auto()
    ACTIVE = auto()
    CIOS_D2X = auto()
    CIOS_HERMES = auto()
    CIOS_WANIKOKO = auto()
    CIOS_UNKNOWN = auto()
    BOOTMII_IOS = auto()


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
priiloader_detect = "Priiloader installed"
bootmii_ios_detect = "BootMii"
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
re_hbc = re.compile(
    r"Homebrew Channel (.*) running on IOS(\d{1,3})"
)  # Group 1: HBC version Group 2: HBC IOS
re_region = re.compile(r"Region: (\w*(\-.)?)")
re_original_region = re.compile(r"\(original region: (.*)\)")
re_drive_date_detect = re.compile(r"Drive date: (.*)$")  # Group 1
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


def process_syscheck(syscheck_lines: Iterator[str]) -> dict:
    # one time checks
    sysmenu_found = False
    hbc_found = False
    region_found = False
    priiloader_found = False
    drive_date_found = False
    results = {
        "SYSMENU": "Unknown",
        "HBC": ["Unknown", 0],
        "Priiloader": False,
        "CURR_REGION": "Unknown",
        "ORIGINAL_REGION": True,
    }
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
        if not region_found:
            match = re_region.search(entry)
            if match:
                results.update({"CURR_REGION": match.group(1)})
                changed_region = re_original_region.search(entry)
                if changed_region:
                    results.update({"ORIGINAL_REGION": changed_region.group(1)})
                continue
        if not priiloader_found:
            if priiloader_detect in entry:
                results.update({"Priiloader": True})
        if not drive_date_found:
            match = re_drive_date_detect.search(entry)
            if match:
                results.update({"DRIVEDATE": match.group(1)})
        match = re_ios_tid.search(entry)
        if match:
            ios_tid = int(match.group(1))
        else:
            continue
        if vwii_detect in entry:
            return None  # Not supported
        if stub_detect in entry:
            results.update({ios_tid: (IOSType.STUB, None)})
            continue
        if patch_no_patches_detect in entry:
            results.update({ios_tid: (IOSType.ACTIVE, None)})
            continue
        if (
            ios_tid == 58 and patch_usb_2_detect in entry
        ):  # Special case, IOS 58 has USB 2.0 "Patch" normally, but don't continue immediately because it may have other patches making it a cIOS
            results.update({ios_tid: (IOSType.ACTIVE, None)})
        if (
            (patch_nand_access_detect in entry)
            or (patch_eticket_services_detect in entry)
            or (patch_trucha_patch_detect in entry)
            or (ios_tid != 58 and patch_usb_2_detect in entry)
        ):
            results.update({ios_tid: cios_detect(entry)})
        if ios_tid == 254 and bootmii_ios_detect in entry:
            results.update({ios_tid: (IOSType.BOOTMII_IOS, None)})
    return results


def cios_detect(syscheck_entry: str) -> Tuple[IOSType, str]:
    if "d2x" in syscheck_entry:
        return (IOSType.CIOS_D2X, process_d2x(syscheck_entry))
    if cios_hermes_detect in syscheck_entry:
        return (IOSType.CIOS_HERMES, re_lazy_full_info.search(syscheck_entry).group(1))
    if cios_wanikoko_detect in syscheck_entry:
        return (IOSType.CIOS_WANIKOKO, re_lazy_full_info.search(syscheck_entry).group(1))
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


def gen_report_for_ios(ios: int, lut: dict) -> str:
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
    if entry[0] == IOSType.BOOTMII_IOS:
        return f"BootMii IOS Installed at tid:{ios}"
    return f"Error generating report for IOS {ios}"


def summaraize(infile: pathlib.Path):
    report = []
    result = process_syscheck((line for line in open(infile)))
    # These next few lines are cancer, I know, I know
    sysmenu = result["SYSMENU"]
    if sysmenu != "Unknown":
        sysmenu_ios = sysmenu_ios_map[sysmenu]
    else:
        sysmenu_ios = "???"
    hbc = result["HBC"][0]
    if hbc[0] != "Unknown":
        hbc_ios = int(result["HBC"][1])
    else:
        hbc = ("Unknown", 58)  # Trust me ok
    report.append(f"System Menu version {sysmenu} using IOS {sysmenu_ios}")
    if "CURR_REGION" in result:
        report.append("Current Region: {}".format(result["CURR_REGION"]))
    if "ORIGINAL_REGION" in result:
        report.append("Original Region: {}".format(result["ORIGINAL_REGION"]))
    report.append(f"Homebrew Channel version {hbc} using IOS {hbc_ios}")
    if result["DRIVEDATE"]:
        report.append("Drive date: {}".format(result["DRIVEDATE"]))
    if result["Priiloader"]:
        report.append("Priiloader is installed")
    else:
        report.append("Priiloader not installed")
    if sysmenu_ios != "Unknown":
        report.append(gen_report_for_ios(sysmenu_ios, result))
    if hbc_ios != 58 and hbc_ios != "Unknown":
        report.append(gen_report_for_ios(hbc_ios, result))
    [report.append(gen_report_for_ios(n, result)) for n in [58, 249, 250, 251, 254]]
    ios_total = 0
    ios_active = 0
    ios_cios = 0
    ios_stub = 0
    for k, v in result.items():
        if isinstance(k, int):
            ios_typ: IOSType = v[0]
            ios_total += 1
            if ios_typ == IOSType.ACTIVE:
                ios_active += 1
                continue
            if ios_typ == IOSType.STUB:
                ios_stub += 1
                continue
            if (
                ios_typ == IOSType.CIOS_D2X
                or ios_typ == IOSType.CIOS_HERMES
                or ios_typ == IOSType.CIOS_WANIKOKO
                or ios_typ == IOSType.CIOS_UNKNOWN
            ):
                ios_cios += 1
                continue
            if ios_typ == IOSType.BOOTMII_IOS:
                ios_active += 1
    report.append(f"Total IOS count: {ios_total}")
    report.append(f"Stubs: {ios_stub} total. {round((ios_stub/ios_total)*100,2)}% of total")
    report.append(f"Active: {ios_active} total. {round((ios_active/ios_total)*100,2)}% of total")
    report.append(
        f"cIOS: {ios_cios} total. {round((ios_cios/(ios_total - ios_stub)*100),2)}% of non-stub"
    )
    return "\n".join(report)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("syscheck_file", help="syscheck.csv to process")
    infile = pathlib.Path(parser.parse_args().syscheck_file).absolute()
    print(summaraize(infile))
