
from pathlib import Path

import os
import yaml
import requests
import shutil
import tarfile
import subprocess
import sys

class Config:

    def __init__(self):
        self.data = []
        ConfigPath = str(Path(__file__).parent.parent / "Config.yaml")
        with open(ConfigPath, "r") as stream:
            try:
                self.data = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def GetData(self):
        return self.data

    def GetScriptWorkspaceDir(self):
        return self.data['ScriptWorkspaceDir']

    def GetScriptWorkspaceTempDir(self):
        return str(Path(self.GetScriptWorkspaceDir()) / "Temp")

    def GetScriptWorkspaceCacheDir(self):
        return str(Path(self.GetScriptWorkspaceDir()) / "Cache")

    def GetScriptWorkspaceRecoveryDir(self):
        return str(Path(self.GetScriptWorkspaceDir()) / "Recovery")

    def GetScriptWorkspaceServerDir(self):
        return str(Path(self.GetScriptWorkspaceDir()) / "Server")

    def GetServerDataModsDir(self):
        return str(Path(self.data.CurrentServerData['ServerDataDir']) / "Mods")

    def GetFactorioExecutable(self):
        return str(Path(self.GetScriptWorkspaceServerDir()) / 'bin' / 'x64' / 'factorio')


def InitializeWorkspace():
    RequiredPaths = [
        config.GetScriptWorkspaceTempDir(),
        config.GetScriptWorkspaceCacheDir(),
        config.GetScriptWorkspaceRecoveryDir()
    ]

    for i in RequiredPaths:
        if os.path.exists(i) == False or os.path.isdir(i) == False:
            os.makedirs(i, exist_ok=True)


def DownloadServerData():
    ServerVersion = config.GetData()['Version']

    DownloadURL = f"https://www.factorio.com/get-download/{ServerVersion}/headless/linux64"
    response = requests.get(DownloadURL, stream=True)

    PackagePath = str(Path(config.GetScriptWorkspaceTempDir()) / "FactorioServer.tar.xz")

    open(PackagePath, 'wb').write(response.content)

    return PackagePath

def ExtractServerData(ServerDataPackagePath):
    Tar = tarfile.open(ServerDataPackagePath)
    Tar.extractall(config.GetScriptWorkspaceServerDir())


def StartServer():
    print("Factorio Server started...")

    ExecutablePath = config.GetFactorioExecutable()
    Command = f"{ExecutablePath} --start-server {config.GetData()['SaveName']}"

    try:
        p = subprocess.Popen(Command.split()).wait()
    except subprocess.CalledProcessError as e:
        raise RuntimeError("command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))

    print("Factorio Server ended...")
    return p


def CleanUp():
    shutil.rmtree(config.GetScriptWorkspaceTempDir())


if __name__ == '__main__':
    config = Config()

    if len(sys.argv) == 1:
        print("No commands provided.")
    else:
        arg1 = sys.argv[1]

        if arg1 == "init":
            InitializeWorkspace()
        elif arg1 == "install":
            PackagePath = DownloadServerData()
            ExtractServerData(PackagePath)
            CleanUp()
        elif arg1 == "start":
            StartServer()
        elif arg1 == "cleanup":
            CleanUp()
