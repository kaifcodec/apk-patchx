# APK-Patchx

<h2 align="center">⚡ apk-patchx</h2>

<p align="center">
  <a href="https://pypi.org/project/apk-patchx/">
    <img src="https://img.shields.io/pypi/v/apk-patchx?color=1E90FF&label=PyPI&style=for-the-badge">
  </a>
   
  <img src="https://img.shields.io/badge/Tested%20on-Linux%20%7C%20macOS%20%7C%20Termux-0d1117?style=for-the-badge&logo=android&logoColor=39ff14">
  
  </p>
<br>

---

### 🔥 What is apk-patchx?
`apk-patchx` is a command-line tool that makes APK manipulation fast, modular, and developer-friendly.  
Whether you’re a security researcher, reverse engineer, or power user — it gives you a one-stop solution for:  

- 📦 **Pulling & merging split APKs** directly from connected Android devices  
- 🔍 **Decoding & rebuilding** APKs with apktool  
- 🧩 **Injecting Frida gadgets** into any architecture (`arm`, `arm64`, `x86`, `x86_64`)  
- 📝 **Patching smali/dex** code with your own hooks  
- 🔑 **Auto-signing** APKs for immediate deployment  
- 🎛️ **Custom decode/build options** for advanced workflows  

---

<p align="center">
  <img src="https://placehold.co/1100x150/000000/39ff14?font=JetBrains%20Mono&text=%24%20apk-patchx%20%20patch%20%20--arch%20arm64%20%20%20--frida-version%20%2017.2.8" alt="apk-patchx Terminal Example">
</p>

## Installation

```bash
pip install apk-patchx
```

## Usage

```bash
apk-patchx --help # For help regarding available commands
apk-patchx <COMMAND> --help # For help regarding options usage
apk-patchx patch --help # e.g.
```


### Available Commands

| Command | Description |
|--------|-------------|
| `build`  | Build APK from decoded directory. |
| `decode` | Decode APK file. |
| `patch`  | Patch APK with Frida gadget. |
| `pull`   | Pull APK from connected device. |
| `rename` | Rename APK package. |
| `sign`   | Sign APK file. |

---

## Patch Command (Full Options)

### Options


| Flag | Description |
|------|-------------|
| `-a, --arch [arm,arm64,x86,x86_64]` | **Required.** Target architecture. |
| `-g, --gadget-conf PATH` | Custom Frida gadget config JSON file. |
| `--net` | Add permissive network security config. |
| `-s, --no-src` | Skip DEX disassembly. |
| `--only-main-classes` | Only disassemble main DEX. |
| `--frida-version TEXT` | Specify Frida version to use. |
| `--apktool-decode-args TEXT` | Extra arguments for apktool decode. |
| `--apktool-build-args TEXT` | Extra arguments for apktool build. |
| `--help` | Show help and exit. |

### Rename APK package
```bash
apk-patchx rename app.apk com.newpackage.name
```

### Sign APK
```bash
apk-patchx sign app.apk
```

## Architecture Support

- ARM (`arm`)
- ARM64 (`arm64`) 
- x86 (`x86`)
- x86_64 (`x86_64`)

## Requirements

- Python 3.8+
- Java Runtime Environment (JRE 8+)
- ADB (for device operations)

## Tool Management

APK-Patchx automatically downloads and manages required tools in `~/.apk-patchx/tools/`:

- apktool
- Android SDK build-tools
- Platform tools (adb)
- dexpatch
- Frida gadgets

## License

MIT License - see LICENSE file for details.
