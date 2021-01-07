#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

"""
diff --git a/linux-info.eclass b/linux-info.eclass
index 16740a3..f9941a4 100644
--- a/linux-info.eclass
+++ b/linux-info.eclass
@@ -731,7 +731,7 @@ check_extra_config() {
 			return 0
 		fi
 	else
-		require_configured_kernel
+		linux_config_exists
 	fi
 
 	einfo "Checking for suitable kernel configuration options..."
"""

subprocess.run(["/usr/bin/patch", "-d", ".", "-p", "1"], input=inStr, universal_newlines=True)




        modDir = os.path.join(FmConst.dataDir, "repo-patch", "gentoo")
        for fullfn in glob.glob(os.path.join(modDir, "*.patch")):
            FmUtil.shellCall("/usr/bin/patch -d \"%s\" -p 1 < \"%s\" > /dev/null" % (repoDir, fullfn))
