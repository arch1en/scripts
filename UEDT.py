"""
    Unauthorized copying of this file, via any medium is strictly prohibited.
    Proprietary and confidential.
    Copyright © Artur "Arch1eN" Ostrowski <aostrowski.fm@gmail.com>, November 2020.
    All Rights Reserved.
    
    UEDT should be in the project directory, next to the 'uproject' file. 
"""

"""
    Config
"""

class Config:
    # Compilation
    CompilationConfiguration = "Development"
    # Build
    BuildStagingDir = "E:/_Builds" # / ProjectName / ConfigurationName
    BuildConfiguration = "Development" # Development | Test | Shipping | Release 
    
    # Whitelist maps that will be added to the build.
    # If, array is empty, map parameter during cooking process will be ignored.
    Maps =  [

    ]
    
"""
    Code
"""

import os
import sys
import glob
import shutil
import logging
import argparse
import subprocess

from abc import ABC

from pathlib import Path

c = Config

class Command(ABC):
   
    def __init__(self, *args, **kwargs) -> None:
        self._Execute(args[0])
    
    def _Execute(self, args):
        pass
        
# Returns full path to the project's 'uproject' file.
# Eg. C:/Project/Project.uproject
def GetUProjectPath():
    for root, dirs, files in os.walk(GetProjectDir()):
        for file in files:
            if file.endswith(".uproject"):
                return Path(os.path.join(root, file))

def GetProjectDir():
    return os.path.dirname(os.path.realpath(__file__))

def GetProjectFileName():
    return str(GetUProjectPath()).split(os.sep)[-1]

def GetProjectName():
    return GetProjectFileName().split(".")[0]

def GetUATPath():
    return Path(GetAssociatedEngineDir()) / 'Engine/Build/BatchFiles/RunUAT.bat'

def GetUProjectFileData():
    import json
    
    with open(GetUProjectPath(), 'r') as f:
        return json.loads(f.read())
    
# [TestRequired]
def GetAssociatedEngineDir():
    data = GetUProjectFileData()
    path = []
    
    # Distinguish source and launcher engine association.
    if data['EngineAssociation'].startswith('{'):
        path = GetRegistryData(f"HKCU:Software/Epic Games/Unreal Engine/Builds/{data['EngineAssociation']}")
    else:
        path = GetRegistryData(f"HKLM:SOFTWARE/EpicGames/Unreal Engine/{data['EngineAssociation']}/InstalledDirectory")
        
    #path = Path(GetRegistryData(f"HKLM:SOFTWARE/EpicGames/Unreal Engine/{data['EngineAssociation']}/InstalledDirectory")[0])
    
    return Path(path[0])

def GetRegistryData(RegistryPath):
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

        try:
            AccessRegistry = winreg.ConnectRegistry(None, RegistryType)
        except OSError as e:
            logging.getLogger().info(f"Cannot connect to {RegistryType} : {e}")
            return None

        RegPath = RegPath.replace("/","\\")
        RegPath, RegKeyName = RegPath.rsplit("\\", 1)
        
        try: 
            RegKey = winreg.OpenKey(AccessRegistry, RegPath)
        except OSError as e:
            logging.getLogger().info(f"Cannot open {RegPath} registry.")
            return None

        Values = winreg.QueryValueEx(RegKey, RegKeyName)
        if len(Values) < 1:
            logging.getLogger().info(
                f"Cannot retrieve data from {RegKeyName} registry in {RegistryType}\\{RegPath}.")
            return None

        if Values[0].find(";"):
            Values = Values[0].split(';')

        Result = [v for v in Values if len(v) > 0]

        return Result
    else:
        raise NotImplemented

def RemoveDir(path):
    shutil.rmtree(path, ignore_errors=False, onerror=RmTreeHandleError)


def RemoveFile(path):
    os.remove(path)


def RmTreeHandleError(func, path, exc_info):
    print("Cannot remove files from path " + str(path))


class Clean(Command):
    def _Execute(self, args):
        ProjectDir = GetProjectDir()
        
        DirsToRemove = [
            "Binaries",
            "Intermediate",
            "Saved/Autosaves",
            "Saved/Backup",
            "Saved/Diff"
        ]
        
        PathsToRemove = [ProjectDir + "/" + x for x in DirsToRemove]

        for path in PathsToRemove:
            path = Path(path)
            if os.path.exists(path):
                RemoveDir(path)

        for mainPath in glob.glob(ProjectDir + "/Plugins/*"):
            for dirToRemove in DirsToRemove:
                finalPath = Path(mainPath) / dirToRemove
                if os.path.exists(finalPath):
                    RemoveDir(finalPath)
        

        for file in os.listdir(ProjectDir):
            if file.endswith(".sln"):
                FilePath = os.path.join(ProjectDir, file)
                if os.path.exists(FilePath):
                    RemoveFile(FilePath)

        print("Clean Up Ended.")

class Build(Command):
    def _Execute(self, args):
        
        BuildConfiguration = ""

        if args.get("configuration") is not None:
            BuildConfiguration = args.get("configuration")
        elif args.get("c") is not None:
            BuildConfiguration = args.get("c")
        else:
            BuildConfiguration = c.BuildConfiguration
        
        ActualBuildConfiguration = BuildConfiguration

        if ActualBuildConfiguration == "Release":
            ActualBuildConfiguration = "Shipping"

        logging.getLogger().info("--------------------------------")
        logging.getLogger().info(f"Build Configuration : {BuildConfiguration}")
        logging.getLogger().info("--------------------------------")

        Args = [
            f"{str(GetUATPath())}",
            "BuildCookRun",
            f"-ue4exe={str(Path(GetAssociatedEngineDir()) / 'Engine/Binaries/Win64/UE4Editor-Cmd.exe')}",
            f"-project={str(Path(GetUProjectPath()))}",
            f"-clientconfig={ActualBuildConfiguration}",
            f"-serverconfig={ActualBuildConfiguration}",
            "-targetplatform=Win64",
            "-platform=Win64",
            "-noP4",
            "-build",
            "-cook", # cook -
            "-stage",
            f"-stagingdirectory={str(Path(c.BuildStagingDir) / GetProjectName() / BuildConfiguration)}",
            # Due to problems with blueprint nativization, it is by default disabled in building process.
            "-ini:Game[/Script/UnrealEd.ProjectPackagingSettings]:BlueprintNativizationMethod=Disabled",
            #"-nocompileeditor",
            "-installed",
            "-unversionedcookedcontent",
            "-compressed",
            f"-map={'+'.join(c.Maps)}",
            ("-distribution" if BuildConfiguration == "Release" else ""), # 
            ("-encryptinifiles" if BuildConfiguration == "Release" else ""), # 
            ("-skipeditorcontent" if BuildConfiguration == "Release" else ""), # 
            ("-skipcookingeditorcontent" if BuildConfiguration == "Release" else ""), # 
            ("-pak" if BuildConfiguration == "Release" else ""), # 
            "-fullrebuild"
            #"-clean",
            #"-iterativecooking"
        ]

        try:
            BuildProcess = subprocess.Popen(Args).wait()
        except:
            pass


class Compile(Command):
    def _Execute(self, args):
        MSBuildPath = GetRegistryData("HKLM:SOFTWARE/Microsoft/MSBuild/ToolsVersions/4.0/MSBuildToolsPath")
        if len(MSBuildPath) > 0:
            ProjectName = GetProjectName()

            BatchFilePath = Path(GetAssociatedEngineDir()) / 'Engine/Build/BatchFiles/Build.bat'
            if not os.path.exists(BatchFilePath):
                logging.error(f"File does not exist. {str(BatchFilePath)}")
                return

            Commands = [
                f"{str(BatchFilePath)}",
                ProjectName+'Editor',
                'Win64',
                c.CompilationConfiguration,
                GetUProjectPath(),
                '-WaitMutex'
            ]

            try:
                BuildProcess = subprocess.Popen(Commands).wait()
            except:
                pass
        else:
            logging.error("MSBuild not installed. Use 'python UEDT.py compile -help' to get information about MSBuild tool installation.")


class CookProject(Command):
    def _Execute(self, args):
        Args = [
            f"{str(Path(GetAssociatedEngineDir()) / 'Engine/Binaries/Win64/UE4Editor.exe')}",
            f"{str(Path(GetUProjectPath()))}",
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

class DataValidator(Command):
    def _Execute(self, args):
        args = f"{str(Path(GetAssociatedEngineDir()) / 'Engine/Binaries/Win64/UE4Editor-Cmd.exe')} {str(Path(GetUProjectPath()))} -run=DataValidation"

        try:
            process = subprocess.Popen(args.split()).wait()
        except:
            pass


class GauntletTest(Command):      
    def _Execute(self, args):
        
        if args.get("target") is None:
            print("Cannot perform GauntletTest. Target not provided.")
            return
        
        args = f"{GetUATPath()} BuildCookRun -project={GetUProjectPath()} -platform=Win64 -configuration=Development -build -cook -pak -stage"
        print(args)
        
        try:
            process = subprocess.Popen(args.split()).wait()
        except:
            pass
        
        print("\n################\n# START GAUNTLET TEST\n################")
        
        args = f"{GetUATPath()} RunUnreal -project={GetUProjectPath()} -platform=Win64 -configuration=Development -build=local -test={args.target}"

        try:
            process = subprocess.Popen(args.split()).wait()
        except:
            pass

class Test(Command):
    def _Execute(self, args):
        GetAssociatedEngineDir()

class ShowChangelist(Command):
    def _Execute(self, args):
        os.system('p4 changes -m 1 -s submitted //GiantsUprising/Master/...')

"""
    Commands
"""

commands = [
    ["build", Build, "Build project.",   
        [
            ["--configuration", "Override default configuration"],
            ["--c", "Override default configuration"],
        ]
    ],
    ["clean", Clean, "Clean project by removing Binaries folder, Intermediate folder and some Saved folders.", []],
    ["compile", Compile, "Compile project using MSBuild tool.", 
        [
            ["--configuration", "Override default configuration"],
            ["--c", "Override default configuration"],
        ]
    ],
    ["cook", CookProject, "Cook content (for shipping build testing).", []],
    ["validate", DataValidator, 'Invoke DataValidation command, data validation plugin enabled required for this to run.', []],
    ["showChangelist", ShowChangelist, 'Returns changelist number of a registered repository.', []],
    ["gauntlet", GauntletTest, 'Run Gauntlet automation test. Requires \'target\' argument.',
        [
            ["--target", "Provide a name of a test to execute."]
        ]
    ],
    ["test", Test, 'Sandbox test command. Does what you tell it.', []],
]

"""
    Entry
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Unreal Engine Development Tool")

    logging.basicConfig(filename='UEDT.log', encoding='utf-8', level=logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    CommandHelp = '\n'.join([f"{command[0]} - {command[2]}" for command in commands])

    subparsers = parser.add_subparsers(dest='command')

    for command in commands:
        command_paraser = subparsers.add_parser(command[0], help=command[2])
        subcommands = command[3]
        if len(subcommands) > 0:
            for subcommand in subcommands:
                command_paraser.add_argument(subcommand[0], help=subcommand[1])
    
    args = parser.parse_args()

    CommandToExecute = None

    for command in commands:
        if args.command == command[0]:
            CommandToExecute = command[1]
            break

    if CommandToExecute is not None:
        CommandToExecute(vars(args))
    else:
        logging.getLogger().info(f'No such command "{args.command}"')