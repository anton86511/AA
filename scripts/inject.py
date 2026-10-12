#!/usr/bin/env python3
"""Inject iSponsorBlock.dylib (+ resource bundle) into a decrypted IPA.

usage: inject.py IN.ipa OUT.ipa [--substrate /path/to/libellekit.dylib]
"""
import argparse, os, plistlib, shutil, subprocess, sys, tempfile, zipfile
import lief

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DYLIB = os.path.join(ROOT, "tweak", "iSponsorBlock.dylib")
BUNDLE = os.path.join(ROOT, "tweak", "iSponsorBlock.bundle")
SUBSTRATE_OLD = "/Library/Frameworks/CydiaSubstrate.framework/CydiaSubstrate"
SUBSTRATE_NEW = "@rpath/CydiaSubstrate.framework/CydiaSubstrate"
TWEAK_LOAD = "@executable_path/Frameworks/iSponsorBlock.dylib"


def macho(path):
    fat = lief.MachO.parse(path)
    if fat is None:
        sys.exit(f"cannot parse Mach-O: {path}")
    return fat


def write(fat, path):
    fat.write(path)


def patch_tweak(dst, with_substrate):
    fat = macho(dst)
    for b in fat:
        for lib in b.libraries:
            if lib.name == "/Library/MobileSubstrate/DynamicLibraries/iSponsorBlock.dylib":
                lib.name = "@rpath/iSponsorBlock.dylib"  # install name
            elif lib.name == SUBSTRATE_OLD and with_substrate:
                lib.name = SUBSTRATE_NEW
        if with_substrate and not any(r.path == "@loader_path/.." for r in b.rpaths):
            b.add(lief.MachO.RPathCommand.create("@loader_path/.."))
            b.add(lief.MachO.RPathCommand.create("@executable_path/Frameworks"))
    write(fat, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ipa_in"); ap.add_argument("ipa_out")
    ap.add_argument("--keep-extensions", action="store_true",
                    help="keep PlugIns/Extensions/Watch (default: removed, they break sideload signing with a changed bundle ID)")
    ap.add_argument("--require-substrate", action="store_true", help="fail if dependencies stay unresolved")
    ap.add_argument("--substrate", help="ElleKit/Substrate dylib to bundle as CydiaSubstrate.framework")
    a = ap.parse_args()

    work = tempfile.mkdtemp()
    with zipfile.ZipFile(a.ipa_in) as z:
        z.extractall(work)
    payload = os.path.join(work, "Payload")
    apps = [d for d in os.listdir(payload) if d.endswith(".app")]
    if len(apps) != 1:
        sys.exit(f"expected exactly one .app in Payload, got {apps}")
    app = os.path.join(payload, apps[0])
    with open(os.path.join(app, "Info.plist"), "rb") as f:
        info = plistlib.load(f)
    print("App:", info.get("CFBundleIdentifier"), info.get("CFBundleShortVersionString"))
    exe = os.path.join(app, info["CFBundleExecutable"])

    # encryption check (cryptid must be 0)
    efat = macho(exe)
    for b in efat:
        if b.has_encryption_info and b.encryption_info.crypt_id != 0:
            sys.exit("ERROR: this IPA is still FairPlay-encrypted (cryptid != 0). Use a decrypted IPA.")

    if not a.keep_extensions:
        for d in ("PlugIns", "Extensions", "Watch", "SC_Info"):
            t = os.path.join(app, d)
            if os.path.isdir(t):
                print("Removing", d)
                shutil.rmtree(t)
        info.pop("UISupportedDevices", None)
        with open(os.path.join(app, "Info.plist"), "wb") as f:
            plistlib.dump(info, f)

    fw = os.path.join(app, "Frameworks")
    os.makedirs(fw, exist_ok=True)
    dst = os.path.join(fw, "iSponsorBlock.dylib")
    shutil.copy2(DYLIB, dst)

    with_sub = False
    if a.substrate and os.path.isfile(a.substrate):
        sd = os.path.join(fw, "CydiaSubstrate.framework")
        os.makedirs(sd, exist_ok=True)
        shutil.copy2(a.substrate, os.path.join(sd, "CydiaSubstrate"))
        with open(os.path.join(sd, "Info.plist"), "wb") as f:
            plistlib.dump({"CFBundleIdentifier": "com.saurik.substrate", "CFBundleExecutable": "CydiaSubstrate",
                           "CFBundlePackageType": "FMWK", "CFBundleName": "CydiaSubstrate",
                           "CFBundleVersion": "1.0", "CFBundleShortVersionString": "1.0"}, f)
        # make the substrate dylib loadable from the app
        sf = macho(os.path.join(sd, "CydiaSubstrate"))
        for b in sf:
            for c in b.commands:
                if c.command == lief.MachO.LoadCommand.TYPE.ID_DYLIB:
                    c.name = SUBSTRATE_NEW
        write(sf, os.path.join(sd, "CydiaSubstrate"))
        with_sub = True
    else:
        print("WARNING: no substrate bundled; your signing tool must provide CydiaSubstrate/ElleKit.")

    patch_tweak(dst, with_sub)

    # resource bundle: the tweak looks in the app root first
    shutil.copytree(BUNDLE, os.path.join(app, "iSponsorBlock.bundle"), dirs_exist_ok=True)

    # add LC_LOAD_DYLIB to the main executable, drop the (now invalid) signature
    fat = macho(exe)
    for b in fat:
        if any(l.name == TWEAK_LOAD for l in b.libraries):
            continue
        b.add_library(TWEAK_LOAD)
        if b.has_code_signature:
            b.remove_signature()
    write(fat, exe + ".new")
    os.replace(exe + ".new", exe)
    os.chmod(exe, 0o755)
    shutil.rmtree(os.path.join(app, "_CodeSignature"), ignore_errors=True)

    # sanity check: every non-system dependency of the tweak must exist inside the app
    problems = []
    tf = macho(dst)
    for b in tf:
        for l in b.libraries:
            n = l.name
            if n.startswith(("/System/", "/usr/lib/")):
                continue
            if n.startswith("@rpath/"):
                ok = os.path.exists(os.path.join(fw, n[7:])) or os.path.exists(os.path.join(app, n[7:]))
            elif n.startswith("@loader_path/"):
                ok = os.path.exists(os.path.join(fw, n[13:]))
            else:
                ok = False
            if not ok and "iSponsorBlock.dylib" not in n:
                problems.append(n)
    if problems:
        print("WARNING: unresolved dependencies (the app WILL crash on launch unless your signer fixes them):")
        for n in problems:
            print("   ", n)
        if a.require_substrate:
            sys.exit("ERROR: --require-substrate set but dependencies are unresolved")

    # re-zip
    if os.path.exists(a.ipa_out):
        os.remove(a.ipa_out)
    subprocess.run(["zip", "-qry9", os.path.abspath(a.ipa_out), "Payload"], cwd=work, check=True)
    shutil.rmtree(work)
    print("Wrote", a.ipa_out)


if __name__ == "__main__":
    main()
