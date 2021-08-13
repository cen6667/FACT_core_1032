#!/usr/bin/env python3

import logging
import pathlib

try:
    from helperFunctions.install import run_cmd_with_logging, check_distribution

    from ...installer import AbstractPluginInstaller
except ImportError:
    import sys
    print(
        'Could not import dependencies.\n' +
        'Try starting with "python3 -m plugins.analysis.PLUGIN_NAME.install" from the FACT_core/src directory',
        file=sys.stderr
    )
    sys.exit(1)

# The base directory of the plugin
base_path = pathlib.Path(__file__).resolve().parent


class InputVectorsInstaller(AbstractPluginInstaller):
    def install_docker_images(self):
        run_cmd_with_logging('docker build -t input-vectors .', shell=True)
        run_cmd_with_logging('docker pull fkiecad/radare-web-gui:latest', shell=True)


# Alias for generic use
Installer = InputVectorsInstaller

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    distribution = check_distribution()
    installer = Installer(base_path, distribution)
    installer.install()
