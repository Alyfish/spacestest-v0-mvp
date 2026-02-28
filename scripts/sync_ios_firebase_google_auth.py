#!/usr/bin/env python3
"""
Sync iOS Firebase + Google auth config from a production GoogleService-Info.plist.

This script updates repo-tracked files that commonly drift out of sync:
- ios-frontend/ios/Runner/GoogleService-Info.plist (copy from source if needed)
- ios-frontend/lib/firebase_options.dart (iOS + macOS FirebaseOptions blocks)
- ios-frontend/ios/Runner/Info.plist (GIDClientID + reversed Google URL scheme)

It can also run in check-only mode to validate current state.
"""

from __future__ import annotations

import argparse
import plistlib
import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_GOOGLE_PLIST = ROOT / "ios-frontend/ios/Runner/GoogleService-Info.plist"
RUNNER_INFO_PLIST = ROOT / "ios-frontend/ios/Runner/Info.plist"
FIREBASE_OPTIONS_DART = ROOT / "ios-frontend/lib/firebase_options.dart"
SUPABASE_SERVICE_DART = ROOT / "ios-frontend/lib/services/supabase_service.dart"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync iOS Firebase + Google auth config in this repo.",
    )
    parser.add_argument(
        "--firebase-plist",
        default=str(RUNNER_GOOGLE_PLIST),
        help="Path to the production GoogleService-Info.plist to use.",
    )
    parser.add_argument(
        "--expected-bundle-id",
        default="com.spaces.app",
        help="Production iOS bundle ID expected in the Firebase plist.",
    )
    parser.add_argument(
        "--google-ios-client-id",
        default="",
        help=(
            "Optional iOS OAuth client ID (331...apps.googleusercontent.com). "
            "Used if CLIENT_ID is not present in the Firebase plist."
        ),
    )
    parser.add_argument(
        "--google-reversed-client-id",
        default="",
        help=(
            "Optional reversed iOS OAuth client ID (com.googleusercontent.apps...). "
            "Used if REVERSED_CLIENT_ID is not present in the Firebase plist."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag, the script only validates and prints what is needed.",
    )
    return parser.parse_args()


def read_plist(path: Path) -> dict:
    try:
        with path.open("rb") as f:
            data = plistlib.load(f)
    except FileNotFoundError:
        fail(f"File not found: {path}")
    except Exception as exc:
        fail(f"Failed to parse plist {path}: {exc}")
    if not isinstance(data, dict):
        fail(f"Unexpected plist root type in {path}: {type(data)!r}")
    return data


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def info(message: str) -> None:
    print(message)


def derive_reversed_client_id(client_id: str) -> str:
    suffix = ".apps.googleusercontent.com"
    if client_id.endswith(suffix):
        return f"com.googleusercontent.apps.{client_id[:-len(suffix)]}"
    return ""


def replace_line_value(text: str, key: str, new_value: str) -> str:
    pattern = re.compile(
        rf"(^\s*{re.escape(key)}:\s*)'[^']*'(,\s*$)",
        re.MULTILINE,
    )
    new_text, count = pattern.subn(rf"\1'{new_value}'\2", text, count=1)
    if count != 1:
        fail(f"Could not find `{key}` in FirebaseOptions block")
    return new_text


def replace_firebase_block(text: str, block_name: str, values: dict[str, str]) -> str:
    block_pattern = re.compile(
        rf"(static const FirebaseOptions {re.escape(block_name)} = FirebaseOptions\(\n)(.*?)(\n  \);)",
        re.DOTALL,
    )
    match = block_pattern.search(text)
    if not match:
        fail(f"Could not find `{block_name}` FirebaseOptions block in firebase_options.dart")

    block_body = match.group(2)
    updated = block_body
    for key, value in values.items():
        updated = replace_line_value(updated, key, value)

    return text[: match.start(2)] + updated + text[match.end(2) :]


def update_firebase_options(dart_path: Path, firebase_plist: dict, expected_bundle_id: str, apply: bool) -> bool:
    text = dart_path.read_text(encoding="utf-8")

    values = {
        "apiKey": str(firebase_plist["API_KEY"]),
        "appId": str(firebase_plist["GOOGLE_APP_ID"]),
        "messagingSenderId": str(firebase_plist["GCM_SENDER_ID"]),
        "projectId": str(firebase_plist["PROJECT_ID"]),
        "storageBucket": str(firebase_plist["STORAGE_BUCKET"]),
        "iosBundleId": expected_bundle_id,
    }

    new_text = replace_firebase_block(text, "ios", values)
    # This project currently reuses the iOS Firebase app config for macOS.
    new_text = replace_firebase_block(text=new_text, block_name="macos", values=values)

    changed = new_text != text
    if changed and apply:
        dart_path.write_text(new_text, encoding="utf-8")
    return changed


def _replace_info_plist_gid(text: str, client_id: str) -> str:
    pattern = re.compile(r"(<key>GIDClientID</key>\s*<string>)([^<]*)(</string>)", re.DOTALL)
    new_text, count = pattern.subn(rf"\g<1>{client_id}\g<3>", text, count=1)
    if count != 1:
        fail("Could not find GIDClientID in Info.plist")
    return new_text


def _replace_info_plist_google_scheme(text: str, reversed_client_id: str) -> str:
    pattern = re.compile(r"(<string>)(com\.googleusercontent\.apps\.[^<]*)(</string>)")
    new_text, count = pattern.subn(rf"\g<1>{reversed_client_id}\g<3>", text, count=1)
    if count != 1:
        fail("Could not find Google URL scheme (com.googleusercontent.apps...) in Info.plist")
    return new_text


def update_info_plist(info_plist_path: Path, client_id: str, reversed_client_id: str, apply: bool) -> bool:
    text = info_plist_path.read_text(encoding="utf-8")
    new_text = _replace_info_plist_gid(text, client_id)
    new_text = _replace_info_plist_google_scheme(new_text, reversed_client_id)
    changed = new_text != text
    if changed and apply:
        info_plist_path.write_text(new_text, encoding="utf-8")
    return changed


def ensure_no_legacy_hardcoded_ios_client_id() -> tuple[bool, str]:
    text = SUPABASE_SERVICE_DART.read_text(encoding="utf-8")
    legacy_constant_present = "_googleIosClientId =" in text
    override_present = "GOOGLE_IOS_CLIENT_ID" in text
    if legacy_constant_present:
        return False, "Legacy hardcoded _googleIosClientId constant still present in supabase_service.dart"
    if not override_present:
        return False, "GOOGLE_IOS_CLIENT_ID override path not found in supabase_service.dart"
    return True, "SupabaseService no longer hardcodes the iOS Google client ID"


def main() -> None:
    args = parse_args()

    firebase_plist_path = Path(args.firebase_plist).expanduser().resolve()
    firebase_plist = read_plist(firebase_plist_path)

    required_keys = ["API_KEY", "GCM_SENDER_ID", "BUNDLE_ID", "PROJECT_ID", "STORAGE_BUCKET", "GOOGLE_APP_ID"]
    missing_keys = [k for k in required_keys if k not in firebase_plist]
    if missing_keys:
        fail(f"Firebase plist is missing required keys: {', '.join(missing_keys)}")

    bundle_id = str(firebase_plist.get("BUNDLE_ID", "")).strip()
    if bundle_id != args.expected_bundle_id:
        fail(
            f"Firebase plist BUNDLE_ID is `{bundle_id}` but expected "
            f"`{args.expected_bundle_id}`. Download the prod iOS plist for the correct app."
        )

    client_id = str(firebase_plist.get("CLIENT_ID") or args.google_ios_client_id).strip()
    reversed_client_id = str(
        firebase_plist.get("REVERSED_CLIENT_ID")
        or args.google_reversed_client_id
        or derive_reversed_client_id(client_id)
    ).strip()

    info(f"Using Firebase plist: {firebase_plist_path}")
    info(f"Firebase project: {firebase_plist['PROJECT_ID']}")
    info(f"Firebase iOS bundle ID: {bundle_id}")

    if firebase_plist_path != RUNNER_GOOGLE_PLIST:
        if args.apply:
            shutil.copy2(firebase_plist_path, RUNNER_GOOGLE_PLIST)
            info(f"Updated {RUNNER_GOOGLE_PLIST}")
        else:
            info(f"Would copy {firebase_plist_path} -> {RUNNER_GOOGLE_PLIST}")
    else:
        info(f"Using in-place repo plist: {RUNNER_GOOGLE_PLIST}")

    firebase_options_changed = update_firebase_options(
        FIREBASE_OPTIONS_DART,
        firebase_plist=firebase_plist,
        expected_bundle_id=args.expected_bundle_id,
        apply=args.apply,
    )
    info(
        ("Updated" if firebase_options_changed and args.apply else "Would update" if firebase_options_changed else "No change")
        + f" {FIREBASE_OPTIONS_DART}"
    )

    if not client_id or not reversed_client_id:
        info(
            "Google iOS client values not found in Firebase plist. "
            "Pass --google-ios-client-id and --google-reversed-client-id to update Info.plist."
        )
        if args.apply:
            fail(
                "Cannot apply Info.plist Google auth updates without iOS client values. "
                "Provide --google-ios-client-id and --google-reversed-client-id."
            )
    else:
        info_plist_changed = update_info_plist(
            RUNNER_INFO_PLIST,
            client_id=client_id,
            reversed_client_id=reversed_client_id,
            apply=args.apply,
        )
        info(
            ("Updated" if info_plist_changed and args.apply else "Would update" if info_plist_changed else "No change")
            + f" {RUNNER_INFO_PLIST}"
        )

    ok, message = ensure_no_legacy_hardcoded_ios_client_id()
    info(message)
    if not ok:
        fail(message)

    info("")
    info("Next checks:")
    info(f"- Confirm `{RUNNER_GOOGLE_PLIST}` has BUNDLE_ID `{args.expected_bundle_id}`")
    info(f"- Confirm `{FIREBASE_OPTIONS_DART}` no longer references `com.example.spaces` in iOS/macos blocks")
    info(f"- Confirm `{RUNNER_INFO_PLIST}` GIDClientID + Google URL scheme match the prod iOS OAuth client")
    info("- Run on a physical iPhone and test Google sign-in callback")


if __name__ == "__main__":
    main()
