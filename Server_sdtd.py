# Execute this file from the root directory of the server.
# Remember to "init" workspace at the start.

import os
import sys
import tarfile
import subprocess
import urllib.request
import urllib.error

# File replacements : dictionary { "PastebinUrl", "PathOfAFileToReplace" }
# Path of a file to replace will be : ServerDataDir + "/" + PathOfAFileToReplace
class ServerData():
	def __init__(self, Version, ServerDataDir, ServerConfigPath, AllocsFixesDownloadUrl, FileReplacements):
		self.Version = Version
		self.ServerDataDir = ServerDataDir
		self.ServerConfigPath = ServerConfigPath
		self.AllocsFixesDownloadUrl = AllocsFixesDownloadUrl
                self.FileReplacements = FileReplacements # @todo: Implement
# config

class Config:
	LogVerbosity = 0
	ServerName = "server_carnivore"
	
	ServerProcessName = "7daystodie"	
	ServerDataDir = "/home/gameservers/7d2d/zombieland"

	RcloneRemoteName = "7daystodie_remote"
	
	RemoteDir = "MEGAsync_VPS/gameservers/7d2d"
	SteamCmdPath = "/home/gameservers/_tools/steamcmd/steamcmd.sh"
	ServerConfigPath = "/home/sdtd/server_carnivore/svrcfg_semperinvicta.xml"
	ScriptWorkspaceDir = "/home/sdtd/script_workspace"
	
	ServerDataArray ={
		"Carnivore" : ServerData(
                    Version="alpha17.4", 
                    ServerDataDir="/home/sdtd/server_carnivore", 
                    ServerConfigPath="/home/sdtd/server_carnivore/serverconfig.xml", 
                    AllocsFixesDownloadUrl="http://illy.bz/fi/7dtd/server_fixes_v17_20_30.tar.gz")
	}
	
	CurrentServerData = ServerDataArray['Carnivore']
	
	def GetServerPath(self):
		return "/home/sdtd"
	
	def GetServerSaveDataDir(self):
		return GetServerPath() + "/.local/share/7DaysToDie/Saves"
	
	def GetScriptWorkspaceTempDir(self):
		return self.ScriptWorkspaceDir  + "/Temp"
	
	def GetScriptWorkspaceCacheDir(self):
		return self.ScriptWorkspaceDir + "/Cache"

	def GetScriptWorkspaceRecoveryDir(self):
		return self.ScriptWorkspaceDir + "/Recovery"

	def GetServerDataModsDir(self):
		return self.ServerDataDir + "/Mods"

	def GetAllocsFixesPackagePath(self):
		return self.GetScriptWorkspaceTempDir() + "/allocs_package.tar.gz"
		
	FilesToPreserve = [
		"serverconfig.xml"
		"Data/Config/buffs.xml"
	]
config = Config()

# functions

def main():
    arg1 = sys.argv[1]

	if arg1 == "all":
		#TerminateServer()
		Backup()
		UpdateServer()
	elif arg1 == "backup":
		Backup()
	elif arg1 == "update":
		UpdateServer()
	elif arg1 == "updatefixes":
		UpdateAllocsFixes()
	elif arg1 == "launch":
		LaunchServer()
	elif arg1 == "terminate":
		TerminateServer()
	elif arg1 == "init":
		InitializeWorkspace()
        elif arg1 == "migrate"
                PlayerName = sys.argv[2]
                MigrateFrom = sys.argv[3]
                MigrateTo = sys.argv[4]
                MigrateCharacter(PlayerName, MigrateFrom, MigrateTo)
	else:
		Log(0, "Wrong command")

def MigrateCharacter(PlayerName, ServerNameMigrateFrom, ServerNameMigrateTo):


def Backup():
	Log(0, "Backup started...")
	args = 	[
			"rclone",
			"copy",
			config.GetServerSaveDataDir(),
			config.RcloneRemoteName+":"+config.RemoteDir,
			"-v"
	]
	try:		
		p = subprocess.Popen(args).wait()
	except subprocess.CalledProcessError as e:
		raise RuntimeError("command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))
	Log(0, "Backup ended...")
	return p

def UpdateServer():
		#1. Turn off the server.
		#2. Backup required server files (serverconfig.xml, buffs.xml).
		#3. Update server.
		#4. Check if both files are similar.
		#5. If they are almost identical, override.
	Log(0, "UpdateServer started...")
	args = 	[config.SteamCmdPath,
			"steam",
			"+login",
			"anonymous",
			"+force_install_dir",
			config.CurrentServerData.ServerDataDir,
			"+app_update",
			"294420",
			"-beta",
			config.CurrentServerData.Version,
			"validate",
			"+quit"]

	try:
		p = subprocess.Popen(args)
	except subprocess.CalledProcessError as e:
		raise RuntimeError("command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))
	Log(0, "UpdateServer ended...")
	return p

def LaunchServer():
	Log(0, "LaunchServer started...")
	args = 	[config.CurrentServerData.ServerDataDir + "/startserver.sh",
			"-configfile=" + config.CurrentServerData.ServerConfigPath
			]

	try:
		p = subprocess.Popen(args).wait()
	except subprocess.CalledProcessError as e:
		raise RuntimeError("command '{}' returned with error (code {}): {}".format(e.cmd, e.returncode, e.output))
	Log(0, "LaunchServer ended...")
	return p

def TerminateServer():
	p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
	out, err = p.communicate()

	for line in out.splitlines():
		if config.ServerProcessName in line:
			pid = int(line.split(None, 1)[0])
			os.kill(pid, signal.SIGTERM)

def WipeServerData():
	Answer = raw_input("You are about to wipe all the data, including saved files. Are you sure ? [y/n]"
	
	if Answer == "y":
	
	

def InitializeWorkspace():
	
	RequiredPaths = [
		config.GetScriptWorkspaceTempDir(),
		config.GetScriptWorkspaceCacheDir(),
		config.GetScriptWorkspaceRecoveryDir()
	]

	for i in RequiredPaths :
		if os.path.exists(i) == False or os.path.isdir(i) == False:
			os.makedirs(i, exist_ok=True)


def IsWorkspaceInitialized():
	return os.path.exists(config.GetScriptWorkspaceTempDir()) and os.path.isdir(config.GetScriptWorkspaceTempDir()) and 	os.path.exists(config.GetScriptWorkspaceCacheDir()) and os.path.isdir(config.GetScriptWorkspaceCacheDir())

def UpdateAllocsFixes():

	DownloadAllocsFixes()
	ExtractAllocsFixes()
	
	
def DownloadAllocsFixes():
		
	attempts = 0

	while attempts < 3:
		try:
			with urllib.request.urlopen(config.CurrentServerData.AllocsFixesDownloadUrl, timeout=5) as response, open(config.GetAllocsFixesPackagePath(), 'wb') as out_file:
				data = response.read() # a `bytes` object
				out_file.write(data)
			break
		except urllib.error.URLError as e:
			attempts += 1
			print(type(e))

def	ExtractAllocsFixes():
	
	t = tarfile.open(config.GetAllocsFixesPackagePath())
	# @todo Add exception handling!
	#try:
	f = t.extractall(config.CurrentServerData.ServerDataDir)
	#except tarfile.ExtractError as e:
			
def Log(Verbosity, Message):
	if Verbosity >= config.LogVerbosity:
		print(Message)

main()
