#!/usr/bin/env python3
"""Local setup and launcher for the Richman 4 nostalgia fork (GPL-3.0-or-later)."""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from audit_assets import REQUIRED, audit

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / ".local/nostalgia.json"
MUSIC = tuple(f"rich{n:02}.mid" for n in (8, 16, 17, 18, 19, 20, 21, 22)) + tuple(
    f"midi{n:02}.mid" for n in range(1, 17) if n != 14
) + ("midi14-1.mid", "midi14-2.mid")


def asset_directory(explicit=None):
    value = explicit or os.environ.get("RICH4_ASSETS")
    if not value and CONFIG.is_file():
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        if not isinstance(config, dict) or not isinstance(config.get("assets"), str) or not config["assets"].strip():
            raise ValueError("本机素材配置无效，请重新运行 setup")
        value = config["assets"]
    return Path(value or REPO / "game-assets").expanduser().resolve()


def check_assets(directory):
    """Check archive boundaries and music presence; never execute or alter game files."""
    directory = Path(directory)
    if not directory.is_dir():
        return {"directory": str(directory), "errors": ["素材目录不存在"], "warnings": []}
    result = audit(directory)
    # The native engine reads MKFs directly. The original executable is optional.
    result["errors"] = [e for e in result["errors"] if e != "Missing rich4.exe"]
    names = [p.name.lower() for p in directory.iterdir() if p.is_file()]
    if "rich4.exe" not in names:
        result["warnings"] = [w for w in result["warnings"] if not w.startswith("rich4.exe ")]
    duplicate = sorted({n for n in names if n in (*REQUIRED, *MUSIC) and names.count(n) > 1})
    if duplicate:
        result["errors"].append("存在大小写重复的素材文件：" + ", ".join(duplicate))
    missing = [name for name in MUSIC if name not in names]
    if missing:
        result["errors"].append("缺少原版 MIDI 音乐：" + ", ".join(missing))
    empty = [p.name for p in directory.iterdir() if p.is_file() and p.name.lower() in MUSIC
             and p.stat().st_size == 0]
    if empty:
        result["errors"].append("音乐文件为空：" + ", ".join(empty))
    result["scope"] = "仅检查资源包边界与音乐文件；不证明完整解码、画面一致性或可玩性"
    return result


def print_check(result, as_json=False):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print("素材目录：" + result["directory"])
    for error in result["errors"]:
        print("  缺失或错误：" + error)
    for warning in result["warnings"]:
        print("  提示：" + warning)
    if result["errors"]:
        print('请运行：python3 scripts/nostalgia.py setup "/你的大富翁4游戏目录"')
    else:
        print("7 个资源包和 25 个音乐文件的基础检查通过。")


def native_architecture():
    """A Rosetta Python reports x86_64 even when the host has an ARM64 toolchain."""
    architecture = platform.machine()
    if architecture == "x86_64":
        try:
            probe = subprocess.run(["/usr/sbin/sysctl", "-in", "hw.optional.arm64"],
                                   capture_output=True, text=True, check=False)
            if probe.returncode == 0 and probe.stdout.strip() == "1":
                return "arm64"
        except OSError:
            pass
    return architecture


def build_native():
    if sys.platform != "darwin":
        raise RuntimeError("此启动入口用于 macOS；其他平台请参阅 README.upstream.md")
    environment = os.environ.copy()
    architecture = native_architecture()
    prefix = "/opt/homebrew" if architecture == "arm64" else "/usr/local"
    environment["PATH"] = prefix + "/bin:" + environment.get("PATH", "")
    cmake = shutil.which("cmake", path=environment["PATH"])
    if not cmake:
        raise RuntimeError("缺少构建依赖，请先运行：brew install cmake sdl3 freetype fluid-synth pkgconf")
    build = REPO / ("build/mac-nostalgia-" + architecture)
    subprocess.run([cmake, "-S", str(REPO), "-B", str(build), "-DCMAKE_BUILD_TYPE=Release",
                    "-DCMAKE_OSX_ARCHITECTURES=" + architecture, "-DCMAKE_PREFIX_PATH=" + prefix,
                    "-DRICH4_BUILD_GAME=ON", "-DRICH4_BUILD_VIEWER=OFF", "-DRICH4_SANITIZERS=OFF",
                    "-DBUILD_TESTING=OFF"], env=environment, check=True)
    subprocess.run([cmake, "--build", str(build), "--target", "rich4-native", "--parallel",
                    str(min(os.cpu_count() or 2, 8))], env=environment, check=True)
    return build / "rich4-native.app/Contents/MacOS/rich4-native"


def font_path(explicit=None):
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise RuntimeError("找不到指定字体：" + str(path))
        return path
    candidates = [
        Path("/Applications/Microsoft Word.app/Contents/Resources/DFonts/mingliu.ttc"),
        Path("/Applications/Microsoft Excel.app/Contents/Resources/DFonts/mingliu.ttc"),
        Path.home() / "Library/Fonts/mingliu.ttc",
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
    ]
    for path in candidates:
        if path.is_file():
            if path.name.lower() != "mingliu.ttc":
                print("使用系统中文字体；字形与原版细明体存在差异：" + path.name)
            return path
    raise RuntimeError("未找到中文字体；请使用 play --font 指向本机可用的中文字体")


def main(argv=None):
    parser = argparse.ArgumentParser(description="大富翁4怀旧版：本机素材配置与启动")
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("setup", help="记住本机素材位置，不复制素材")
    setup.add_argument("directory", type=Path)
    check = commands.add_parser("check", help="只读检查素材")
    check.add_argument("--assets", type=Path)
    check.add_argument("--json", action="store_true")
    commands.add_parser("build", help="只构建原生程序，不需要原版素材")
    play = commands.add_parser("play", help="检查素材并启动原版画面游戏")
    play.add_argument("--assets", type=Path)
    play.add_argument("--font", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            print("程序已构建：" + str(build_native()))
            return 0
        directory = args.directory.expanduser().resolve() if args.command == "setup" else asset_directory(args.assets)
        result = check_assets(directory)
        print_check(result, getattr(args, "json", False))
        if result["errors"]:
            return 2
        if args.command == "setup":
            CONFIG.parent.mkdir(parents=True, exist_ok=True)
            CONFIG.write_text(json.dumps({"assets": str(directory)}, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
            print("已保存本机配置；现在可以双击「启动怀旧版.command」。")
        elif args.command == "play":
            font = font_path(args.font)
            binary = build_native()
            save_dir = Path.home() / "Library/Application Support/Rich4Nostalgia/saves"
            log = REPO / "artifacts/nostalgia-runtime.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            print("启动游戏；存档目录：" + str(save_dir), flush=True)
            with log.open("w", encoding="utf-8") as output:
                status = subprocess.run([str(binary), "--assets", str(directory), "--font", str(font),
                                         "--save-dir", str(save_dir)], stdout=output, stderr=subprocess.STDOUT).returncode
            if status:
                print("游戏未正常退出，日志：" + str(log))
                print(log.read_text(encoding="utf-8", errors="replace")[-3000:])
            return status
        return 0
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as error:
        print("无法完成：" + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
