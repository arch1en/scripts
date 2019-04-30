import os
import sys
import shutil

class Config:
    ProjectDir = os.path.dirname(os.path.realpath(__file__))
    EngineDir = "C:/_Engines/UE_4.20"

c = Config

def main():
    if sys.argv[1] == "clean":
        CleanUpProject()
    else:
        print("No such command \"" + sys.argv[1] + "\"")
	
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

    print("Clean Up Ended.")

def RemoveDir(path):
    shutil.rmtree(path, ignore_errors=False, onerror=RmTreeHandleError)

def RemoveFile(path):
    os.remove(path)

def RmTreeHandleError(func, path, exc_info):
    print("Cannot remove files from path " + path)


if __name__ == '__main__':
    main()
