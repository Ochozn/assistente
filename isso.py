import subprocess
import sys
import os
import shutil
import platform
import logging
import importlib.metadata
from typing import List, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command: List[str], shell: bool = False) -> Tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
            shell=shell
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except FileNotFoundError:
        return False, f"Command not found: {command[0]}"

def check_venv():
    """Check if running in a virtual environment."""
    return sys.prefix != sys.base_prefix

def check_admin():
    """Check if running as Administrator."""
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def check_build_environment() -> bool:
    """Check if all required tools, headers, and libraries are available."""
    vcvars_path = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
    if not os.path.exists(vcvars_path):
        logger.error(f"Visual Studio Build Tools not found at {vcvars_path}")
        return False

    # Run vcvars64.bat and capture environment variables
    temp_file = "env_vars.txt"
    command = f'"{vcvars_path}" && set > {temp_file}'
    success, output = run_command(command, shell=True)
    if not success:
        logger.error("C++ compiler (cl.exe) not functional.")
        return False

    # Capture existing INCLUDE, LIB, and PATH
    include_paths = []
    lib_paths = []
    path_entries = []
    with open(temp_file, 'r') as f:
        for line in f:
            if line.startswith("INCLUDE="):
                include_paths = line.strip().split('=')[1].split(';')
            if line.startswith("LIB="):
                lib_paths = line.strip().split('=')[1].split(';')
            if line.startswith("PATH="):
                path_entries = line.strip().split('=')[1].split(';')
    os.remove(temp_file)

    # Define all required paths for building chroma-hnswlib
    sdk_version = "10.0.22621.0"
    required_include_paths = {
        "ucrt": r"C:\Program Files (x86)\Windows Kits\10\Include\{}\ucrt".format(sdk_version),
        "shared": r"C:\Program Files (x86)\Windows Kits\10\Include\{}\shared".format(sdk_version),
        "um": r"C:\Program Files (x86)\Windows Kits\10\Include\{}\um".format(sdk_version),
        "msvc_include": r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.43.34808\include",
        "msvc_atlmfc_include": r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.43.34808\ATLMFC\include",
        "python_include": r"C:\Python312\include",
        "python_include_upper": r"C:\Python312\Include"
    }
    required_lib_paths = {
        "ucrt": r"C:\Program Files (x86)\Windows Kits\10\Lib\{}\ucrt\x64".format(sdk_version),
        "um": r"C:\Program Files (x86)\Windows Kits\10\Lib\{}\um\x64".format(sdk_version),
        "msvc_lib": r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.43.34808\lib\x64",
        "msvc_atlmfc_lib": r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.43.34808\ATLMFC\lib\x64",
        "python_libs": r"C:\Python312\libs",
        "python_pcbuild": r"C:\Python312\PCbuild\amd64"
    }
    required_path_entries = {
        "sdk_bin": r"C:\Program Files (x86)\Windows Kits\10\bin\{}\x64".format(sdk_version),
        "msvc_bin": r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.43.34808\bin\HostX86\x64"
    }

    # Check and add INCLUDE paths
    for key, path in required_include_paths.items():
        if not any(path in p for p in include_paths):
            logger.warning(f"Windows SDK {key} path not found in INCLUDE environment variable.")
            os.environ["INCLUDE"] = os.environ.get("INCLUDE", "") + ";" + path
            logger.info(f"Manually added {path} to INCLUDE")
        # Verify a key header exists in each path
        header_to_check = {
            "ucrt": "float.h",
            "shared": "sal.h",
            "um": "windows.h",
            "msvc_include": "type_traits",
            "msvc_atlmfc_include": "afx.h",
            "python_include": "Python.h",
            "python_include_upper": "pyconfig.h"
        }.get(key)
        if header_to_check and not os.path.exists(os.path.join(path, header_to_check)):
            logger.error(f"{header_to_check} not found in {path}")
            return False
        logger.info(f"Header {header_to_check or 'N/A'} found in {path}")

    # Check and add LIB paths, with relaxed validation for Python libraries
    python_lib_found = False
    for key, path in required_lib_paths.items():
        if not any(path in p for p in lib_paths):
            logger.warning(f"Windows SDK {key} path not found in LIB environment variable.")
            os.environ["LIB"] = os.environ.get("LIB", "") + ";" + path
            logger.info(f"Manually added {path} to LIB")
        # Verify a key library exists in each path
        lib_to_check = {
            "ucrt": "ucrt.lib",
            "um": "kernel32.lib",
            "msvc_lib": "msvcrt.lib",
            "msvc_atlmfc_lib": "mfc140.lib",
            "python_libs": "python312.lib",
            "python_pcbuild": "python312.lib"
        }.get(key)
        if lib_to_check:
            lib_exists = os.path.exists(os.path.join(path, lib_to_check))
            if key in ["python_libs", "python_pcbuild"]:
                if lib_exists:
                    python_lib_found = True
                    logger.info(f"Library {lib_to_check} found in {path}")
                else:
                    logger.info(f"Library {lib_to_check} not found in {path}, checking other paths...")
            else:
                if not lib_exists:
                    logger.error(f"{lib_to_check} not found in {path}")
                    return False
                logger.info(f"Library {lib_to_check} found in {path}")

    # Ensure python312.lib was found in at least one location
    if not python_lib_found:
        logger.error("python312.lib not found in any Python library paths (C:\\Python312\\libs or C:\\Python312\\PCbuild\\amd64)")
        return False

    # Check and add PATH entries
    for key, path in required_path_entries.items():
        if not any(path in p for p in path_entries):
            logger.warning(f"Windows SDK {key} path not found in PATH environment variable.")
            os.environ["PATH"] = os.environ.get("PATH", "") + ";" + path
            logger.info(f"Manually added {path} to PATH")
        # Verify key tools exist in each path
        tools_to_check = {
            "sdk_bin": ["rc.exe", "mt.exe"],
            "msvc_bin": ["cl.exe", "link.exe"]
        }.get(key, [])
        for tool in tools_to_check:
            if not os.path.exists(os.path.join(path, tool)):
                logger.error(f"{tool} not found in {path}")
                return False
            logger.info(f"Tool {tool} found in {path}")

    return True

def guide_visual_studio_installation():
    """Provide instructions to install or repair Visual Studio Build Tools."""
    instructions = r"""
Visual Studio Build Tools 2022 is missing, incomplete, or misconfigured (required headers, libraries, or tools not found).

To compile dependencies like chroma-hnswlib, you need Visual Studio Build Tools 2022 with C++ support.

Please follow these steps:

1. Download Visual Studio Build Tools 2022:
   URL: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
   - Scroll to "All Downloads" and select "Build Tools for Visual Studio 2022".

2. Run the installer and select/modify:
   - Workload: "Desktop development with C++"
   - Components (ensure these are checked):
     - MSVC v143 - VS 2022 C++ x64/x86 build tools (Latest)
     - C++ core features
     - Windows 11 SDK (10.0.22621.0)
     - English language pack
   - Optional: C++ CMake tools for Windows

3. Install or repair (5–10 GB, 10–20 minutes).

4. Verify installation:
   ```
   "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
   echo %INCLUDE%
   echo %LIB%
   echo %PATH%
   ```
   Ensure paths like "C:\Program Files (x86)\Windows Kits\10\Include\10.0.22621.0\ucrt", "C:\Program Files (x86)\Windows Kits\10\Include\10.0.22621.0\shared", "C:\Program Files (x86)\Windows Kits\10\Lib\10.0.22621.0\um\x64", and "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64" are present.

5. Rerun this script after installation.

Press Enter to exit, then rerun the script after installing Build Tools.
"""
    logger.info(instructions)
    input()
    sys.exit(1)

def setup_vcvars_environment() -> bool:
    """Set up Visual Studio environment variables for compilation."""
    vcvars_path = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
    if not os.path.exists(vcvars_path):
        logger.error(f"vcvars64.bat not found at {vcvars_path}")
        return False

    temp_file = "env_vars.bat"
    command = f'"{vcvars_path}" && set > {temp_file}'
    success, output = run_command(command, shell=True)
    if not success:
        logger.error(f"Failed to run vcvars64.bat: {output}")
        return False

    try:
        with open(temp_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        os.remove(temp_file)

        # Ensure all required paths are set
        sdk_version = "10.0.22621.0"
        required_include_paths = [
            r"C:\Program Files (x86)\Windows Kits\10\Include\{}\ucrt".format(sdk_version),
            r"C:\Program Files (x86)\Windows Kits\10\Include\{}\shared".format(sdk_version),
            r"C:\Program Files (x86)\Windows Kits\10\Include\{}\um".format(sdk_version),
            r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.43.34808\include",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.43.34808\ATLMFC\include",
            r"C:\Python312\include",
            r"C:\Python312\Include"
        ]
        required_lib_paths = [
            r"C:\Program Files (x86)\Windows Kits\10\Lib\{}\ucrt\x64".format(sdk_version),
            r"C:\Program Files (x86)\Windows Kits\10\Lib\{}\um\x64".format(sdk_version),
            r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.43.34808\lib\x64",
            r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.43.34808\ATLMFC\lib\x64",
            r"C:\Python312\libs",
            r"C:\Python312\PCbuild\amd64"
        ]
        required_path_entries = [
            r"C:\Program Files (x86)\Windows Kits\10\bin\{}\x64".format(sdk_version),
            r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.43.34808\bin\HostX86\x64"
        ]

        # Add INCLUDE paths
        current_include = os.environ.get("INCLUDE", "")
        for path in required_include_paths:
            if path not in current_include:
                os.environ["INCLUDE"] = current_include + ";" + path
                logger.info(f"Manually added {path} to INCLUDE")
                current_include = os.environ["INCLUDE"]

        # Add LIB paths
        current_lib = os.environ.get("LIB", "")
        for path in required_lib_paths:
            if path not in current_lib:
                os.environ["LIB"] = current_lib + ";" + path
                logger.info(f"Manually added {path} to LIB")
                current_lib = os.environ["LIB"]

        # Add PATH entries
        current_path = os.environ.get("PATH", "")
        for path in required_path_entries:
            if path not in current_path:
                os.environ["PATH"] = current_path + ";" + path
                logger.info(f"Manually added {path} to PATH")
                current_path = os.environ["PATH"]

        logger.info("Visual Studio environment variables set.")
        return True
    except Exception as e:
        logger.error(f"Failed to set environment variables: {e}")
        return False

def fix_pip_installation():
    """Repair corrupted pip installation."""
    logger.info("Checking and repairing pip installation...")
    success, output = run_command([sys.executable, "-m", "ensurepip"])
    if not success:
        logger.error(f"Failed to run ensurepip: {output}")
        sys.exit(1)
    success, output = run_command([sys.executable, "-m", "pip", "install", "--force-reinstall", "pip"])
    if success:
        logger.info("pip repaired successfully.")
    else:
        logger.error(f"Failed to repair pip: {output}")
        sys.exit(1)

def clean_pip_cache():
    """Clean pip cache to avoid corrupted downloads."""
    pip_cache = os.path.join(os.getenv("LOCALAPPDATA"), "pip", "Cache")
    if os.path.exists(pip_cache):
        logger.info("Cleaning pip cache...")
        try:
            shutil.rmtree(pip_cache)
            logger.info("Pip cache cleaned.")
        except Exception as e:
            logger.warning(f"Failed to clean pip cache: {e}")

def clean_site_packages():
    """Remove problematic packages from site-packages."""
    site_packages = Path(sys.prefix) / "Lib" / "site-packages"
    if site_packages.exists():
        logger.info("Cleaning problematic packages from site-packages...")
        for item in site_packages.glob("~ip*"):
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                logger.info(f"Removed {item}")
            except Exception as e:
                logger.warning(f"Failed to remove {item}: {e}")

def install_package(package: str, version_constraint: str = "", user_install: bool = False) -> bool:
    """Install a package with optional version constraint."""
    package_spec = f"{package}{version_constraint}"
    logger.info(f"Installing {package_spec}...")
    cmd = [sys.executable, "-m", "pip", "install", package_spec]
    if user_install:
        cmd.append("--user")
    success, output = run_command(cmd)
    if success:
        logger.info(f"Successfully installed {package_spec}")
    else:
        logger.error(f"Failed to install {package_spec}: {output}")
    return success

def verify_installation(package: str) -> bool:
    """Verify if a package is installed and log its version."""
    try:
        version = importlib.metadata.version(package)
        logger.info(f"{package} is installed, version: {version}")
        return True
    except importlib.metadata.PackageNotFoundError:
        logger.error(f"{package} is not installed")
        return False

def main():
    """Install all dependencies for crewai, including build tools setup, and verify."""
    if platform.system() != "Windows":
        logger.error("This script is designed for Windows only.")
        sys.exit(1)

    # Step 1: Check Python version
    if sys.version_info[:2] != (3, 12):
        logger.warning("This script is tested with Python 3.12. You are using Python %s.%s.",
                       sys.version_info[0], sys.version_info[1])

    # Step 2: Check for virtual environment or admin privileges
    if not check_venv() and not check_admin():
        logger.error("Please run this script in a virtual environment or as Administrator to avoid permission issues.")
        logger.info("To create a virtual environment:")
        logger.info("  python -m venv venv")
        logger.info("  venv\\Scripts\\activate")
        logger.info("Or run Command Prompt as Administrator.")
        sys.exit(1)

    # Step 3: Fix pip installation
    clean_site_packages()
    fix_pip_installation()

    # Step 4: Check build environment
    if not check_build_environment():
        guide_visual_studio_installation()

    # Step 5: Set up Visual Studio environment
    if not setup_vcvars_environment():
        logger.error("Failed to set up Visual Studio environment. Please ensure Visual Studio Build Tools is installed.")
        sys.exit(1)

    # Step 6: Clean pip cache
    clean_pip_cache()

    # Step 7: Install dependencies
    dependencies = [
        ("numpy", "==2.1.3"),
        ("chroma-hnswlib", "==0.7.6"),
        ("chromadb", "==0.5.11"),
        ("instructor", "==0.5.2"),
        ("langchain", "==0.1.20"),
        ("langchain-openai", "==0.0.5"),
        ("openai", "==1.72.0"),
        ("opentelemetry-api", "==1.32.0"),
        ("opentelemetry-exporter-otlp-proto-http", "==1.32.0"),
        ("opentelemetry-sdk", "==1.32.0"),
        ("pydantic", "==2.11.3"),
        ("regex", "==2023.12.25"),
        ("crewai", "==0.114.0")
    ]

    all_installed = True
    user_install = False
    for package, version in dependencies:
        success = install_package(package, version, user_install)
        if not success and not user_install:
            logger.info("Retrying with --user flag due to permission issues...")
            user_install = True
            success = install_package(package, version, user_install)
        if not success:
            all_installed = False

    # Step 8: Verify installations
    logger.info("\nVerifying installations...")
    verification_passed = True
    for package, _ in dependencies:
        if not verify_installation(package):
            verification_passed = False

    # Step 9: Final message
    if all_installed and verification_passed:
        logger.info("\n🎉 All dependencies, including crewai and C++ build requirements, installed and verified successfully!")
        logger.info("You can now use crewai. Example:")
        logger.info("```python\n"
                    "import crewai\n"
                    "print(crewai.__version__)\n"
                    "```")
    else:
        logger.error("\n❌ Some dependencies failed to install or verify. Please check the logs above.")
        logger.info("Common issues and fixes:")
        logger.info("- Missing tools: Ensure Visual Studio Build Tools includes Windows 11 SDK (10.0.22621.0).")
        logger.info("- Permission errors: Run this script as Administrator or in a virtual environment.")
        logger.info("- Corrupted pip: The script attempted to fix this; if issues persist, reinstall Python.")
        logger.info("- Run as Administrator: Open Command Prompt as Administrator and rerun the script.")
        sys.exit(1)

if __name__ == "__main__":
    main()