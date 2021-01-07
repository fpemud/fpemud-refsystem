import os

class FmUtil:

    @staticmethod
    def getLeafDirList(dirName):
        ret = []
        for root, dirs, files in os.walk(dirName):
            print(root)
            if root == dirName:
                continue
            if len(dirs) == 0:
                ret.append(root)
        return ret

print(FmUtil.getLeafDirList("profiles"))

