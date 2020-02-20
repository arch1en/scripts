
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
        ConfigPath = str(Path(__file__).absolute().parent.parent / "Config.yaml")
        with open(ConfigPath, "r") as stream:
            try:
                self.data = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def GetData(self):
        return self.data

    def GetScriptWorkspaceDir(self):
        return Path(self.data['ScriptWorkspaceDir'])

    # Required Dirs
    def GetScriptWorkspaceTempDir(self):
        return Path(self.GetScriptWorkspaceDir()) / "Temp"

    def GetScriptWorkspaceServerDir(self):
        return Path(self.GetScriptWorkspaceDir()) / "Server"

    def GetScriptWorkspaceSavesDir(self):
        return Path(self.GetScriptWorkspaceDir()) / "Saves"
    # ~Required Dirs

    def GetScriptWorkspaceRequiredDirs(self):
        return [self.GetScriptWorkspaceTempDir(), self.GetScriptWorkspaceServerDir(), self.GetScriptWorkspaceSavesDir() ]

    def GetDefaultServerSettingsPath(self):
        return Path(config.GetScriptWorkspaceDir()) / 'server-settings.json'

    def GetDefaultMapGenSettingsPath(self):
        return Path(config.GetScriptWorkspaceDir()) / 'map-gen-settings.json'

    def GetDefaultMapSettingsPath(self):
        return Path(config.GetScriptWorkspaceDir()) / 'map-settings.json'

    def GetServerDataModsDir(self):
        return Path(self.data.CurrentServerData['ServerDataDir']) / "Mods"

    def GetFactorioExecutablePath(self):
        return Path(self.GetScriptWorkspaceServerDir() / 'factorio' / 'bin' / 'x64' / 'factorio')

    def GetFactorioSavesDir(self):
        return Path(self.GetScriptWorkspaceServerDir() / 'factorio' / 'saves')

    def GetCurrentSaveFilePath(self):
        return Path(self.GetScriptWorkspaceSavesDir() / self.GetData()['SaveName'] / (self.GetData()['SaveName'] + '.zip'))

def InitiateWorkspaceIfNotReady():
    for i in config.GetScriptWorkspaceRequiredDirs():
        if not os.path.exists(i):
            InitiateWorkspace()
            break


def InitiateWorkspace():
    for i in config.GetScriptWorkspaceRequiredDirs():
        if os.path.exists(i) == False or os.path.isdir(i) == False:
            os.makedirs(i, exist_ok=True)


def DownloadServerData():
    ServerVersion = config.GetData()['Version']

    DownloadURL = f"https://www.factorio.com/get-download/{ServerVersion}/headless/linux64"
    response = requests.get(DownloadURL, stream=True)

    PackagePath = str(config.GetScriptWorkspaceTempDir() / "FactorioServer.tar.xz")

    open(PackagePath, 'wb').write(response.content)

    return PackagePath

def ExtractServerData(ServerDataPackagePath):
    Tar = tarfile.open(ServerDataPackagePath)
    Tar.extractall(str(config.GetScriptWorkspaceServerDir()))


def TryCreateDefaultServerFiles():
    if not os.path.exists(config.GetDefaultServerSettingsPath()):
        shutil.copy(f"{str(config.GetScriptWorkspaceServerDir() / 'factorio' / 'data' / 'server-settings.example.json') }", f"{str(config.GetDefaultServerSettingsPath())}")

    if not os.path.exists(config.GetDefaultMapGenSettingsPath()):
        shutil.copy(f"{str(config.GetScriptWorkspaceServerDir() / 'factorio' / 'data' / 'map-gen-settings.example.json') }", f"{str(config.GetDefaultMapGenSettingsPath())}")

    if not os.path.exists(config.GetDefaultMapSettingsPath()):
        shutil.copy(f"{str(config.GetScriptWorkspaceServerDir() / 'factorio' / 'data' / 'map-settings.example.json') }", f"{str(config.GetDefaultMapSettingsPath())}")

def CreateSaveData():

    ExecutablePath = config.GetFactorioExecutablePath()
    SaveName = config.GetData()['SaveName']
    Command = f"{str(ExecutablePath)} --create { config.GetCurrentSaveFilePath() } --map-gen-settings {str(config.GetDefaultMapGenSettingsPath())} --map-settings {str(config.GetDefaultMapSettingsPath())} "

    try:
        p = subprocess.Popen(Command.split()).wait()
    except subprocess.CalledProcessError as e:
        raise RuntimeError("command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))

    print("Factorio Server ended...")
    return p

def StartServer():
    print("Factorio Server started...")

    ExecutablePath = config.GetFactorioExecutablePath()
    Command = f"{str(ExecutablePath)} "

    # Todo : Load save files apropriate to the server.
    if not os.path.exists(config.GetFactorioSavesDir()):
        Command += f"--start-server {config.GetCurrentSaveFilePath()} "
    else:
        Command += f"--start-server-load-latest "

    Command += f"--server-settings {str(config.GetDefaultServerSettingsPath())}"

    try:
        p = subprocess.Popen(Command.split()).wait()
    except subprocess.CalledProcessError as e:
        raise RuntimeError("command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))

    print("Factorio Server ended...")
    return p


def CleanUp():
    shutil.rmtree(str(config.GetScriptWorkspaceTempDir()))


def Purge():
    shutil.rmtree(str(config.GetScriptWorkspaceDir()),  ignore_errors=True)

if __name__ == '__main__':
    config = Config()

    if len(sys.argv) == 1:
        print("No commands provided.")
    else:
        arg1 = sys.argv[1]

        if arg1 == "install":
            InitiateWorkspaceIfNotReady()
            PackagePath = DownloadServerData()
            ExtractServerData(PackagePath)
            CleanUp()
        elif arg1 == "init.data":
            TryCreateDefaultServerFiles()
        elif arg1 == "init.save":
            CreateSaveData()
        elif arg1 == "start":
            StartServer()
        elif arg1 == "purge":
            Purge()
        elif arg1 == "cleanup":
            CleanUp()
