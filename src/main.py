"""Valheim server utility tool.

Usage:
  main.py server <server-name> <command>
  main.py -h

Options:
    -h Show help.
"""

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
import docopt


class Config:

    def __init__(self):
        self.__data = []
        ConfigPath = str(Path(__file__).absolute().parent / "Config.yaml")
        with open(ConfigPath, "r") as stream:
            try:
                self.__data = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def CheckIntegrity(self):
        OK = True
        Message = []

        if self.GetData()['Version'] is None:
            Message.append("'Version' field is empty. ")
            OK = False

        if self.GetData()['ScriptWorkspaceDir'] is None:
            Message.append("'ScriptWorkspaceDir' field is empty. ")
            OK = False

        if self.GetData()['SaveName'] is None:
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

        if self.GetData()['Credentials']:
            if self.GetData()['Credentials']['User'] is None:
                Message.append("'User' field is empty. ")
                OK = False
            elif self.GetData()['Credentials']['Token'] is None:
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

    def GetCommonData(self):
        return self.GetData()['Common']

    def GetData(self):
        return self.__data

    def GetScriptWorkspaceDir(self):
        return Path(self.GetData()['ScriptWorkspaceDir'])

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

    # Server Dirs
    def GetServerDataModsDir(self):
        raise NotImplemented

    def GetServerDataModsDirEnsured(self):
        if not os.path.exists(self.GetServerDataModsDir()):
            os.mkdir(self.GetServerDataModsDir())
        return self.GetServerDataModsDir()

    def GetSavesDir(self):
        #return Path(self.GetScriptWorkspaceServerDir() / 'factorio' / 'saves')
        raise NotImplemented

    def GetavesDirEnsured(self):
        if not os.path.exists(self.GetSavesDir()):
            os.mkdir(self.GetSavesDir())
        return self.GetSavesDir()
    # ~Server Dirs

    def GetServerExecutablePath(self):
        return Path(self.GetScriptWorkspaceServerDir() / 'factorio.sh')

    def GetCurrentSaveFilePath(self):
        raise NotImplemented


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


def UpdateServerData():
    # 1. Turn off the server.
    # 2. Backup required server files.
    # 3. Update server.
    # 4. Check if both files are similar.
    # 5. If they are almost identical, override.
    Log(0, "UpdateServer started...")
    Command = f"{str(Path(config.data['Common']['SteamCmdPath']))} steam +login anonymous +force_install_dir {str(Path(config.CurrentServerData['ServerDataDir']))} +app_update {str(Path(config.data['ApplicationSteamID']))} +quit"

    try:
        p = subprocess.Popen(Command.split())
    except subprocess.CalledProcessError as e:
        raise RuntimeError("command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))
    Log(0, "UpdateServer ended...")
    return p


def StartServer():
    print(f"{config.data['ApplicationName']} server started...")

    ExecutablePath = config.GetExecutablePath()
    Command = f"{str(ExecutablePath)} "

    try:
        p = subprocess.Popen(Command.split()).wait()
    except subprocess.CalledProcessError as e:
        raise RuntimeError("command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))

    print(f"{config.data['ApplicationName']} Server ended...")
    return p


def CleanUp():
    shutil.rmtree(str(config.GetScriptWorkspaceTempDir()))


def Purge():
    shutil.rmtree(str(config.GetScriptWorkspaceDir()), ignore_errors=True)


def main():
    config = Config()
    commands = sys.args
    # Mods Disabled.
    #mods = ModHandler()

    if config.CheckIntegrity() is not True:
        sys.exit(1)

    try:
        args = docopt.docopt(__doc__, commands, help=False)

        if args.get('-h'):
            print(__doc__)
            return 0

        if args.get('server'):

            serverName = args.get('<server-name>')
            if serverName:

                serverData = config.GetServerData(serverName)

                if serverData:
                    command = args.get('<command>')
                    if command == 'install':
                        InitiateWorkspaceIfNotReady()
                        ExtractServerData(DownloadServerData())
                        CleanUp()
                    if command == 'start':
                        StartServer()
                    if command == 'purge':
                        Purge()
                else:
                    print(f"No configuration found for server {serverName}")

    except docopt.DocoptExit as e:
        print(f"Command(s) unrecognized ({' '.join([x for x in commands])}). Use -h parameter to show usage docstring.")

    return 0

if __name__ == '__main__':
    main()


