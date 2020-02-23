# Copyright Artur "Arch1eN" Ostrowski.
# Use 'help' command for more information.

from pathlib import Path
from types import FunctionType

import os
import yaml
import requests
import shutil
import tarfile
import subprocess
import sys
import re
import datetime


class Config:

    def __init__(self):
        self.data = []
        ConfigPath = str(Path(__file__).absolute().parent / "Config.yaml")
        with open(ConfigPath, "r") as stream:
            try:
                self.data = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def CheckIntegrity(self):
        OK = True
        Message = []

        if self.data['Version'] is None:
            Message.append("'Version' field is empty. ")
            OK = False

        if self.data['ScriptWorkspaceDir'] is None:
            Message.append("'ScriptWorkspaceDir' field is empty. ")
            OK = False

        if self.data['SaveName'] is None:
            Message.append("'SaveName' field is empty. ")
            OK = False

        if not OK:
            print(f"Config file integrity check failed.")
            for m in Message:
                print(f"- {''.join(m)}")

        return OK

    def CheckCredentialsIntegrity(self):
        OK = True
        Message = []

        if self.data['Credentials']:
            if self.data['Credentials']['User'] is None:
                Message.append("'User' field is empty. ")
                OK = False
            elif self.data['Credentials']['Token'] is None:
                Message.append("'Token' field is empty. ")
                OK = False
        else:
            Message.append("No credentials data.")
            OK = False

        if not OK:
            print(f"Config file credentials integrity check failed.")
            for m in Message:
                print(f"- {''.join(m)}")

        return OK

    def GetServerVersion(self):
        ConfigVersion = self.GetData()['Version']
        ConfigVersion = ConfigVersion.split('.')

        Version = {}
        Version['Major'] = ConfigVersion[0]
        Version['Minor'] = ConfigVersion[1]
        Version['Patch'] = ConfigVersion[2]

        return Version

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
        return [self.GetScriptWorkspaceTempDir(), self.GetScriptWorkspaceServerDir(), self.GetScriptWorkspaceSavesDir()]

    def GetDefaultServerSettingsPath(self):
        return Path(config.GetScriptWorkspaceDir()) / 'server-settings.json'

    def GetDefaultMapGenSettingsPath(self):
        return Path(config.GetScriptWorkspaceDir()) / 'map-gen-settings.json'

    def GetDefaultMapSettingsPath(self):
        return Path(config.GetScriptWorkspaceDir()) / 'map-settings.json'

    # Server Dirs
    def GetServerDataModsDir(self):
        return Path(self.GetScriptWorkspaceServerDir()) / 'factorio' / 'mods'

    def GetServerDataModsDirEnsured(self):
        if not os.path.exists(self.GetServerDataModsDir()):
            os.mkdir(self.GetServerDataModsDir())
        return self.GetServerDataModsDir()

    def GetFactorioSavesDir(self):
        return Path(self.GetScriptWorkspaceServerDir() / 'factorio' / 'saves')

    def GetFactorioSavesDirEnsured(self):
        if not os.path.exists(self.GetFactorioSavesDir()):
            os.mkdir(self.GetFactorioSavesDir())
        return self.GetFactorioSavesDir()
    # ~Server Dirs

    def GetFactorioExecutablePath(self):
        return Path(self.GetScriptWorkspaceServerDir() / 'factorio' / 'bin' / 'x64' / 'factorio')

    def GetCurrentSaveFilePath(self):
        return Path(
            self.GetScriptWorkspaceSavesDir() / self.GetData()['SaveName'] / (self.GetData()['SaveName'] + '.zip'))

    def GenerateConfigFile(self):
        ConfigFileBody = """Version: 0.17.79
ScriptWorkspaceDir: # Mandatory. This folder will be used by the script to manage files.
SaveName: # A name of a save that will be used by the server.
Credentials: # Credentials are required for the mods to be downloaded.
  User: # Username of your account. If you have steam version, you can find it in '%APPDATA%/Factorio/player-data.json' (a 'service-name' parameter)
  Token: # Token associated with your account. If you have steam version, you can find it in '%APPDATA%/Factorio/player-data.json' (a 'service-token' parameter)
Mods: This list of mods will be downloaded to the server.
  - Name: 'bobvehicleequipment' # Mod name. It can be identified by the last part of the mod url from mods.factorio.com (https://mods.factorio.com/mod/bobvehicleequipment).
"""

class CommandData:
    Command: str
    FunctionPtr: FunctionType
    Description: str

    def __init__(self, Command, FunctionPtr, Description):
        self.Command = Command
        self.FunctionPtr = FunctionPtr
        self.Description = Description


class CommandHandler:
    CommandDatas = []

    def RegisterCommand(self, Command: CommandData):
        for c in self.CommandDatas:
            if c.Command == Command.Command:
                print("Command already registered. Breaking...")
                break

        self.CommandDatas.append(Command)
        self.CommandDatas.sort(key=lambda x: x.Command)

    def InvokeHelp(self):
        for c in self.CommandDatas:
            print(f"{c.Command} - {c.Description}")

    def EvaluateCommands(self, Args):
        if len(Args) == 1:
            print("No commands provided.")
            return

        if Args[1] == 'help':
            self.InvokeHelp()
            return

        for c in self.CommandDatas:
            if c.Command == Args[1]:
                c.FunctionPtr()
                break


class ModHandler:
    Username: str
    Token: str

    def GetFactorioModsUrl(self):
        return 'https://mods.factorio.com/api/mods'

    def RetrieveModsData(self):
        OK = config.CheckCredentialsIntegrity()
        if not OK:
            return
        else:
            self.Username = config.GetData()['Credentials']['User']
            self.Token = config.GetData()['Credentials']['Token']

        ModsConfigData = config.GetData()['Mods']

        NewestReleaseIndices = []

        ModsRetrievedData = []

        for Mod in ModsConfigData:
            r = requests.get(f"{self.GetFactorioModsUrl()}/{Mod['Name']}")
            if r.status_code == 200:
                RetrievedData = r.json()
                ModsRetrievedData.append(RetrievedData)

                Newest = self.GetNewestModVersionDataIndexBasedOnServerVersion(RetrievedData)
                NewestReleaseIndices.append(Newest)

        self.DownloadMods(ModsRetrievedData, NewestReleaseIndices)

    def DownloadMods(self, ModsData, NewestReleaseIndices):

        for i in range(len(ModsData)):
            ModData = ModsData[i]
            DownloadURL = f"{self.GetFactorioModsUrl()}/{ModData['name']}?username={self.Username}&token={self.Token}"

            response = requests.get(DownloadURL, stream=True)
            PackagePath = str(config.GetServerDataModsDirEnsured() / ModData['releases'][NewestReleaseIndices[i]]['file_name'])
            open(PackagePath, 'wb').write(response.content)

    def PurgeMods(self):
        shutil.rmtree(config.GetServerDataModsDir(), ignore_errors=True)


    def GetNewestModVersionDataIndexBasedOnServerVersion(self, JsonData):
        ServerVersion = config.GetServerVersion()
        RegexPattern = f"^{ServerVersion['Major']}.{ServerVersion['Minor']}"

        Newest = 0

        for i in range(len(JsonData['releases'])):
            Release = JsonData['releases'][i]
            Found = re.search(RegexPattern, Release['info_json']['factorio_version'])
            if Found is not None and Found.group(0) != '':
                if self.ParseReleaseDate(JsonData['releases'][Newest]) < self.ParseReleaseDate(Release):
                    Newest = i

        return Newest


    def ParseReleaseDate(self, ReleaseData):
        DateTime = ReleaseData['released_at'].split('T')

        YearMonthDay = DateTime[0].split('-')
        HourMinuteSecond = DateTime[1].split(':')

        return datetime.datetime(int(YearMonthDay[0]), int(YearMonthDay[1]), int(YearMonthDay[2]), int(HourMinuteSecond[0]), int(HourMinuteSecond[1]), int(HourMinuteSecond[2].split('.')[0]))


def InitiateWorkspaceIfNotReady():
    for i in config.GetScriptWorkspaceRequiredDirs():
        if not os.path.exists(i):
            InitiateWorkspace()
            break


def InitiateWorkspace():
    for i in config.GetScriptWorkspaceRequiredDirs():
        i = str(i)
        if os.path.exists(i) is False or os.path.isdir(i) is False:
            os.makedirs(i, exist_ok=True)
        print("Workspace initiated.")


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
        shutil.copy(
            f"{str(config.GetScriptWorkspaceServerDir() / 'factorio' / 'data' / 'server-settings.example.json')}",
            f"{str(config.GetDefaultServerSettingsPath())}")

    if not os.path.exists(config.GetDefaultMapGenSettingsPath()):
        shutil.copy(
            f"{str(config.GetScriptWorkspaceServerDir() / 'factorio' / 'data' / 'map-gen-settings.example.json')}",
            f"{str(config.GetDefaultMapGenSettingsPath())}")

    if not os.path.exists(config.GetDefaultMapSettingsPath()):
        shutil.copy(f"{str(config.GetScriptWorkspaceServerDir() / 'factorio' / 'data' / 'map-settings.example.json')}",
                    f"{str(config.GetDefaultMapSettingsPath())}")


def CreateSaveData():
    ExecutablePath = config.GetFactorioExecutablePath()
    SaveName = config.GetData()['SaveName']
    Command = f"{str(ExecutablePath)} --create {config.GetCurrentSaveFilePath()} --map-gen-settings {str(config.GetDefaultMapGenSettingsPath())} --map-settings {str(config.GetDefaultMapSettingsPath())} "

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
    shutil.rmtree(str(config.GetScriptWorkspaceDir()), ignore_errors=True)


if __name__ == '__main__':
    config = Config()
    commands = CommandHandler()
    mods = ModHandler()

    if config.CheckIntegrity() is not True:
        sys.exit(1)


    def InstallCommand():
        InitiateWorkspaceIfNotReady()
        ExtractServerData(DownloadServerData())
        CleanUp()
        TryCreateDefaultServerFiles()
    commands.RegisterCommand(CommandData('server.install', InstallCommand,
                                         """Downloads, unpacks and puts server files into the <workspace-dir>/Server directory. Depends on \'Version\' field in configuration file.'"""))


    def InitSaveCommand():
        CreateSaveData()
    commands.RegisterCommand(CommandData('server.save.create', InitSaveCommand,
                                         """Save files initialization. Corresponding map-gen-settings.json and map-settings.json files should be configured before invoking this command."""))


    def StartServerCommand():
        StartServer()
    commands.RegisterCommand(CommandData('server.start', StartServerCommand,
                                         """Launches factorio server. Depends on \'SaveName\' config field. After launching, server can be stopped by clicking Ctrl+C combo."""))


    def DownloadMods():
        mods.RetrieveModsData()
    commands.RegisterCommand(CommandData('mods.download', DownloadMods,
                                         """Download mods that are listed in the config file."""))

    def PurgeMods():
        mods.PurgeMods()
    commands.RegisterCommand(CommandData('mods.purge', PurgeMods,
                                         """Remove all mods from server 'mods' folder."""))

    def PurgeCommand():
        Purge()
    commands.RegisterCommand(CommandData('server.purge', PurgeCommand,
                                         """Removes all data from script workspace directory. Use with caution !"""))

    commands.EvaluateCommands(sys.argv)
