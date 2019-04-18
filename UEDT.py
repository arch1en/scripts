import os
import sys
import shutil

class Config:
    ProjectDir = "C:/_Workspace/BeBee"
    EngineDir = "C:/_Engines/UE_4.20"

c = Config

def main():
    if sys.argv[1] == "cleanup":
        CleanUpProject()

def CleanUpProject():
    ProjectDir = c.ProjectDir
    PathsToRemove = [
        ProjectDir + "/Binaries",
        ProjectDir + "/Intermediate",
        ProjectDir + "/Saved/Autosaves",
        ProjectDir + "/Saved/Backup",
        ProjectDir + "/Saved/Collections",
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

    

def RemoveDir(path):
    shutil.rmtree(path, ignore_errors=False, onerror=RmTreeHandleError)

def RemoveFile(path):
    os.remove(path)

def RmTreeHandleError(func, path, exc_info):
    print("Cannot remove files from path " + path)


if __name__ == '__main__':
    main()
