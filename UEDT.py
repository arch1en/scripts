"""
    Unauthorized copying of this file, via any medium is strictly prohibited.
    Proprietary and confidential.
    Copyright © Artur "Arch1eN" Ostrowski <aostrowski.fm@gmail.com>, November 2020.
    All Rights Reserved.
"""

import os
import subprocess
import shutil
import argparse
import logging

from pathlib import Path


class Config:
    ProjectDir = os.path.dirname(os.path.realpath(__file__))
    ProjectPath = str(ProjectDir + os.sep + ProjectDir.split(os.sep)[-1] + ".uproject")
    EngineDir = "E:/_Engines/UE_4.22_Stock"
    BuildStagingDir = "E:/_Builds/BBDevTest"
    Configuration = "Shipping" # Development | Shipping | Test


c = Config


def GetProjectFileName():
    return c.ProjectPath.split(os.sep)[-1]


def GetProjectName():
    return GetProjectFileName().split(".")[0]


class Cleaner:
    def CleanUpProject(self):
        ProjectDir = c.ProjectDir
        PathsToRemove = [
            ProjectDir + "/Binaries",
            ProjectDir + "/Intermediate",
            ProjectDir + "/Saved/Autosaves",
            ProjectDir + "/Saved/Backup",
            ProjectDir + "/Saved/Diff"
        ]

        for path in PathsToRemove:
            if os.path.exists(path):
                RemoveDir(path)

        for file in os.listdir(ProjectDir):
            if file.endswith(".sln"):
                FilePath = os.path.join(ProjectDir, file)
                if os.path.exists(FilePath):
                    RemoveFile(FilePath)

        print("Clean Up Ended.")


def RemoveDir(path):
    shutil.rmtree(path, ignore_errors=False, onerror=RmTreeHandleError)


def RemoveFile(path):
    os.remove(path)


def RmTreeHandleError(func, path, exc_info):
    print("Cannot remove files from path " + path)


class Builder:
    def BuildProject(self):
        Args = [
            f"{str(Path(c.EngineDir) / 'Engine/Build/BatchFiles/RunUAT.bat')}",
            "BuildCookRun",
            f"-ue4exe={str(Path(c.EngineDir) / 'Engine/Binaries/Win64/UE4Editor-Cmd.exe')}",
            f"-project={str(Path(c.ProjectPath))}",
            f"-clientconfig={c.Configuration}",
            f"-serverconfig={c.Configuration}",
            "-targetplatform=Win64",
            "-platform=Win64",
            "-noP4",
            "-build",
            "-cook", # cook -
            "-stage",
            f"-stagingdirectory={str(Path(c.BuildStagingDir) / c.Configuration)}",
            # Due to problems with blueprint nativization, it is by default disabled in building process.
            "-ini:Game[/Script/UnrealEd.ProjectPackagingSettings]:BlueprintNativizationMethod=Disabled",
            "-nocompileeditor",
            "-installed",
            "-unversionedcookedcontent",
            "-compressed",
            # -map=FirstMap+SecondMap",
            #"-clean",
            #"-iterativecooking"
        ]

        try:
            BuildProcess = subprocess.Popen(Args).wait()
        except:
            pass


class Compiler:
    def RetrieveMSBuildPath(self, RegistryPath):
        if os.sys.platform == "win32":
            import winreg

            RegType, RegPath = RegistryPath.split(":")

            RegistryType = {
                'HKCR': winreg.HKEY_CLASSES_ROOT,
                'HKCU': winreg.HKEY_CURRENT_USER,
                'HKLM': winreg.HKEY_LOCAL_MACHINE,
                'HKU': winreg.HKEY_USERS,
                'HKCC': winreg.HKEY_CURRENT_CONFIG
            }[RegType]

            AccessRegistry = winreg.ConnectRegistry(None, RegistryType)

            if AccessRegistry is None:
                logging.getLogger().info(f"Cannot connect to {RegistryType}")
                return ""

            RegPath = RegPath.replace("/","\\")
            RegPath, RegKeyName = RegPath.rsplit("\\", 1)
            RegKey = winreg.OpenKey(AccessRegistry, RegPath)

            if RegKey is None:
                logging.getLogger().info(f"Cannot open {RegPath} registry.")
                return ""

            Values = winreg.QueryValueEx(RegKey, RegKeyName)
            if len(Values) < 1:
                logging.getLogger().info(
                    f"Cannot retrieve data from {RegKeyName} registry in {RegistryType}\\{RegPath}.")
                return ""

            if Values[0].find(";"):
                Values = Values[0].split(';')

            Values = [v for v in Values if len(v) > 0]

            return Values
        else:
            raise NotImplemented

    def CompileProject(self):
        MSBuildPath = self.RetrieveMSBuildPath("HKLM:SOFTWARE/Microsoft/MSBuild/ToolsVersions/4.0/MSBuildToolsPath")
        if len(MSBuildPath) > 0:
            ProjectName = GetProjectName()


            Commands = [
                f"{str(Path(c.EngineDir) / 'Engine/Build/BatchFiles/Build.bat')}",
                ProjectName+'Editor',
                'Win64',
                'Development',
                c.ProjectPath,
                '-WaitMutex'
            ]

            try:
                BuildProcess = subprocess.Popen(Commands).wait()
            except:
                pass
        else:
            logging.error("MSBuild not installed. Use 'python UEDT.py compile -help' to get information about MSBuild tool installation.")


class Cooker:
    def CookProject(self):
        Args = [
            f"{str(Path(c.EngineDir) / 'Engine/Binaries/Win64/UE4Editor.exe')}",
            f"{str(Path(c.ProjectPath))}",
            "-run=cook",
            "-targetplatform=Win64",
            "-cookonthefly",
            "-iterate",
            # Due to problems with blueprint nativization, it is by default disabled in building process.
            #"-ini:Game[/Script/UnrealEd.ProjectPackagingSettings]:BlueprintNativizationMethod=Disabled",
            #"-map=FirstMap+SecondMap",
            #"-clean",
        ]

        try:
            BuildProcess = subprocess.Popen(Args).wait()
        except:
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Unreal Engine Development Tool")

    p = c.ProjectDir

    def Clean():
        obj = Cleaner()
        obj.CleanUpProject()

    def Build():
        obj = Builder()
        obj.BuildProject()

    def Compile():
        obj = Compiler()
        obj.CompileProject()

    def Cook():
        obj = Cooker()
        obj.CookProject()

    commands = [
        ["build", Build, "Build project."],
        ["clean", Clean, "Clean project by removing Binaries folder, Intermediate folder and some Saved folders."],
        ["compile", Compile, "Compile project using MSBuild tool."],
        ["cook", Cook, "Cook content (for shipping build testing)."]
    ]

    CommandHelp = '\n'.join([command[2] for command in commands])

    parser.add_argument('command', type=str, help=CommandHelp)

    args = parser.parse_args()

    CommandToExecute = None

    for command in commands:
        if args.command == command[0]:
            CommandToExecute = command[1]
            break

    if CommandToExecute is not None:
        CommandToExecute()
    else:
        logging.getLogger().info(f'No such command "{args.command}"')